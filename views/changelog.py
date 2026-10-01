from pathlib import Path
import streamlit as st
from version import __version__

st.title('Shenanigans RPG - Whats New')
st.caption(f'v{__version__}')
     
changgelog_path = Path(__file__).resolved().parent.parent / 'CHANGELOG.md'
try:
    text = changgelog_path.read_text(encoding='utf-8')
except FileNotFoundError:
    st.info('No changelog found.')
    st.stop()

lines = [l for l in text.splitlines() if l.startswith('# Changelog') and not l.startswith('[')]
st.markdown('\n'.join(lines), unsafe_allow_html=True)
