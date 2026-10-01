from datetime import datetime
import streamlit as st
from src.db import get_supabase, upload_game_image, delete_game_image, game_image_url
from src.players_tab import render_players_tab
from src.stats_manager import render_stats_tab
from src.icons import IconChange, icon_inputs, label_html, prefetch_icons

sb = get_supabase()
uid = st.session_state.user.id

DICE_LABELS = {'d6': 'D6 (Dice + Pips)', 'd20': 'D20 (1d20+value)'}
SOURCE_ICONS = {'points': '🎯', 'direct': '✏️', 'gm': '🧙', 'award': '⭐'}

game_id = st.session_state.get('current_game_id')
if game_id is None:
    st.info('Chose a game from **My games** first.')
    st.stop()

rows = sb.table('games').select('*').eq('id', game_id).execute().data
if not rows:
    st.error('This game does not exist or you no longer have access.')
    st.stop()

game = rows[0]
is_dm = game['dm_id'] == uid


def format_date(iso: str) -> str:
    return datetime.fromisoformat(iso).strftime('%d %b %Y, %H:%M')


# Header
img_col, info_col = st.columns([1, 2])
img_url = game_image_url(game['image_path'])
if img_url:
    img_col.image(img_url)

with info_col:
    st.title(game['name'])
    st.caption(f"{game.get('setting') or 'No setting'}" 
               f" | {DICE_LABELS[game['dice_system']]}"
               f"{' | You are the game master' if is_dm else ''}")
    unit = 'die' if game['dice_system'] == 'd6' else 'points of current value'
    st.caption(f"Upgrade cost per pip:{game.get('skill_pip_cost', 1)} x {unit} for skills, "
        f"{game.get('main_pip_cost', 10)} x {unit} for main stats")
    if game.get('description'):
        st.markdown(game['description'])


# edit game (DM)
if is_dm:
    with st.expander('Edit Game Details'):
        with st.form('edit_game'):
            name = st.text_input('Game name', value=game['name'])
            game_setting = st.text_input('Setting', value=game.get('setting') or '')
            
            starting_points = st.number_input(
                'Starting skill points for new characters',
                min_value = 0,
                max_value = 1000,
                value = game.get('starting_skill_points') or 0,
                step = 1
                )

            cost_col1, cost_col2 = st.columns(2)
            skill_cost = cost_col1.number_input(
                'Skill cost per die *per pip', min_value=0, max_value=100,
                value=game.get('skill_pip_cost', 1), step=1
                )
            main_cost = cost_col2.number_input(
                'Main stat cost per doe *per pip', min_value=0, max_value=100,
                value=game.get('main_pip_cost', 10), step=1
                )
                        
            player_edit = st.checkbox(
                'Players can edit their own character sheets',
                value = bool(game.get('players_can_edit_sheets'))
                )

            description = st.text_area(
                'Description *markdown supported',
                value = game.get('description') or '',
                height = 150
                )

            new_image = st.file_uploader(
                'Replace cover image',
                type = ['png', 'jpg', 'jpeg', 'webp']
                )
            
            saved = st.form_submit_button('Save Changes')

        if saved:
            ok = True
            
            try:
                updates = {
                    'name': name.strip() or game['name'],
                    'setting': game_setting.strip() or None,
                    'starting_skill_points': int(starting_points),
                    'players_can_edit_sheets': player_edit,
                    'skill_pip_cost': int(skill_cost),
                    'main_pip_cost': int(main_cost),
                    'description': description.strip() or None
                    }

                if new_image:
                    updates['image_path'] = upload_game_image(game_id, new_image)
                sb.table('games').update(updates).eq('id', game_id).execute()

                if new_image:
                    delete_game_image(game['image_path'])

            except Exception as err:
                ok = False
                st.error(f'Could not save:{err}')

            if ok:
                st.rerun()

st.divider()


