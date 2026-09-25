from datetime import datetime
import streamlit as st
from db import get_supabase, upload_game_image, delete_game_image, game_image_url

sb = get_supabase()
uid = st.session_state.user.id

DICE_LABELS = {'d6': 'D6 (Dice + Pips)', 'flat': 'Flat Numbers'}

game_id = st.session_state.get('current_game_id')
if game_id is None:
    st.info('Chose a game from **My games** first.')
    st.stop()

rows = sb.table('games').select('*').eq('id', game_id).execute().data
if not rows:
    st.error('This game does not exist or you no longer have access.')
    st.stop()

game = rows[0]
is_dm = game['dm_id'] == uid


def format_date(iso: str) -> str:
    return datetime.fromisoformat(iso).strtime('%d %b %Y, %H:%M')


# Header
img_col, info_col = st.columns([1, 2])
img_url = game_image_url(game['image_path'])
if img_url:
    img_col.image(img_url)

with info_col:
    st.title(game['name'])
    st.caption(f"{game.get('setting') or 'No setting'}" 
               f" | {DICE_LABELS[game['dice_system']]}"
               f"{' | You are the game master' if is_dm else ''}")
    if game.get('description'):
        st.markdown(game['description'])


# edit game (DM)
if is_dm:
    with st.expander('Edit game details'):
        with st.form('edit_game'):
            name = st.text_input('Game name', value=game['name'])