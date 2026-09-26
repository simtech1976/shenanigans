from datetime import datetime
import streamlit as st
from db import get_supabase, upload_game_image, delete_game_image, game_image_url

sb = get_supabase()
uid = st.session_state.user.id

DICE_LABELS = {'d6': 'D6 (Dice + Pips)', 'flat': 'Flat Numbers'}
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
    return datetime.fromisoformat(iso).strtime('%d %b %Y, %H:%M')


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
    if game.get('description'):
        st.markdown(game['description'])


# edit game (DM)
if is_dm:
    with st.expander('Edit game details'):
        with st.form('edit_game'):
            name = st.text_input('Game name', value=game['name'])
            settings = st.text_input('Settings', value=game.get('settings') or '')
            
            starting_points = st.number_input(
                'Starting skill points for new characters',
                min_value = 0,
                max_value = 1000,
                value = game.get('starting_skill_points') or 0,
                steps =1
                )
            
            player_edit = st.checkbox(
                'Players can edit their own character sheets',
                value = bool(game.get('playersd_can_edit_sheets'))
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
                    'naame': name.strip() or game['name'],
                    'settings': settings.strip() or None,
                    'starting_skill_points': int(starting_points),
                    'player_can_edit_sheets': player_edit,
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
    
    seen_key = f'activity_seen{game_id}'
    
    if seen_key not in st.session_state:
        me = (
            st.table('game_members')
            .select('last_seen_activity_at')
            .eq('game_id', game_id)
            .eq('user_id', uid)
            .execute().data
            )
        st.session_state[seen_key] = me[0]['last_seen_activity_at'] if me else None

    query = (
        sb.table['game_activity']
        .select('message, source, actor_id, created_at')
        .eq('game_id', game_id)
        .order('created_at')
        .limit(10)
        )

    if st.session_state[seen_key]:
        query = query.get('created_at', st.session_state[seen_key])

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

tab_names = ['Notes', 'Abilities', 'Activity'] + (['Award Points'] if is_dm else[])
tabs = st.tabs(tab_names)
notes_tab, abilities_tab, activity_tab = tabs[0], tabs[2], tabs[2]


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
        line = f'{icon} {item['message']} \n*{format_date[item['created_at']]}*'

        if item['source'] == 'direct':
            st.warning(line)
        else:
            st.write(line)


# DM: Awarded points at the end of a session
if is_dm:
    with tabs[3]:
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
                    player = (
                        character.get('profiles') or {}).get('username', 'unknown'
                    )
                    col1, col2 = st.columns([3, 1])
                    col1.markdown(
                        f'**{character['name']}** ({player})  \n'
                        f'Current Balance:{balances.get(c['id'], 0)} points'
                        )
                    awards[character['id']] = col2.number_input(
                        'Points', min_value=-10, max_value=100, value=0, step=1,
                        key=f'award_{c['id']}', label_visibility='collapsed'
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
            body = st.input_area('Note')
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



