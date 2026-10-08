import streamlit as st
from src.character_service import apply_change, load_sheet, point_balance
from src.db import get_supabase
from src.icons import label_html, prefetch_icons
from tabs.players_tab import md_escape
from src.rules import (D6, UPGRADE_STEP ,describe_roll, format_change, format_level,
                       plan_sheet_edits, plan_upgrade, roll, roll_notes)


sb = get_supabase()
uid = st.session_state.user.id
DICE_LABELS = {'d6': 'D6', 'd20': 'D20'}
MAX_CHARS = 60

character_id = st.session_state.get('current_character_id')
if character_id is None:
    st.error('No character selected')
    st.stop()

rows = sb.table('characters').select('*, profiles(username)').eq('id', character_id).execute().data
if not rows:
    st.error('Character not found or you do not have permission to view it')
    st.session_state.pop('current_character_id', None)
    st.stop()
character = rows[0]

game = sb.table('games').select('*').eq('id', character['game_id']).execute().data[0]
system = game['dice_system']
is_dm = game['dm_id'] == uid
is_owner = character['owner_id'] == uid
can_manage = is_dm or is_owner
can_edit_directly = is_dm or (is_owner and game.get('players_can_edit_sheets'))


# Header
title_col, points_col = st.columns([4, 1])
with title_col:
    st.title(character['name'])
    bits = []
    if character.get('species'):
        bits.append(md_escape(character['species']))
    player = (character.get('profiles') or {}).get('username')
    if is_dm and not is_owner and player:
        bits.append((f'Played by {md_escape(player)}'))
    bits.append(f"{md_escape(game['name'])} ({DICE_LABELS.get(system, system)})")
    st.caption(' | '.join(bits))
balance = point_balance(sb, character_id)
points_col.metric('Points', balance)

flash = st.session_state.pop(f'flash_{character_id}', None)
if flash:
    st.success(flash, icon='📢')
    st.toast(flash, icon='📢')

if character.get('notes'):
    with st.expander('Notes', expanded=False):
        st.markdown(character['notes'])

if st.button('🔙 Back to game'):
    st.session_state.current_game_id = character['game_id']
    st.switch_page('views/game.py')


# Stats and Skills
st.divider()
sheet = load_sheet(sb, game, character_id)
prefetch_icons([s for main_skill, skills in sheet for s in [main_skill, *skills]])


def show_roll_result(container, stat):
    result = st.session_state.get(f'roll_{character_id}_{stat.stat_id}')
    if result:
        text = f"🎲 {describe_roll(system, stat.level, result['dice'], result['total'])}"
        note = roll_notes(system, result['dice'])
        container.markdown(f"{text}{f' (**{note}**)' if note else ''}")


def upgrade_control(container, stat):
    """ Upgrade control with a confirm step for own and GM """
    change = plan_upgrade(game, stat)
    new_code = format_level(system, stat.level + UPGRADE_STEP)
    cost = change.cost
    if cost == 0 and not can_edit_directly:
        container.button('!', key=f'up_{stat.stat_id}', disabled=True, 
                         help='Upgrade is free but you cannot edit directly.')
        return
    if cost > balance:
        container.button(f'! {cost}', key=f'up_{stat.stat_id}', disabled=True, 
                         help=f'Upgrade {stat.name} to {new_code} costs {cost} points: '
                         f'{character["name"]} has {balance}.')
        return
    with container.popover(f'! {cost}' if cost else '! free'):
        st.markdown(f'Raise **{md_escape(stat.name)}** from **{stat.code}** to **{new_code}**'
                    + (f' for **{cost} points**?' if cost else '?'))
        if stat.is_main:
            st.caption(f'All {md_escape(stat.name)} skills rise by the same amount.')
        if cost:
            st.caption(f'{balance - cost} points remaining.')
        if st.button(f'Spend {cost} points' if cost else 'Upgrade', 
                     key=f'confirm_up_{stat.stat_id}', type='primary'):
            try:
                apply_change(sb, character_id, change)
            except Exception as err:
                st.error(str(err))
            else:
                st.session_state[f'flash_{character_id}'] = (
                    f'{stat.name} upgraded to {new_code}' 
                    + (f' for {cost} points.' if cost else '.')
                )
                st.rerun()



