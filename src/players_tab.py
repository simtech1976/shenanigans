""" Players tabe for the game page ~ GM can incite and remove plauyers or they can leave the game. """

import streamlit as st


def md_escape(text: str) -> str:
    """Escape special characters for Markdown."""
    return ''.join('\\' + ch if ch in '\\`*_{}[]()#+-.!|<>~' else ch for ch in text)


def _player_search(text: str) -> str:
    """ return plain text for username search. """
    return ''.join(ch for ch in text if ch.isalnum() or ch in ' -,_').strip()



def _invite_section(sb, game_id: int, member_ids: set):
    st.subheader('Invite players')
    people = (sb.table('profiles').select('id, username, avatar_emoji, bio')
              .limit(1000).execute().data)
    people = sorted((p for p in people if p['id'] not in member_ids),
                    key=lambda p: p['username'].lower())
    if not people:
        st.caption('Everyone with an account is already in this game. New players need to '
                   'sign up before they appear here.')
        return
 
    filter_text = st.text_input('Filter', placeholder='Type part of a username to narrow the list',
                                key=f'player_filter_{game_id}').strip().lower()
    if filter_text:
        people = [p for p in people if filter_text in p['username'].lower()]
        if not people:
            st.caption('No one matches that filter.')
 
    with st.container(height=360 if len(people) > 6 else 'content', border=False):
        for p in people:
            name_col, btn_col = st.columns([4, 1])
            avatar = f"{p['avatar_emoji']} " if p.get('avatar_emoji') else ''
            name_col.markdown(f"{avatar}**{md_escape(p['username'])}**")
            if p.get('bio'):
                name_col.caption(p['bio'])
            if btn_col.button('Invite', key=f"invite_{p['id']}"):
                try:
                    sb.table('game_members').insert({'game_id': game_id, 'user_id': p['id']}).execute()
                except Exception as err:
                    st.error(f'Could not send the invitation: {err}')
                else:
                    st.toast(f"Invitation sent to {p['username']}", icon='✉️')
                    st.rerun()
    st.caption('Invited players see the invitation on their **My games** page and choose '
               'whether to accept. New players need to sign up before they appear here.')
 
 
def render_players_tab(sb, game_id: int, uid: str, is_dm: bool):
    members = (sb.table('game_members')
               .select('user_id, role, status, created_at, profiles(username, avatar_emoji)')
               .eq('game_id', game_id).order('created_at').execute().data)
    member_ids = {m['user_id'] for m in members}
 
    # The GM can see every character, so show who plays whom
    characters_by_owner: dict[str, list[str]] = {}
    if is_dm:
        chars = (sb.table('characters').select('owner_id, name')
                 .eq('game_id', game_id).order('name').execute().data)
        for c in chars:
            characters_by_owner.setdefault(c['owner_id'], []).append(c['name'])
 
    if is_dm:
        _invite_section(sb, game_id, member_ids)
        st.divider()
 
    st.subheader('In this game')
    for m in members:
        prof = m.get('profiles') or {}
        username = prof.get('username', 'Unknown player')
        avatar = f"{prof['avatar_emoji']} " if prof.get('avatar_emoji') else ''
        is_me = m['user_id'] == uid
        if m['role'] == 'dm':
            status = '🧙 Game master'
        elif m['status'] == 'invited':
            status = '✉️ Invited'
        else:
            status = '🎲 Player'
 
        with st.container(border=True):
            info_col, action_col = st.columns([4, 1])
            info_col.markdown(f"{avatar}**{md_escape(username)}**{' (you)' if is_me else ''} · {status}")
            if is_dm and m['role'] == 'player' and m['status'] == 'active':
                names = characters_by_owner.get(m['user_id'])
                info_col.caption('Playing: ' + ', '.join(names) if names else 'No character yet')
 
            # GM: cancel an invitation or remove a player
            if is_dm and m['role'] == 'player':
                invited = m['status'] == 'invited'
                with action_col.popover('Cancel invite' if invited else 'Remove'):
                    if invited:
                        st.write(f'Cancel the invitation to **{username}**?')
                    else:
                        st.write(f'Remove **{username}** from this game? Their characters are '
                                 'kept, so they can be brought back by inviting them again.')
                    if st.button('Confirm', key=f"remove_{m['user_id']}", type='primary'):
                        sb.table('game_members').delete() \
                            .eq('game_id', game_id).eq('user_id', m['user_id']).execute()
                        st.rerun()
 
            # Player: leave the game
            elif is_me and m['role'] == 'player':
                with action_col.popover('Leave game'):
                    st.write('Leave this game? You will lose access to it until the GM '
                             'invites you again. Your characters are kept.')
                    if st.button('Leave', key='leave_game', type='primary'):
                        sb.table('game_members').delete() \
                            .eq('game_id', game_id).eq('user_id', uid).execute()
                        st.session_state.pop('current_game_id', None)
                        st.switch_page('views/my_games.py')
 