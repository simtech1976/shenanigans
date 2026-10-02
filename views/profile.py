import re
import streamlit as st
from src.db import get_supabase

sb = get_supabase()
user = st.session_state.user
profile = st.session_state.get('profile') or {}
first_time = not profile.get('username_confirmed')

USERNAME_RE = re.compile(r'^[A-Za-z0-9](?:[A-Za-z0-9 ._\-]{1,28})[A-Za-z0-9]$')
MIN_PASSWORD_LENGTH = 8
PROVIDER_NAMES = {'email': 'Email and password', 'azure': 'Microsoft', 'discord': 'Discord'}
MAX_USER_CHAR = 30
MAX_EMOJI_CHAR = 16
BIO_MAX_CHAR = 500


def _friendly(err) -> str:
    text = str(err)
    if '23505' in text or 'duplicate key' in text:
        return 'That username is already taken.'
    return text


if first_time:
    st.title('Welcome to Shenanigans RPG Tables!')
    st.write('Please choose a username to use in the game.')
else:
    st.title('My Profile')


with st.form('profile_form'):
    username = st.text_input(
        'Username', value=profile.get('username', ''), max_chars=MAX_USER_CHAR,
        help=f'3-{MAX_USER_CHAR} characters, letters, numbers, spaces, and ._- are allowed.'
    )
    avatar = st.text_input(
        'Avatar Emoji (optional)',
        value=profile.get('avatar_emoji'),
        max_chars=MAX_EMOJI_CHAR,
        placeholder=f'e.g. 🐉, 🧙, ⚔️ (max {MAX_EMOJI_CHAR} characters)',
    )
    bio = st.text_area(
        'About me (optional)',
        value=profile.get('bio') or '',
        max_chars=BIO_MAX_CHAR,
        placeholder=f'Write a short bio about yourself (max {BIO_MAX_CHAR} characters).',
    )
    saved = st.form_submit_button('Continue' if first_time else 'Save Changes')

if saved:
    username = ' '.join(username.split())
    if not USERNAME_RE.match(username):
        st.error('Invalid username. Must be 3-30 characters, letters, numbers, spaces, and ._- are allowed.')
    else:
        try:
            rows = (sb.table('profiles').update({
                'username': username,
                'username_confirmed': True,
                'avatar_emoji': avatar.strip() or None,
                'bio': bio.strip() or None,
            }).eq('id', user.id).execute().data)
        except Exception as err:
            st.error(_friendly(err))
        else:
            if not rows:
                st.error('Could not update profile. Please log out and back in.')
            else:
                st.session_state.profile = rows[0]
                if first_time:
                    st.session_state.after_welcome = True
                st.toast('Profile updated!', icon='✅')
                st.rerun()

if first_time:
    st.stop()


# Account
st.divider()
st.subheader('Account')
providers = (getattr(user, 'app_metadata', None) or {}).get('providers', [])
st.markdown(
    f"**signed in with:** {', '.join(PROVIDER_NAMES.get(p, p.title()) for p in providers) or 'Unknown'}"
)

if user.email:
    st.caption(f'Account email: {user.email} (only visible to you, not other players)')

if 'email' in providers:
    with st.expander('Change Password'):
        with st.form('change_password', clear_on_submit=True):
            new_pw = st.text_input('New Password', type='password', help=f'Must be at least {MIN_PASSWORD_LENGTH} characters long.')
            confirm_pw = st.text_input('Confirm New Password', type='password')
            change = st.form_submit_button('Change Password')  
        if change:
            if len(new_pw) < MIN_PASSWORD_LENGTH:
                st.error(f'Password must be at least {MIN_PASSWORD_LENGTH} characters.')
            elif new_pw != confirm_pw:
                st.error('Passwords do not match.')
            else:
                try:
                    sb.auth.update_user({'password': new_pw})
                    st.toast('Password changed successfully!', icon='✅')
                except Exception as err:
                    st.error(f'Error changing password: {err}')
                else:
                    st.success('Password changed successfully!')
                    st.toast('Password changed successfully!', icon='✅')
