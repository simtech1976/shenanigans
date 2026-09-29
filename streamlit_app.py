import streamlit as st
from src.db import get_supabase

st.set_page_config(page_title='Shenanigans RPG Tables', page_icon='🎲', layout='wide')

if 'user' not in st.session_state:
    st.session_state.user = None


def logout():
    get_supabase().auth.sign_out()
    for key in ('user', 'current_game_id', 'signed_urls'):
        st.session_state.pop(key, None)
    st.session_state.user = None
    st.rerun()


login_page = st.Page('views/login.py', title='Log In', icon='🔓')
games_page = st.Page('views/my_games.py', title='My Games', icon='🎲', default=True)
game_page = st.Page('views/game.py', title='Current Game', icon='📜')
logout_page = st.Page(logout, title='Log Out', icon='🔏')

if st.session_state.user is None:
    pg = st.navigation([login_page])
else:
    pg = st.navigation([games_page, game_page, logout_page])

pg.run()