def stat_row(stat, main=None):
    if can_manage:
        label_col, code_col, roll_col, up_col, result_col = st.columns([4, 1.2, 1, 1.2, 3.6])
    else:
        label_col, code_col, roll_col, result_col = st.columns([4, 1.2, 1, 4])
    if stat.is_main:
        label_col.markdown(label_html(stat, bold=True, size=26), unsafe_allow_html=True)
        code_col.markdown(f'**{stat.code}***')
    else:
        note = f'{format_change(system, stat.bonus)}' if stat.is_improved else None
        label = label_html(stat, bold=stat.is_improved, note=note)
        label_col.markdown(f'<div style="padding-left:1.5rem">{label}</div>', unsafe_allow_html=True)
        code_col.markdown(f'**{stat.code}**' if stat.is_improved else f'{stat.code}')
    if roll_col.button('Roll', key=f'roll_btn_{stat.stat_id}'):
        dice, total = roll(system, stat.level)
        st.session_state[f'roll_{character_id}_{stat.stat_id}'] = {
            'dice': dice, 'total': total, 'level': stat.level}
        st.toast(f'{stat.name}: {total}', icon='🎲')
    if can_manage:
        upgrade_control(up_col, stat)
    show_roll_result(result_col, stat)


def level_input(stat, main=None) -> int:
    """Inputs for one stat in edit mode; returns the level entered."""
    label_col, a_col, b_col = st.columns([4, 1.5, 1.5])
    indent = '' if stat.is_main else 'padding-left:1.6rem'
    label_col.markdown(f'<div style="{indent}">{label_html(stat, bold=stat.is_main)}</div>',
                       unsafe_allow_html=True)
    key = f'edit_{character_id}_{stat.stat_id}'
    if system == D6:
        dice, pips = divmod(stat.level, 3)
        d = a_col.number_input('Dice', min_value=0, max_value=30, value=dice,
                               key=f'{key}_d', label_visibility='collapsed')
        p = b_col.selectbox('Pips', [0, 1, 2], index=pips, key=f'{key}_p',
                            format_func=lambda n: f'+{n}' if n else '+0',
                            label_visibility='collapsed')
        return int(d) * 3 + int(p)
    return int(a_col.number_input('Value', min_value=-10, max_value=50, value=stat.level,
                                  key=f'{key}_v', label_visibility='collapsed'))
 
 
if st.session_state.pop(f'close_edit_{character_id}', False):
    # After saving: leave edit mode and forget the old form values
    st.session_state[f'edit_mode_{character_id}'] = False
    for k in [k for k in st.session_state if str(k).startswith(f'edit_{character_id}_')]:
        del st.session_state[k]



if not sheet:
    st.info('This game has no stats yet. The GM can add them in the **Stats & skills** tab.')
elif can_edit_directly and st.toggle('✏️ Edit values', key=f'edit_mode_{character_id}',
                                     help='Set values directly, without spending points.'):
    st.caption('Set values directly, without spending points. '
               + ('Columns are dice and pips. ' if system == D6 else '')
               + 'A skill you leave as it is keeps moving with its main stat; '
                 "a skill you change can't be lower than its main stat.")
    with st.form(f'edit_values_{character_id}'):
        targets = {}
        for main, skills in sheet:
            with st.container(border=True):
                targets[main.stat_id] = level_input(main)
                for skill in skills:
                    targets[skill.stat_id] = level_input(skill, main)
        save_values = st.form_submit_button('Save changes', type='primary')
    if save_values:
        try:
            changes = plan_sheet_edits(game, sheet, targets)
        except ValueError as err:
            st.error(f'Nothing was saved: {err}.')
        else:
            if not changes:
                st.info('No values were changed.')
            else:
                failed = None
                for i, change in enumerate(changes):
                    try:
                        apply_change(sb, character_id, change)
                    except Exception as err:
                        failed = (i, err)
                        break
                if failed:
                    i, err = failed
                    st.error(f'Saved {i} of {len(changes)} changes, then stopped: {err}')
                else:
                    st.session_state[f'flash_{character_id}'] = (
                        f'Saved {len(changes)} change{"s" if len(changes) != 1 else ""}.')
                    st.session_state[f'close_edit_{character_id}'] = True
                    st.rerun()
