import streamlit as st
from db import get_supabase

sb = get_supabase()

if 'user' not in st.session_state:
    st.session_state.user = None

def logout():
    get_supabase().auth.sign_out()
    st.session_state.user = None
    st.rerun()


login_page = st.Page('views/login.py', title='Log In', icon='🔑')
todos_page = st.Page('views/todos.py', title='Todos', icon='✅', default=True)
logout_page = st.Page(logout, title='Log Out', icon='🚪')

if st.session_state.user is None:
    pg = st.navigation([login_page])
else:
    pg = st.navigation([todos_page, logout_page])

pg.run()