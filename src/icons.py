""" Icons or Emojis for stats and abilities """

import html
import streamlit as st
from src.db import delete_game_image, game_image_url, prefetch_image_urls, upload_game_image

MAX_ICON_BYTES = 1024 * 1024
ICON_TYPES = ['png', 'jpg', 'jpeg', 'webp']
ICON_SIZE = 22
MAX_EMOJI_CHARS = 16

def _get(item, key):
    return item.get(key) if isinstance(item, dict) else getattr(item, key, None)


def prefetch_icons(items) -> None:
    """ Sign all uploaded page icons in a single request. """
    prefetch_image_urls(_get(i, 'icon_path') for i in items)


def icon_html(item, size: int = ICON_SIZE) -> str:
    """ Upload image or emoji else nothing. """
    path = _get(item, 'icon_path')
    if path:
        url = game_image_url(path)
        if url:
            return (f'<img src="{html.escape(url)}" '
                    f'width="{size}" '
                    f'height={size}" '
                    f'style="vertical-align:middle;object-fit:contain;border-radius:4px" '
                    f'alt="">'
                    )
    emoji = _get(item, 'icon_emoji')
    return html.escape(emoji) if emoji else ''


def label_html(item, name: str | None = None, 
               bold: bool = False,
               size: int = ICON_SIZE,
               note: str | None = None) -> str:
    """ <icon> name """
    text = html.escape(name if name is not None else _get(item, 'name') or '')
    if bold:
        text = f'<strong>{text}</strong>'
    icon = icon_html(item, size)
    out = f'{icon}&nbsp; {text}' if icon else text
    if note:
        out += f' <span style="opacity:0.55;font-size:0.8em">{html.escape(note)}</span>'
    return out


def icon_inputs(item: str, current=None) -> tuple[str, object, bool]:
    """ Upload of image / emoji, if one already exists add a remove option to form """
    emoji = st.text_input(
        'emoji (optional)', 
        value=(_get(current, 'icon_emoji') or '') if current else '',
        max_chars=MAX_EMOJI_CHARS,
        placeholder='e.g. 🧗',
        key=f'{item}_emoji'
        )
    upload = st.file_uploader(
        f'Or upload and icon (PNG, JPG, JPEG or WebP, max {MAX_ICON_BYTES}MB)',
        type=ICON_TYPES,
        key=f'{item}_upload'
        )
    remove = False
    if current and _get(current, 'icon_path'):
        remove = st.checkbox('Remove uploaded icon', key=f'{item}_remove')
    return emoji.strip(), upload, remove


class IconChange:

    def __init__(self, game_id: int, emoji: str, upload, remove: bool,
                 current_path: str | None = None):
        self.game_id, self.emoji, self.upload = game_id, emoji, upload
        self.remove, self.current_path = remove, current_path
        self.new_path = None

    def fields(self) -> dict:
        if len(self.emoji) > MAX_EMOJI_CHARS:
            raise ValueError('Emoji should be one or two characters.')
        out = {'icon_emoji': self.emoji or None}
        if self.upload:
            self.new_path = upload_game_image(
                self.game_id, self.upload, folder='icons', max_bytes=MAX_ICON_BYTES
            )
            out['icon_path'] = self.new_path
        elif self.remove:
            out['icon_path'] = None
        return out

    def commit(self) -> None:
        if (self.upload or self.remove) and self.current_path:
            delete_game_image(self.current_path)

    def rollback(self) -> None:
        delete_game_image(self.new_path)
