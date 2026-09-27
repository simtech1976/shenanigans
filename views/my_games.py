import streamlit as st
from src.db import get_supabase, game_image_url, upload_game_image

sb = get_supabase()
uid = st.session_state.user.id

DICE_LABELS = {'d6': 'D6 (dice + pips)', 'd20': 'D20 (1d20 + value)'}
