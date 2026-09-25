import streamlit as st
from db import get_supabase

sb = get_supabase()

if 'user' not in st.session_state:
    st.session_state.user = None

if st.session_state.user is None:

    login_tab, signup_tab = st.tabs(['Log in', 'Sign up'])

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
                        st.session_state.user = res.user
                        st.rerun()
                    except Exception as err:
                        st.error(f'Login failed: {err}')

    with signup_tab:
        with st.form('signup_form'):    
            email = st.text_input('Email', type='email', key='signup_email')
            pw = st.text_input('Password', type='password', key='signup_pw')
            submitted = st.form_submit_button('Sign Up')

            if submitted:
                if not email.strip() or not pw:
                    st.error('Please enter email and password')
                else:
                    try:
                        sb.auth.sign_up({
                            'email': email.strip(),
                            'password': pw
                        })
                        st.success('Check your password to confirm your account then log in.')
                    except Exception as err:
                        st.error(f'Sign-up failed: {err}')

    st.stop()

st.write(f'Logged in as {st.session_state.user.email}')

if st.button('Log Out'):
    sb.auth.sign_out()
    st.session_state.user = None
    st.rerun()

new = st.text_input('New Todo')
if st.button('Add') and new:
    sb.table('todos').insert({'title': new}).execute()
    st.rerun

for row in sb.table('todos').select('*').order('created_at').execute().data:
    st.write(row['title'])