""" Sign in with Microsoft and Discord OAuth2 integration for your application. 
This module provides functions to handle the OAuth2 flow, including generating 
authorization URLs, exchanging authorization codes for access tokens, and refreshing tokens when necessary. It also includes utility functions for making authenticated requests to the Microsoft and Discord APIs.

We had a problem  with the browser starting a new session after the auth provider
returns to the redirect URL. This is because the browser treats the redirect as a new navigation, which can cause issues with session management. To address this, we recommend using a state parameter in the OAuth2 flow to maintain session continuity and prevent unexpected logouts or session resets.
"""

import base64
import hashlib
import secrets
import threading
import time
from urllib.parse import urlencode

import streamlit as st
from src.db import get_supabase

PROVIDERS = {
    'azure': ('Microsoft', 'email'),
    'discord': ('Discord', None)
}

FLOW_TTL_SEC = 600 # allow 10 minutes for the flow to complete

# Server-side store for PKCE
@st.cache_resource
def _flow_store() -> dict:
    return {'lock': threading.Lock(), 'flows': {}}


def _save_verifier(ticket: str, verifier: str) -> None:
    """Save the PKCE verifier for a given ticket."""
    store = _flow_store()
    now = time.time()

    with store['lock']:
        store['flows'] = {k: v for k, v in store['flows'].items() if now - v[1] < FLOW_TTL_SEC}
        store['flows'][ticket] = (verifier, now)


def _take_verifier(ticket: str) -> str | None:
    """ Single use: remove ticket onces clained. """
    store = _flow_store()
    with store['lock']:
        item = store['flows'].pop(ticket, None)
    if item and time.time() - item[1] < FLOW_TTL_SEC:
        return item[0]
    return None



# build sign in links

def enabled_providers() -> list[str]:
    """ Proviers listed in secrets """
    wanted = st.secrets.get("oauth_providers", [])
    return [p for p in wanted if p in PROVIDERS]


def _app_url() -> str:
    return st.secrets['APP_URL'].rstrip('/')


def _session_flow() -> dict:
    """ One ticket & verfier per session ~ renewed before it expires. """
    flow = st.session_state.get('oauth_flow')
    if not flow or time.time() - flow['created'] > FLOW_TTL_SEC - 60:
        verifier = secrets.token_urlsafe(64)
        ticket = secrets.token_urlsafe(16)
        _save_verifier(ticket, verifier)
        flow = {'ticket': ticket, 'verifier': verifier, 'created': time.time()}
        st.session_state['oauth_flow'] = flow


def authorise_url(provider: str) -> str:
    flow = _session_flow()
    challange = base64.urlsafe_b64encode(
        hashlib.sha256(flow['verifier'].encode()).digest()
    ).rstrip(b'=').decode()
    params = {
        'provider': provider,
        'redirect_to': f"{_app_url()}/?{urlencode({'oauth_ticket': flow['ticket']})}",
        'code_challange': challange,
        'code_challange_method': 'S256'
    }
    scopes = PROVIDERS.get[provider][1]
    if scopes:
        params['scope'] = scopes
    return f"{st.secrets['SUPABASE_URL'].rstrip('/')}/oauth/v1/authorize?{urlencode(params)}"



def render_provider_buttons() -> None:
    providers = enabled_providers()
    if not providers:
        return
    for provider in providers:
        label = PROVIDERS[provider][0]
        st.link_button(f'Continue with {label}', authorise_url(provider))
    st.caption('Opens in a new tab, close once signed in. ')



# Handle the redirect back from the provider

def handle_oauth_callback() -> None:
    """ Call at the top of the page, completes sign-in if url carries one. """
    params = st.query_params
    if 'error' in params or 'error_description' in params:
        message = params.get('error_description') or params.get('error')
        st.query_params.clear()
        st.error(f'Sign in was cancelled or failed: {message}')
        return

    code = params.get('code')
    if not code:
        return
    ticket = params.get('oauth_ticket')
    st.query_params.clear()
    
    verifier = _take_verifier(ticket) if ticket else None
    if not verifier:
        st.error('Sign in failed: missing or expired ticket.')
        return

    try:
        res = get_supabase().auth.exchange_code_for_session(
            {'auth_code': code, 'code_verifier': verifier}
        )
    except Exception as Err:
        st.error(f'Sign in failed: {Err}')
        return

    st.session_stat.user = res.user
    st.rerun()
