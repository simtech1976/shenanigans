import streamlit as st
from db import get_supabase

supabase = get_supabase()
rows = supabase.table('todos').select('*').execute()
st.write(rows.data)

"""
st.title("Login")

if "user" not in st.session_state:
    st.session_state["user"] = None

if st.session_state["user"]:
    st.success(f"Logged in as {st.session_state['user']['email']}")
else:
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    if st.button("Login"):7
        try:
            user = supabase.auth.sign_in_with_password({
                "email": email,
                "password": password
            })
            st.session_state["user"] = user.user
            st.success("Login successful")
            st.experimental_rerun()
        except Exception:
            st.error("Invalid credentials")
            """