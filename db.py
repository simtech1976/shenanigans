import time
import uuid

import streamlit as st
from supabase import create_client, Client

GAME_IMAGE = 'game-images'
MAX_IMAGE_BYTES = 5 * 1024 * 1024
SIGNED_URL_SECONDS = 2400

def get_supabase() -> Client:
    """ One client per session, keeping auth from leeking to other users. """
    if 'supabase' not in st.session_state:
        st.session_state.supabase = create_client(
            st.secrets['SUPABASE_URL'],
            st.secrets['SUPABASE_KEY']
        )
    return st.session_state.supabase

def upload_game_image(game_id: int, uploaded_file) -> str:
    """ Upload a streamlit UploadedFile to game_id/random; returns path. """
    if uploaded_file.size > MAX_IMAGE_BYTES:
        raise ValueError('Image must be 5MB or smaller.')

    ext = uploaded_file.name.rsplit('.', 1)[-1].lower()
    path = f'{game_id}/{uuid.uuid4().hex}.{ext}'
    get_supabase().storage.from_(GAME_IMAGE).upload(
        path,
        uploaded_file.getvalue(),
        {'content-type': uploaded_file.type}
    )
    return path

def delete_game_image(path: str | None) -> None:
    if path:
        get_supabase().storage.from_(GAME_IMAGE).remove([path])

def game_image_url(path: str | None) -> str | None:
    """ Image URL, cahced per user session. """
    if not path:
        return None

    cache = st.session_state.setdefault('signed_urls', {})
    cached = cache.get(path)

    # Testing for now, will refresh 5 minutes before image expires.
    if cached is None or time.time() - cached[1] > SIGNED_URL_SECONDS - 300:
        res = get_supabase().storage.from_(GAME_IMAGE).create_signed_url(
            path, SIGNED_URL_SECONDS
        )
        cache[path] = (res.get('signedUrl') or res.get('signedURL'), time.time())
    return cache[path][0]