import streamlit as st

DEFAULT_ICON = '🌐'
CUSTOM_ICON = '🎲'


def load_stats(sb, game_id: int):
    """ Default and this games stats.
    return main stats, skill_by_main_id ~ sorted by display order then name 
    Also used in the character sheet"""

    rows = (
        sb.table('stat_definitions')
        .select('*')
        .or_(f'game_id.is.null.game_id.eq.{game_id}')
        .order('sort_order')
        .order('name')
        .execute().data
    )
    
    mains = [r for r in rows if r['parent_id'] is None]
    skills: dict[int, list] = {}
    
    for r in rows:
        if r['parent_id'] is not None:
            skills.setdefault(r['parent_id'], []).append(r)
    
    return mains, skills


def _friendly(err) -> str:
    text = str(err)
    if '23505' in text or 'duplicate key' in text:
        return 'Name already used.'
    return text


def _add_star(sb, game_id, parent_id, name, description, order):
    if not name.strip():
        st.error('Please enter a name')
        return
    