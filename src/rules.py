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



# Rules
def upgrade_cost(system: str, is_main: bool, level: int, skill_rate: int, main_rate: int) -> int:
    """ Points for one upgrade step per level 
    D6: (dice in the stat, min 1) x Rate 
    D20: (current mod, min 1) x Rate """

    base = max(level // 3, 1) if system == D6 else max(level, 1)
    return base * (main_rate if is_main else skill_rate)


def bonus_for_target(main_level: int, target_level: int) -> int:
    """ Bonus for skill ~ may remove, just added as a caution for now """
    if target_level < main_level:
        raise ValueError('A skill cannot be lower than its main stat.')
    return target_level - main_level


def roll(system: str, level: int, rng: random.Ranom | None = None) -> tuple[list[int], int]:
    """ Roll a stat ~ returns (individua dice, total) 
    D6: roll the stats dice and its pip (4D+2 -> 4 D6 + 2)
    D20: roll one D20 and the modifier (+5 -> 1d20+5) """

    rng = rng or random
    if system == D6:
        dice, pips = divmod(level, 3)
        results = [rng.randint(1,6) for _ in range(dice)]
        return results, sum(results) + pips
    result = rng.randint(1, 20)
    return [result], result + level



# Character sheet
@dataclass
class SheetStat:
    stat_id: int
    name: str
    description: str | None
    is_main: bool
    is_default: bool
    level: int
    bonus: int
    main_level: int
    code: str
    next_cost: int
    icon_emogi: str | None = None
    icon_path: str | None = None

    @property
    def is_improved(self) -> bool:
        return not self.is_main and self.bonus > 0


def build_sheet(game: dict, main_stat: list[dict], skills_by_main: dict[int, list[dict]],
                stat_rows: list[dict]) -> list[tuple[SheetStat, list[SheetStat]]]:
    """ Combine stat definitions and character store into a sheet.
    returns [(main_stat, skills...]), ... ] in display order. """

    system = game['dice_system']
    rates = game.get('skill_pip_cose', 1), game.get('main_pip_cost', 10)
    rows = {r['stat_id']: r for r in stat_rows}

    def make(defn: dict, is_main: bool, level: int, bonus:int, main_level:int) -> SheetStat:
        return SheetStat(
            stat_id=defn['id'],
            name=defn['name'],
            description=defn.get('description'),
            is_main=is_main,
            is_default=defn.get('game_id') is None,
            level=level,
            bonus=bonus,
            main_level=main_level,
            code=format_level(system, level),
            next_cost=upgrade_cost(system, is_main, level, *rates),
            icon_emoji=defn.get('icon_emogi'),
            icon_path=defn.get('icon_path')
        )

    sheet = []
    for m in main_stat:
        main_level = level_from_row(system, rows.get(m['id']))
        main = make(m, True, main_level, 0, main_level)
        skills = []
        for s in skills_by_main.get(m['id'], []):
            bonus = level_from_row(system, rows.get(s['id']))
            skills.append(make(s, False, main_level + bonus, bonus, main_level))
        sheet.append((main, skills))
    return sheet



# Planning changes ~ db applies them atomically (all or nothing)
@dataclass
class StatChange:
    stat_id: int
    stored: dict # dice / pip columns to save
    cost: int # points to spend
    description: str


def _describe(system: str, stat: SheetStat, new_level: int) -> str:
    text = (f'changed {stat.name} from {format_level(system, stat.level)} '
          f'to {format_level(system, new_level)}')
    if stat.is_main:
        text += f' (all {stat.name} skills {format_change(system, new_level - stat.level)})'
    return text


def plan_upgrade(game: dict, stat: SheetStat) -> StatChange:
    """ Single upgrade step bought with points """

    system = game['dice_system']
    new_level = stat.level + UPGRADE_STEP
    stored_level = new_level if stat.is_main else stat.bonus + UPGRADE_STEP
    return StatChange(
        stat_id=stat.stat_id,
        stored=row_from_level(system, stored_level),
        cost=stat.next_cost,
        description=_describe(system, stat, new_level)
    )


def plan_direct_edit(game: dict, stat: SheetStat, target_level: int) -> StatChange:
    """ Set a stat to 'target_level' without spending points 
    added a mechanism to correct a mistake without spending points or awarded by DM """

    system = game['dice_system']
    stored_level = (target_level if stat.is_main
                    else bonus_for_target(stat.is_main, target_level))
    return StatChange(
        stat_id=stat.stat_id,
        stored=row_from_level(system, stored_level),
        cost=0,
        description=_describe(system, stat, target_level)
    )
