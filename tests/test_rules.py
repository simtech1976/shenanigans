import random
import pytest
from src.rules import (plan_sheet_edits, D6, D20, bonus_for_target, build_sheet, describe_roll,
                       format_change, format_level, level_from_row, plan_direct_edit, plan_upgrade,
                       row_from_level, roll_notes, upgrade_cost, roll)

GAME_D6 = {'id': 1, 'dice_system': D6, 'skill_pip_cost': 2, 'main_pip_cost': 10}
GAME_D20 = {'id': 2, 'dice_system': D20, 'skill_pip_cost': 1, 'main_pip_cost': 5}


def lv(dice, pips=0):
    return dice * 3 + pips


# Formatting and storage
def test_format_d6():
    assert format_level(D6, lv(4, 2)) == '4D+2'
    assert format_level(D6, lv(4)) == '4D'


def test_format_d20():
    assert format_level(D20, 5) == '+5'
    assert format_level(D20, -1) == '-1'


def test_three_pips_roll_into__die():
    assert row_from_level(D6, lv(4, 2) + 1) == {'dice': 5, 'pips': 0, 'value': 0}


def test_row_round_trip():
    for level in range(30):
        assert level_from_row(D6, row_from_level(D6, level)) == level


def test_format_change():
    assert format_change(D6, 1) == '+1 pip'
    assert format_change(D6, 2) == '+2 pips'
    assert format_change(D6, 3) == '+1D'
    assert format_change(D6, 4) == '+1D+1'
    assert format_change(D20, 5) == '+5'
    assert format_change(D20, -3) == '-3'


# Rules 
def test_skill_follows_main_stat():
    # Main 2D, skill 3D+1 -> bonus 1D+1. Main raised by 1D+1 to 3D+1 -> skill 4D+2.
    bonus = bonus_for_target(lv(2), lv(3, 1))
    assert bonus == lv(1, 1)
    assert format_level(D6, lv(3, 1) + bonus) == '4D+2'
 
 
def test_skill_cannot_be_below_main():
    with pytest.raises(ValueError):
        bonus_for_target(lv(3), lv(2, 2))
 
 
def test_upgrade_cost_scales_with_dice():
    assert upgrade_cost(D6, False, lv(4, 1), 2, 10) == 8 # 4 dice x 2
    assert upgrade_cost(D6, False, lv(6), 2, 10) == 12
    assert upgrade_cost(D6, True, lv(2), 2, 10) == 20 # main stat rate
    assert upgrade_cost(D6, False, lv(0, 2), 2, 10) == 2 # 0D counts as 1D
 
 
def test_upgrade_cost_d20():
    assert upgrade_cost(D20, False, 3, 1, 5) == 3
    assert upgrade_cost(D20, True, 0, 1, 5) == 5
 
 
def test_roll_d6():
    rng = random.Random(1)
    dice, total = roll(D6, lv(4, 2), rng)
    assert len(dice) == 4 and all(1 <= d <= 6 for d in dice)
    assert total == sum(dice) + 2
 
 
def test_roll_d20():
    rng = random.Random(1)
    dice, total = roll(D20, 5, rng)
    assert len(dice) == 1 and 1 <= dice[0] <= 20
    assert total == dice[0] + 5
 
 
# Sheet and planned changes
MAINS = [{'id': 10, 'name': 'Strength', 'game_id': None, 'parent_id': None}]
SKILLS = {10: [{'id': 11, 'name': 'Climbing', 'game_id': None, 'parent_id': 10},
               {'id': 12, 'name': 'Running', 'game_id': None, 'parent_id': 10}]}
 
 
def sheet_with(rows):
    return build_sheet(GAME_D6, MAINS, SKILLS, rows)
 
 
def test_unimproved_skill_equals_main():
    [(main, skills)] = sheet_with([{'stat_id': 10, 'dice': 2, 'pips': 0, 'value': 0}])
    assert main.code == '2D'
    assert [s.code for s in skills] == ['2D', '2D']
    assert not skills[1].is_improved
 
 
def test_improved_skill_shows_main_plus_bonus():
    rows = [{'stat_id': 10, 'dice': 2, 'pips': 0, 'value': 0},
            {'stat_id': 11, 'dice': 1, 'pips': 1, 'value': 0}]
    [(_, skills)] = sheet_with(rows)
    assert skills[0].code == '3D+1' and skills[0].is_improved
    assert skills[0].next_cost == 6 # 3 dice x rate 2
 
 
