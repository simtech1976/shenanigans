""" Load character data from Supabase and applied changes defined in rules.py """
from rules import SheetStat, StatChange, build_sheet
from stats_manager import load_stats


def load_sheet(sb, game: dict, character_id: int) -> list[tuple[SheetStat, list[SheetStat]]]:
    main_stats, skills = load_stats(sb. game['id'])
    rows = (
        sb.table('character_stats')
        .select('*')
        .eq('character_id', character_id)
        .execute().data
    )
    return build_sheet(game, main_stats, skills, rows)


def point_balance(sb, character_id: int) -> int:
    rows = (
        sb.table('character_point_balances')
        .select('balance')
        .eq('character_id', character_id)
        .execute().data
    )
    return rows[0]['balance'] if rows else 0


def apply_change(sb, character_id: int, change: StatChange) -> dict:
    """ Save planned change ~ DB will check permissions and balance, saving the stat, spend and activity log 
    Raises msg such as 'not enough points' """

    return sb.rpc(
        'apply_stat_change',
        {
            'p_character_id': character_id,
            'p_stat_id': change.stat_id,
            'p_dice': change.stored['dice'],
            'p_pips': change.stored['pips'],
            'p_value': change.stored['value'],
            'p_cost': change.cost,
            'p_description': change.description, 
        }
    ).execute().data
