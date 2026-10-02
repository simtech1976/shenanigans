import streamlit as st
from src.character_service import load_sheet, point_balance
from src.db import get_supabase
from src.icons import label_html, prefetch_icons
from src.players_tab import md_escape
from src.rules import D6, describeroll, format_change, roll, roll_note