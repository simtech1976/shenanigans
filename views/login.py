import streamlit as st
from db import get_supabase

sb = get_supabase()
login_tab, signup_tab = st.tabs(['Log In', 'Sign Up'])

with login_tab:
    with st.form('login_form'):
        email = st.text_input('Email', type='email', key='login_email')
        pw = st.text_input('Password', type='password', key='login_pw')
        submitted = st.form_submit_button('Log In')

    if submitted:
        if not email.strip() or not pw:
            st.error('Please enter email and password')
        else:
            try:
                res = sb.auth.sign_in_with_password({
                    'email': email.strip(),
                    'password': pw
                })
            except Exception as err:
                st.error(f'Login failed:{err}')
            else:
                st.session_state.user = res.user
                st.rerun()

with signup_tab:
    with st.form('signup_form'):
        username = st.text_input('Username', key='signup_username')
        email = st.text_input('Email', type='email', key='signup_email')
        pw = st.text_input('Password', type='password', key='signup_pw')
        submitted = st.form_submit_button('Sign Up')

    if submitted:
        if not email.strip or not pw:
            st.error('Please enter username, email and password.')
        else:
            try:
                sb.auth.sign_up({
                    'email': email.strip(),
                    'password': pw,
                    'options': {'data': {'username': username.strip()}}
                })
            except Exception as err:
                st.error(f'Sign-up failed:{err}')
            else:
                st.success('Check your email for verification')