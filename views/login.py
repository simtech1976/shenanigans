import streamlit as st
from src.db import get_supabase

sb = get_supabase()

MIN_PW_LEN = 8
MIN_USER_LEN = 3
MAX_USER_LEN = 30

login_tab, signup_tab, reset_tab = st.tabs(['Log In', 'Sign Up', 'Forgot Password'])

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
        username = username.strip()
        if not username or not email.strip() or not pw:
            st.error('Please enter username, email and password.')
        elif not MIN_USER_LEN <= len(username) <= MAX_USER_LEN:
            st.error(f'Username must be {MIN_USER_LEN} to {MAX_USER_LEN} characters.')
        elif len(pw) < MIN_PW_LEN:
            st.error(f'Password must be at leach {MIN_PW_LEN} characters.')
        else:
            try:
                sb.auth.sign_up({
                    'email': email.strip(),
                    'password': pw,
                    'options': {'data': {'username': username.strip()}}
                })
            except Exception as err:
                if 'Database error' in str(err):
                    # This is temp, will parse exaxt code ~ this is just an assumption
                    st.error(f'Username {username} already taken.')
                else:
                    st.error(f'Sign-up failed:{err}')
            else:
                st.success('Check your email for verification')



# Forgot password
with reset_tab:
    reset_email = st.session_state.get('reset_email')

    if not reset_email:
        #.1 Get email address
        st.write('Enter your email and we will send you a code to reset your password.')
        with st.form('reset_request_form'):
            email = st.text_input('Email', type='email', key='reset_request_email')
            send = st.form_submit_button('Send Code')
        if send:
            email = email.strip()
            if not email:
                st.error('Please enter email address')
            else:
                try:
                    sb.auth.reset_password_for_email(email)
                except Exception as err:
                    st.error(f'Could not send the code:{err}')
                else:
                    st.session_state.reset_email = email
                    st.rerun()
    else:
        #.2 enter code and new password wihtout confirming if email/account exists
        st. info(f'If **{reset_email}** has an account associtated, a reset code has been sent.'
                    'It may take a minute to arrive.')
        with st.form('reset_confirm_form'):
            code = st.text_input('Code', key='reset_code')
            new_pw = st.text_input('New password', type='password', key='reset_new_pw')
            confirm_pw = st.text_input('New password', type='password', key='reset_confirm_pw')
            confirm = st.form_submit_button('Reset Password')
        if confirm:
            code = code.strip().replace(' ', '')
            if not code.isdigit():
                st.error('Enter numberic code from the email.')
            elif len(new_pw) < MIN_PW_LEN:
                st.error(f'Password must be at leach {MIN_PW_LEN} characters.')
            elif new_pw != confirm_pw:
                st.error('Passwords do not match!')
            else:
                try:
                    res = sb.auth.verify_otp({
                        'email': reset_email,
                        'token': code,
                        'type': 'recovery'
                    })
                    sb.auth.update_user({'password': new_pw})
                except Exception as err:
                    st.error(f'Could not reset your password:{err}')
                else:
                    st.session_state.pop('reset_email', None)
                    st.session_state.user = res.user
                    st.toast('Password Changed', icon='🔑')
                    st.rerun()

            col1, col2 = st.columns(2)
            if col1.button('Send Code'):
                try:
                    sb.auth.reset_password_for_email(reset_email)
                except Exception as err:
                    st.error(f'Could not sent code:{err}')
                else:
                    st.success('Code has been sent')

            if col2.button('Use a differnet email'):
                st.session_state.pop('reset_email', None)
                st.rerun()
