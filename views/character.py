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
can_edit_directly = is_dm or (is_owner and game['allow_direct_edit'])


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
        st.markdown(character['notes'], unsafe_allow_html=True)

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
        if st.button('Spend {cost} points' if cost else 'Upgrade', 
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


if not sheet:
    st.info('No stats or skills defined for this character.')
for main_skill, skills in sheet:
    with st.container(border=True):
        stat_row(main_skill)
        for skill in skills:
            stat_row(skill, main_skill)

if system == D6:
    st.caption('None improved skills use main stat')
if can_manage:
    unit = 'pip costs {} point(s) per die' if system == D6 else 'step costs {} point(s) per point of value'
    st.caption(f"⬆ shows what the next step costs: each {unit.format(game.get('skill_pip_cost', 1))} "
               f"for skills, and {game.get('main_pip_cost', 10)} for main stats.")


# Manage
if can_manage:
    st.divider()
    with st.expander('Edit Details'):
        with st.form('edit_character'):
            name = st.text_input('Character Name', value=character['name'], max_chars=MAX_CHARS)
            species = st.text_input('Species', value=character.get('species') or '', max_chars=MAX_CHARS)
            notes = st.text_area('Notes', value=character.get('notes') or '', height=150)
            save = st.form_submit_button('Save')
        if save:
            if not name.strip():
                st.error('Character name cannot be empty')
            else:
                try:
                    sb.table('characters').update({
                        'name': name.strip(),
                        'species': species.strip() or None,
                        'notes': notes.strip() or None
                    }).eq('id', character_id).execute()
                    st.success('Character updated')
                except Exception as e:
                    st.error(f'Error updating character: {e}')
                else:
                    st.rerun()

    with st.expander('Delete Character'):
        st.warning('This will permanently delete the character and all associated data.')
        confirm = st.checkbox('I understand that this action cannot be undone.')
        confirm_name = st.text_input('Type the character name ({character["name"]}) to confirm deletion')
        if confirm and confirm_name == character['name']:
            if st.button('Delete Character', type='primary', disabled=not confirm and confirm_name == character['name']):
                try:
                    sb.table('characters').delete().eq('id', character_id).execute()
                    st.success('Character deleted')
                    st.session_state.pop('current_character_id', None)
                    st.session_state.current_game_id = character['game_id']
                    st.switch_page('views/game.py')
                except Exception as e:
                    st.error(f'Error deleting character: {e}')
