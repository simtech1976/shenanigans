import time
import uuid

import streamlit as st
from supabase import create_client, Client

GAME_IMAGES = 'game-images'
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

def upload_game_image(game_id: int, uploaded_file, folder: str = '',
                      max_bytes: int = MAX_IMAGE_BYTES) -> str:
    """ Upload a streamlit UploadedFile to game_id/random; returns path. """
    if uploaded_file.size > max_bytes:
        raise ValueError(f'Image must {max_bytes// (1024*1024)} or smaller.')

    ext = uploaded_file.name.rsplit('.', 1)[-1].lower()
    prefix = f'{game_id}/{folder}/' if folder else f'{game_id}/'
    path = f'{prefix}{uuid.uuid4().hex}.{ext}'
    get_supabase().storage.from_(GAME_IMAGES).upload(
        path,
        uploaded_file.getvalue(),
        {'content-type': uploaded_file.type}
    )
    return path


def delete_game_image(*paths: str | None) -> None:
    """ Updated to allow the deletion of multiple images. """
    paths = [p for p in paths if p]
    if paths:
        try:
            get_supabase().storage.from_(GAME_IMAGES).remove(paths)
        except Exception:
            pass # don't want to block user ~ will add something more structural later


def game_image_url(path: str | None) -> str | None:
    """ Image URL, cached per user session. """
    if not path:
        return None

    cache = st.session_state.setdefault('signed_urls', {})
    cached = cache.get(path)

    # Testing for now, will refresh 5 minutes before image expires.
    if cached is None or time.time() - cached[1] > SIGNED_URL_SECONDS - 300:
        res = get_supabase().storage.from_(GAME_IMAGES).create_signed_url(
            path,
            SIGNED_URL_SECONDS
        )
        cache[path] = (res.get('signedUrl') or res.get('signedURL'), time.time())
    return cache[path][0]


def prefetch_image_urls(paths) -> None:
    """ Fecth multiple images with oner request (icons etc. and cache) """
    cache = st.session_state.setdefault('signed_urls', {})
    now = time.time()
    missing = [p for p in set(paths) if p and 
               (p not in cache or now - cache[p][1] > SIGNED_URL_SECONDS - 300)]
    if not missing:
        return
    try:
        res = get_supabase().storage.from_(GAME_IMAGES).create_signed_urls(missing, SIGNED_URL_SECONDS)
    except:
        return # fall back to one at a time
    for item in res or []:
        url = item.get('signedUrl') or item.get('signedURL')
        if item.get('path') and url:
            cache[item['path']] = (url, now)
