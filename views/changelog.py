from pathlib import Path
import streamlit as st
from version import __version__

st.title('Shenanigans RPG - Whats New')
st.caption(f'v{__version__}')
     
changelog_path = Path(__file__).resolve().parent.parent / 'CHANGELOG.md'
try:
    text = changelog_path.read_text(encoding='utf-8')
except FileNotFoundError:
    st.info('No changelog found.')
    st.stop()

lines = [l for l in text.splitlines() if not l.startswith('# Changelog') and not l.startswith('[')]
st.markdown('\n'.join(lines))
