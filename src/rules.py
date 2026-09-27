""" Games rules: dice, pips, skills, cost and roll logic """

from __future__ import annotations

import random
from dataclasses import dataclass

D6 = 'd6'
D20 = 'd20'
UPGRADE_STEP = 1 


def level_from_row(dice_system: str, row: dict | None) -> int:
    """ character_stats row -> level. No row means no bonus for a skill """
    if not row:
        return 0
    if dice_system == D6:
        return row['dice'] * 3 + row['pips']
    return row['value']


def row_from_level(dice_system: str, level: int) -> dict:
    """ Level -> the dice/pips/value columns to store """
    if dice_system == D6:
        if level < 0:
            raise ValueError('D6 values cannot be negative')
        dice, pips = divmod(level, 3)
        return {'dice': dice, 'pips': pips, 'value': 0}
    return {'dice': 0, 'pip': 0, 'value': level}


def format_level(dice_system: str, level: int) -> str:
    """ 14 becomes '4D+2 in d6 """
    if dice_system == D6:
        dice, pips = divmod(level, 3)
        return f'{dice}D+{pips}' if pips else f'{dice}D'
    return f'+{level}' if level >= 0 else str(level)


def format_change(dice_system: str, delta: int) -> str:
    """ Size of a change ~ 1D+1, +2pip """
    sign = '+' if delta >= 0 else '-'
    size = abs(delta)
    if dice_system != D6:
        return f'{sign}{size}'
    if size < 3:
        return f'{sign}{size} pip{"" if size == 1 else "s"}'
    return sign + format_level(D6, size)