else:
    for main, skills in sheet:
        with st.container(border=True):
            stat_row(main)
            for skill in skills:
                stat_row(skill, main)
 
if system == D6:
    st.caption('Skills nobody has improved use their main stat. Improved skills are shown in bold.')
if can_manage:
    unit = 'pip costs {} point(s) per die' if system == D6 else 'step costs {} point(s) per point of value'
    st.caption(f"⬆ shows what the next step costs: each {unit.format(game.get('skill_pip_cost', 1))} "
               f"for skills, and {game.get('main_pip_cost', 10)} for main stats.")


# Abilities
st.divider()
st.subheader('Abilities')
game_abilities = (sb.table('abilities').select('*').eq('game_id', character['game_id'])
                  .order('name').execute().data)
chosen_ids = {r['ability_id'] for r in sb.table('character_abilities').select('ability_id')
              .eq('character_id', character_id).execute().data}
chosen = [a for a in game_abilities if a['id'] in chosen_ids]
available = [a for a in game_abilities if a['id'] not in chosen_ids]
prefetch_icons(game_abilities)
 
if not chosen:
    st.caption(f"{md_escape(character['name'])} has no abilities yet.")
for ab in chosen:
    with st.container(border=True):
        text_col, btn_col = st.columns([5, 1])
        text_col.markdown(label_html(ab, bold=True, size=24), unsafe_allow_html=True)
        if ab.get('description'):
            text_col.caption(ab['description'])
        if can_manage:
            with btn_col.popover('Remove'):
                st.write(f"Remove **{md_escape(ab['name'])}** from {md_escape(character['name'])}?")
                if st.button('Remove', key=f"remove_ab_{ab['id']}", type='primary'):
                    sb.table('character_abilities').delete() \
                        .eq('character_id', character_id).eq('ability_id', ab['id']).execute()
                    st.session_state[f'flash_{character_id}'] = f"{ab['name']} removed."
                    st.rerun()
 
if can_manage:
    if not game_abilities:
        st.caption('This game has no abilities yet. The GM can add them in the game\'s **Abilities** tab.')
    elif not available:
        st.caption("All of this game's abilities have been chosen.")
    else:
        with st.expander('➕ Add an ability'):
            for ab in available:
                text_col, btn_col = st.columns([5, 1])
                text_col.markdown(label_html(ab, bold=True), unsafe_allow_html=True)
                if ab.get('description'):
                    text_col.caption(ab['description'])
                if btn_col.button('Add', key=f"add_ab_{ab['id']}"):
                    try:
                        sb.table('character_abilities').insert(
                            {'character_id': character_id, 'ability_id': ab['id']}).execute()
                    except Exception as err:
                        st.error(f'Could not add the ability: {err}')
                    else:
                        st.session_state[f'flash_{character_id}'] = f"{ab['name']} added."
                        st.rerun()
            st.caption('Everyone in the game sees abilities being added or removed in the activity feed.')

 
# Manage
if can_manage:
    st.divider()
    with st.expander('Edit details'):
        with st.form('edit_character'):
            name = st.text_input('Name', value=character['name'], max_chars=60)
            species = st.text_input('Species', value=character.get('species') or '', max_chars=60)
            notes = st.text_area('Notes', value=character.get('notes') or '')
            save = st.form_submit_button('Save')
        if save:
            if not name.strip():
                st.error('The character needs a name.')
            else:
                try:
                    sb.table('characters').update({
                        'name': name.strip(),
                        'species': species.strip() or None,
                        'notes': notes.strip() or None,
                    }).eq('id', character_id).execute()
                except Exception as err:
                    st.error(f'Could not save: {err}')
                else:
                    st.rerun()
 
    with st.expander('Delete character'):
        st.warning('This permanently deletes the character, including its stats, points '
                   'history and activity entries.')
        confirm = st.text_input(f"Type the character's name ({character['name']}) to confirm")
        if st.button('Delete character', type='primary', disabled=confirm.strip() != character['name']):
            sb.table('characters').delete().eq('id', character_id).execute()
            st.session_state.pop('current_character_id', None)
            st.session_state.current_game_id = character['game_id']
            st.switch_page('views/game.py')
 