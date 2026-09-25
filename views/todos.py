import streamlit as st
from db import get_supabase

sb = get_supabase()
st.write(f'Logged in as {st.session_state.user.email}')

with st.form('add_todo', clear_on_submit=True):
    new = st.text_input('New Todo')
    added = st.form_submit_button('Add')
if added and new.strip():
    sb.table('todos').insert({'title': new.strip()}).execute()
    st.rerun()

for row in sb.table('todos').select('*').order('created_at').execute().data:
    st.write(row['title'])