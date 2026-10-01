""" Players tabe for the game page ~ GM can incite and remove plauyers or they can leave the game. """

import streamlit as st


def _player_search(text: str) -> str:
    """ return plain text for username search. """
    return ''.join(ch for ch in text if ch.isalnum() or ch in ' -,_').strip()


def _invite_section(sb, game_id: int, member_ids: set):
    st.subheader('Invite Players')
    search_key = f'player_search_{game_id}'
    with st.form('player_search'):
        query = st.text_input('Search for username', placeholder='At least two characters')
        search = st.form_submit_button('Search')
    if search:
        st.session_state[search_key] = _player_search(query)

    query = st.session_state.get(search_key, '')
    if query and len(query) < 2:
        st.caption('Type at least two characters.')
    elif query:
        results = (
            sb.table('profiles')
            .select('id, username')
            .ilike('username', f'%{query}%')
            .order('username')
            .limit(10)
            .execute().data
        )
        results = [r for r in results if r['id'] not in member_ids]
        if not results:
            st.caption('No results found.')
        for r in results:
            name_col, btn_col = st.columns([4, 1])
            name_col.write(r['username'])
            if btn_col.button('Invite', key=f'invite_{r["id"]}'):
                try:
                    (sb.table('game_members')
                    .insert({
                        'game_id': game_id,
                        'user_id': r['id']
                    })
                    .execute())
                except Exception as err:
                    st.error(f'Could not send the invitation:{err}')
                else:
                    st.toast(f'Invitation sent to {r["username"]}', icon='✅')
                    st.rerun()
    st.caption('Invited players will see the invatiation in their My Game page. They can accept or decline the invitation.')



def render_players_tab(sb, game_id: int, uid: str, is_dm: bool):
    members = (
        sb.table('game_members')
        .select('user_id, role, status, created_at, profiles(username)')
        .eq('game_id', game_id)
        .order('created_at')
        .execute().data
    )
    member_ids = {m['user_id'] for m in members}

    # Shows DM usernames for characters
    characters_by_owner: dict[str, list[str]] = {}
    if is_dm:
        chars = (
            sb.table('characters')
            .select('owner_id, name')
            .eq('game_id', game_id)
            .order('name')
            .execute().data
        )
        for c in chars:
            characters_by_owner.setdefault(c['owner_id'], []).append(c['name'])

    if is_dm:
        _invite_section(sb, game_id, member_ids)
        st.divider()

    st.subheader('In this game')
    for m in members:
        username = (m.get('profiles') or {}).get('username', 'Unknown player')
        is_me = m['user_id'] == uid
        if m['role'] == 'dm':
            status = '🧙 Dungeon Master'
        elif m['status'] == 'invited':
            status = '📨 Invited'
        else:
            status = '🎲 Player'

        with st.container(border=True):
            info_col, action_col = st.columns([4, 1])
            info_col.markdown(f"**{username}**{' (you)' if is_me else ''} - {status}")
            if is_dm and m['role'] == 'player' and m['status'] == 'active':
                names = characters_by_owner.get(m['user_id'])
                info_col.caption('Playing:' + ', '.join(names) if names else 'No characters yet.')

            # DN can cancel invitations or remove players
            if is_dm and m['role'] == 'player':
                invited = m['status'] == 'invited'
                with action_col.popover('Cancel Invite' if invited else 'Remove'):
                    if invited:
                        st.write(f'Cancel the invitation for **{username}**?')
                    else:
                        st.write(f'Remove **{username}** from the game? (characters are kept).')
                    if st.button('Confirm', key=f'remove_{m["user_id"]}', type='primary'):
                        gm = st.table('game_members')
                        gm.delete().eq('game_id', game_id).eq('user_id', m['user_id']).execute()

            # Players can leave the game
            elif is_me and m['role'] == 'player':
                with action_col.popover('Leave Game'):
                    st.write('Leave the game? (characters are kept).')
                    if st.button('Leave', key='leave_game', type='primary'):
                        gm = st.table('game_members')
                        gm.delete().eq('game_id', game_id).eq('user_id', uid).execute()
                        st.session_state.pop('current_game_id', None)
                        st.switch_page('views/my_games.py')
