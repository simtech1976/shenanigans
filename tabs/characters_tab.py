""" Characters tab on the game page: list characters and create new ones. """
import streamlit as st
from players_tab import md_escape


def open_character(character_id: int):
    st.session_state.current_character_id = character_id
    st.switch_page('views/character.py')


def render_characters_tab(sb, game_id: int, uid: str, is_dm: bool):
    """ The DB shows players their own characters and the GM sees all characters. """
    characters = (
        sb.table('characters')
        .select('id, name, species, owner_id, profiles(username)')
        .eq('game_id', game_id)
        .order('name')
        .execute().data
    )
    balances = {}
    if characters:
        balances = {b['character_id']: b['balance'] for b in 
                    sb.table('character_point_balances').select('*')
                    .in_('character_id', [c['id'] for c in characters])
                    .execute().data}


    # Create
    label = '➕ Create new character' + (' or NPC' if is_dm else '')
    with st.expander(label, expanded=not characters):
        with st.form('create_character', clear_on_submit=True):
            name = st.text_input('Character name', max_chars=60, placeholder='Enter a name for your character')
            species = st.text_input('Species (optional)', max_chars=60, placeholder='e.g. Human, Elf, Goblin, etc.')
            notes = st.text_area('Notes (optional)', placeholder='Background and appearance details...')
            create = st.form_submit_button('Create')
        if create:
            if not name.strip():
                st.error('Please enter a character name')
            else:
                try:
                    new = sb.table('characters').insert({
                        'game_id': game_id,
                        'name': name.strip,
                        'species': species.strip() or None,
                        'notes': notes.strip() or None
                    }).execute().data[0]
                except Exception as err:
                    st.error(f'Could not create character: {err}')
                else:
                    st.toast(f'Character "{new["name"]}" created', icon='✨')
                    open_character(new['id'])
        if is_dm:
            st.caption('Character you create belong to you, which makes them handy for NPCs.')


    # List
    if not characters:
        st.caption('No characters yet.' if is_dm else 'You have not created any characters yet.')
        return


    for character in characters:
        my_character = character['owner_id'] == uid
        with st.container(border=True):
            info_col, btn_col = st.columns([4, 1])
            line = f"**{md_escape(character['name'])}**"
            if character.get('species'):
                line += f" | {md_escape(character['species'])}"
            info_col.markdown(line)
            details = [f"{balances.get(character['id'], 0)} points"]
            if is_dm:
                player = (character.get('profiles') or {}).get('username', 'unknown player')
                details.insert(0, 'Your character / NPC' if my_character else f"Played by {player}")
            info_col.caption(' | '.join(details))
            if btn_col.button('Open Sheet', key=f"open_{character['id']}"):
                open_character(character['id'])