@st.fragment(run_every='30s')
def activity_notifications():
    """ Toast noficiations for other players"""
    
    seen_key = f'activity_seen_{game_id}'
    
    if seen_key not in st.session_state:
        me = (
            sb.table('game_members')
            .select('last_seen_activity_at')
            .eq('game_id', game_id)
            .eq('user_id', uid)
            .execute().data
            )
        st.session_state[seen_key] = me[0]['last_seen_activity_at'] if me else None

    query = (
        sb.table('game_activity')
        .select('message, source, actor_id, created_at')
        .eq('game_id', game_id)
        .order('created_at')
        .limit(10)
        )

    if st.session_state[seen_key]:
        query = query.gt('created_at', st.session_state[seen_key])

    new_rows = query.execute().data

    for row in new_rows:
        if row['actor_id'] != uid:
            st.toast(row['message'], icon = SOURCE_ICONS.get(row['source'], '🎲'))

    if new_rows:
        latest = new_rows[-1]['created_at']
        st.session_state[seen_key] = latest
        sb.table('game_members') \
            .update({'last_seen_activity_at': latest}) \
            .eq('game_id', game_id) \
            .eq('user_id', uid) \
            .execute()


activity_notifications()

tab_names = ['Notes', 'Players', 'Stats & Skills', 'Abilities', 'Activity'] + (['Award Points'] if is_dm else[])
tabs = st.tabs(tab_names)
notes_tab, players_tab, stats_tab, abilities_tab, activity_tab = tabs[0], tabs[1], tabs[2], tabs[3], tabs[4]


# Players
with players_tab:
    render_players_tab(sb, game_id, is_dm)


# Stats and Skills
with stats_tab:
    render_stats_tab(sb, game_id, is_dm)


# Activity feed
with activity_tab:
    st.caption('Character stats and points are recorded automatically.')
    feed = (
        sb.table('game_activity')
        .select('message, source, created_at')
        .eq('game_id', game_id)
        .order('created_at', desc=True)
        .limit(50)
        .execute().data
    )
    if not feed:
        st.caption('All quiet 🤫')

    for item in feed:
        icon = SOURCE_ICONS.get(item['source'], '🎲')
        line = f'{icon} {item['message']}  \n*{format_date(item['created_at'])}*'

        if item['source'] == 'direct':
            st.warning(line)
        else:
            st.write(line)
    st.caption('🎯 spent points · ✏️ edited directly · 🧙 changed by GM · ⭐ points awarded')
    


# DM: Awarded points at the end of a session
if is_dm:
    with tabs[4]:
        characters = (
            sb.table('characters')
            .select('id, name, owner_id, profiles(username)')
            .eq('game_id', game_id)
            .order('name')
            .execute().data
        )
        if not characters:
            st.info('No cahacters in the game yet.')
        else:
            ids = [character['id'] for character in characters]
            balances = {
                balance['character_id']: balance['balance'] for balance in 
                sb.table('character_point_balances')
                .select('*')
                .in_('character_id', ids)
                .execute().data
            }

            with st.form('award_points', clear_on_submit=True):
                reason = st.text_input('Session / Reason', placeholder='e.g. Combat/investigaiton')
                awards = {}
                for character in characters:
                    player = (character.get('profiles') or {}).get('username', 'unknown')
                    col1, col2 = st.columns([3, 1])
                    col1.markdown(
                        f'**{character['name']}** ({player})  \n'
                        f'Current Balance:{balances.get(character['id'], 0)} points'
                        )
                    awards[character['id']] = col2.number_input(
                        'Points', min_value=-10, max_value=100, value=0, step=1,
                        key=f'award_{character['id']}', label_visibility='collapsed'
                    )

                give = st.form_submit_button('Award Character Points')

            if give:
                rows = [{
                    'character_id': cid,
                    'amount': int(pts),
                    'reason': reason.strip() or 'Session award'} 
                    for cid, pts in awards.items() if pts !=0]
                
                if not rows:
                    st.warning('Enter points for at least one character.')
                else:
                    try:
                        sb.table('point_transactions').insert(rows).execute()
                    except Exception as err:
                        st.error(f'Could not award points:{err}')
                    else:
                        st.success(f'Awards points to {len(rows)} chacters(s).')
                        st.rerun()

            st.caption('Use a negative number to correct a mistake.')

            history = (
                sb.table('amount, reason, created_at, characters(name)')
                .in_('character_id', ids)
                .order('created_at', desc=True)
                .limit(30)
                .execute().data
            )
            for h in history:
                sign = '+' if h['amount'] > 0 else ''
                st.write(
                    f'{format_date(h['created_at'])} · '
                    f'**{h['characters']['name']}** · '
                    f'{sign}{h['amount']} · '
                    f'{h['reason'] or ""}'
                )

