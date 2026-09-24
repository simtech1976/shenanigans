import streamlit as st
from supabase import create_client, Client

def get_supabase() -> Client:
    if 'supabase' not in st.session_state:
        st.session_state.supabase = create_client(
            st.secrets['SUPABASE_URL'],
            st.secrets['SUPABASE_key']
        )
    return st.session_state.supabase
