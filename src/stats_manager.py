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
    
    main_stat = [r for r in rows if r['parent_id'] is None]
    skills: dict[int, list] = {}
    
    for r in rows:
        if r['parent_id'] is not None:
            skills.setdefault(r['parent_id'], []).append(r)
    return main_stat, skills


def _friendly(err) -> str:
    text = str(err)
    if '23505' in text or 'duplicate key' in text:
        return 'Name already used.'
    return text


def _add_stat(sb, game_id, parent_id, name, description, order):
    if not name.strip():
        st.error('Please enter a name')
        return
    try:
        sb.table('stat_definitions').insert({
            'game_id': game_id,
            'parent_id': parent_id,
            'name': name.strip(),
            'description': description.strip() or None,
            'sort_order': int(order),
        }).execute()
    except Exception as err:
        st.error(_friendly(err))
    else:
        st.rerun()


def _edit_controls(sb, stat, main_names: dict):
    """ Edit popover for one of the game's own stats. """

    is_main = stat['parent_id'] is None
    with st.popoever('Edit'):
        with st.form(f'edit_stat_{stat['id']}'):
            name = st.text_input('Name', value=stat['name'])
            desc = st.text_area('Description', value=stat.get('description') or '')
            order = st.number_input('Display order', min_value=0, value=stat['sort_order'])
            parent_id = stat['parent_id']
            if not is_main:
                ids = list(main_names)
                parent_id = st.selectbox(
                    'Main Stat', ids, format_func=main_names.get,
                    index=ids.index(parent_id) if parent_id in ids else 0
                )
                save = st.form_submit_button('Save')

        if save:
            if not name.strip():
                st.error('Please enter Name')
            else:
                try:
                    sb.table('stat_definitions').update({
                        'name': name.strip(),
                        'description': desc.strip() or None,
                        'sort_order': int(order),
                        'parent_id': parent_id,
                    }).eq('id', stat['id']).execute()
                except Exception as err:
                    st.error(_friendly(err))
                else:
                    st.rerun()

        st.divider()
        st.caption('Deleting main stat also deletes sub-stats/skills for all characters!' if is_main else
                   'Deleting the skill also removes from every character sheet!')
        confirm = st.button('Delete', key=f'confirm_del_stat_{stat['id']}')
        if st.button('Deelte', key=f'del_stat{stat['id']}', type='primary', disabled=not confirm):
            try:
                sb.table('stat_definitions').delete().eq('id', stat['id']).execute()
            except Exception as err:
                st.error(_friendly(err))
            else:
                st.rerun()


def render_stats_tab(sb, game_id: int, is_dm: bool):
    main_stats, skills = load_stats(sb, game_id)
    main_names = {main_stat['id']: main_stat['name'] for main_stat in main_stats}

    st.caption(f'{DEFAULT_ICON} default, in every game · {CUSTOM_ICON} for this game only')

    # DM: Add Stats
    if is_dm:
        add_main_stat_col, add_skill_col = st.columns(2)
        with add_main_stat_col.expander('➕ Add a main stat'):
            with st.form('add_main_stat', clear_on_submit=True):
                name = st.text_input('Name', placeholder='e.g. The Force')
                desc = st.text_area('Description (Optional)')
                next_order = max((m['sort_order'] for m in main_stats), default=0) +1
                order = st.number_input('Display Order', min_value=0, value=next_order)
                add_stat = st.form_submit_button('Add Main Stat')
            if add_stat:
                _add_stat(sb, game_id, None, name, desc, order)

        with add_skill_col.expander('➕ Add a skill'):
            with st.form('add_skill', clear_on_submit=True):
                parent_id = st.selectbox('Main Stat', list(main_names), format_func=main_names.get)
                name = st.text_input('Skill Name', placeholder='e.g. Blaster, Riding, Swimming')
                desc = st.text_area('Description (optional)')
                order = st.number_input('Display Order', min_value=0, value=0)
                add_skill = st.form_submit_button('Add Skill')
            if add_skill:
                if parent_id is None:
                    st.error('Add a main stat first')
                else:
                    _add_stat(sb, game_id, parent_id, name, desc, order)

        st.caption('Default stats are shared by every game, can only be edited from the DB')


    # List
    if not main_stats:
        st.info('No stats.')
    for m in main_stats:
        with st.container(border=True):
            head, ctrl = st.columns([6, 1])
            icon = DEFAULT_ICON if m['game_id'] is None else CUSTOM_ICON
            head