# Notes
with notes_tab:
    if is_dm:
        with st.form('add_note', clear_on_submit=True):
            title = st.text_input('Title (optional)')
            body = st.text_area('Note')
            visible = st.form_submit_button('Visible to players')
            add = st.form_submit_button('Add Note')
            if add:
                if not body.strip():
                    st.error('The note is empty.')
                else:
                    sb.table('game_notes').insert({
                        'game_id': game_id,
                        'title': title.strip() or None,
                        'body': body.strip(),
                        'visible_to_players': visible,
                    }).execute()
                    st.rerun()

    notes = (
        sb.table('game_notes')
        .select('*')
        .eq('game_id', game_id)
        .order('created_at', desc=True)
        .execute().data
    )
    if not notes:
        st.caption('No notes yet.')

    for note in notes:
        with st.container(border=True):
            label = note['title'] or 'Note'
            if is_dm:
                if note['visible_to_players']:
                    label += 'Visible to players'
                else:
                    label += 'DM Only'

            st.markdown(f'**{label}**')
            st.caption(f'Added {format_date(note['created_at'])}')
            st.markdown(note['body'])
            
            if is_dm:
                c1, c2, _ = st.columns([1, 1, 3])
                if note['visible_to_players']:
                    toggle_label = 'hide from players' 
                else:
                    toggle_label = 'Show to players'

                if c1.button(toggle_label, key=f'vis_{note['id']}'):
                    sb.table('game_notes').update(
                        {'visible_to_players': not note['visible_to_players']}
                    ).eq('id', note['id']).execute()
                    st.rerun()
                if c2.button('Delete', key=f'del_note_{note['id']}'):
                    sb.table('game_notes').delete().eq('id', note['id']).execute()
                    st.rerun()


# Abilities
def _ability_error(err) -> str:
    text = str(err)
    return 'Name already used in this game.' if ('23505' in text or 'duplicate key' in text) else text


with abilities_tab:
    st.caption('Abilities players can choose for their characters.')
    if is_dm:
        with st.form('add_ability', clear_on_submit=True):
            a_name = st.text_input('Ability Name', placeholder='e.g. Force Sensitive')
            a_desc = st.text_area('Description')
            a_emoji, a_upload, _ = icon_inputs('add_ability')
            add_ability = st.form_submit_button('Add Ability')
        if add_ability:
            if not a_name.strip():
                st.arror('Please enter an ability name')
            else:
                change = IconChange(game_id, a_emoji, a_upload, False)
                try:
                    sb.table('abilites').insert({
                        'game_id': game_id,
                        'name': a_name.strip(),
                        'description': a_desc.strip() or None,
                        **change.fields()
                    }).execute()
                except Exception as err:
                    change.rollback()
                    st.arror(f'Could not add ability:{_ability_error(err)}')
                else:
                    st.rerun()

    abilities = (
        sb.table('abilities')
        .select('*')
        .eq('game_id', game_id)
        .order('name')
        .execute().data
    )
    prefetch_icons(abilities)
    if not abilities:
        st.caption('No abilites defined yet.')
    for a in abilities:
        with st.container(border=True):
            c1, c2 = st.columns([5, 1])
            c1.markdown(label_html(a, bold=True, size=26), unsafe_allow_html=True)
            if a.get('description'):
                c1.write(a['description'])
            if is_dm:
                with c2.popover('Edit'):
                    with st.form(f"edit_ability_{a['id']}"):
                        e_name = st.text_input('Name', value=a['name'])
                        e_desc = st.text_area('Description', value=a.get('desciption') or '')
                        e_emoji, e_upload, e_remove = icon_inputs(f"edit_ability_{a}", a)
                        e_save = st.form_submit_button('Save')
                    if e_save:
                        if not e_name.strip():
                            st.error('Name cannot be null.')
                        else:
                            change = IconChange(
                                game_id, e_emoji, e_upload, e_remove, a.get('icon_path')
                            )
                            try:
                                sb.table('abilities').update({
                                    'name': e_name.strip(),
                                    'description': e_desc.strip() or None,
                                    **change.fields()
                                }).eq('id', a['id']).execute()
                            except Exception as err:
                                change.rollback()
                                st.error(_ability_error(err))
                            else:
                                change.commit()
                                st.rerun()
                    st.divider()
                    st.caption("Deleting an ability removes it from every character.")
                    confirm = st.checkbox('I understand', key=f"confirm_del_a_{a['id']}")
                    if st.button('Delete', key=f"del_a_{a['id']}", type='primary', disabled=not confirm):
                        sb.table('abilities').delete().eq('id', a['id']).execute()
                        delete_game_image(a.get('icon_path'))
                        st.rerun()