def test_plan_upgrade_skill_stores_bonus():
    rows = [{'stat_id': 10, 'dice': 2, 'pips': 0, 'value': 0},
            {'stat_id': 11, 'dice': 1, 'pips': 1, 'value': 0}]
    [(_, skills)] = sheet_with(rows)
    change = plan_upgrade(GAME_D6, skills[0])
    assert change.stored == {'dice': 1, 'pips': 2, 'value': 0} # bonus 1D+2
    assert change.cost == 6
    assert change.description == 'changed Climbing from 3D+1 to 3D+2'
 
 
def test_plan_upgrade_main_mentions_skills():
    [(main, _)] = sheet_with([{'stat_id': 10, 'dice': 2, 'pips': 2, 'value': 0}])
    change = plan_upgrade(GAME_D6, main)
    assert change.stored == {'dice': 3, 'pips': 0, 'value': 0}
    assert change.description == 'changed Strength from 2D+2 to 3D (all Strength skills +1 pip)'
 
 
def test_plan_direct_edit_skill():
    [(_, skills)] = sheet_with([{'stat_id': 10, 'dice': 2, 'pips': 0, 'value': 0}])
    change = plan_direct_edit(GAME_D6, skills[0], lv(3, 1))
    assert change.stored == {'dice': 1, 'pips': 1, 'value': 0}
    assert change.cost == 0
 
 
# Describing rolls
 
def test_describe_roll_d6():
    assert describe_roll(D6, lv(4, 2), [4, 6, 2, 5], 19) == '4 + 6 + 2 + 5 + 2 = 19'
    assert describe_roll(D6, lv(3), [1, 2, 3], 6) == '1 + 2 + 3 = 6'
    assert describe_roll(D6, lv(0, 2), [], 2) == '0 + 2 = 2'
 
 
def test_describe_roll_d20():
    assert describe_roll(D20, 5, [17], 22) == '17 + 5 = 22'
    assert describe_roll(D20, -1, [10], 9) == '10 − 1 = 9'
 
 
def test_roll_note():
    assert roll_notes(D20, [20]) == 'Natural 20!'
    assert roll_notes(D20, [1]) == 'Natural 1'
    assert roll_notes(D20, [12]) is None
    assert roll_notes(D6, [6, 6, 6]) is None
 
 
# Direct edits from the sheet form
 
ROWS = [{'stat_id': 10, 'dice': 3, 'pips': 0, 'value': 0}, # Strength 3D
        {'stat_id': 11, 'dice': 0, 'pips': 2, 'value': 0}] # Climbing bonus 2 pips -> 3D+2
 
 
def test_edit_main_moves_unchanged_skills():
    changes = plan_sheet_edits(GAME_D6, sheet_with(ROWS), {10: lv(4)})
    assert len(changes) == 1
    assert changes[0].stored == {'dice': 4, 'pips': 0, 'value': 0}
    assert 'all Strength skills +1D' in changes[0].description
 
 
def test_edit_skill_against_new_main():
    changes = plan_sheet_edits(GAME_D6, sheet_with(ROWS), {10: lv(4), 11: lv(5)})
    assert [c.stat_id for c in changes] == [10, 11]
    assert changes[1].stored == {'dice': 1, 'pips': 0, 'value': 0} # 5D is 1D over new 4D
    assert changes[1].description == 'changed Climbing from 3D+2 to 5D'
    assert all(c.cost == 0 for c in changes)
 
 
def test_edit_skill_below_new_main_is_refused():
    with pytest.raises(ValueError, match=r'Climbing cannot be lower than Strength \(4D\)'):
        plan_sheet_edits(GAME_D6, sheet_with(ROWS), {10: lv(4), 11: lv(3, 1)})
 
 
def test_untouched_skill_follows_main_even_if_old_value_now_below():
    # Climbing left at its old 3D+2 while Strength rises to 4D: it keeps its +2 pips (-> 4D+2)
    assert [c.stat_id for c in plan_sheet_edits(GAME_D6, sheet_with(ROWS), {10: lv(4), 11: lv(3, 2)})] == [10]
 
 
def test_setting_skill_equal_to_main_clears_bonus():
    [change] = plan_sheet_edits(GAME_D6, sheet_with(ROWS), {11: lv(3)})
    assert change.stored == {'dice': 0, 'pips': 0, 'value': 0}
 
 
def test_no_changes():
    assert plan_sheet_edits(GAME_D6, sheet_with(ROWS), {}) == []
    assert plan_sheet_edits(GAME_D6, sheet_with(ROWS), {10: lv(3), 11: lv(3, 2)}) == []
 
 
def test_edit_d20():
    sheet = build_sheet(GAME_D20, MAINS, SKILLS, [{'stat_id': 10, 'dice': 0, 'pips': 0, 'value': 2}])
    changes = plan_sheet_edits(GAME_D20, sheet, {10: 3, 12: 6})
    assert changes[0].stored['value'] == 3
    assert changes[1].stored['value'] == 3 # Running +6 is 3 over Strength +3
 