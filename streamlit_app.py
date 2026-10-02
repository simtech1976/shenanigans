import streamlit as st
from src.db import get_supabase
from version import __version__

st.set_page_config(page_title='Shenanigans RPG Tables', page_icon='🎲', layout='wide')

if 'user' not in st.session_state:
    st.session_state.user = None


def logout():
    get_supabase().auth.sign_out()
    for key in ('user', 'profile', 'current_game_id', 'current_character_id', 'signed_urls', 'oauth_flow'):
        st.session_state.pop(key, None)
    st.session_state.user = None
    st.rerun()


def load_profile():
    rows = (
        get_supabase()
        .table('profiles')
        .select('*')
        .eq('id', st.session_state.user.id)
        .execute().data
    )
    return rows[0] if rows else {}


login_page = st.Page('views/login.py', title='Log In', icon='🔓')
games_page = st.Page('views/my_games.py', title='My Games', icon='🎲', default=True)
game_page = st.Page('views/game.py', title='Current Game', icon='📜')
character_page = st.Page('views/character.py', title='Character Sheet', icon='🧙')
profile_page = st.Page('views/profile.py', title='My Profile', icon='👤')
logout_page = st.Page(logout, title='Log Out', icon='🔏')
changelog_page = st.Page('views/changelog.py', title='Whats new', icon='📝')

if st.session_state.user is None:   
    pg = st.navigation([login_page])
else:
    if 'profile' not in st.session_state:
        st.session_state.profile = load_profile()
    if not st.session_state.profile.get('username_confirmed'):
        # First sign ion with Microsoft or Discord, we need to confirm the username
        pg = st.navigation([profile_page, logout])
    else:
        pg = st.navigation([games_page, game_page, character_page, profile_page, changelog_page, logout_page])
        if st.session_state.pop('after_welcome', False):
            st.switch_page(games_page)

st.sidebar.caption(f'Shenanigans RPG Tables v{__version__}')
pg.run()
