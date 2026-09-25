import random

def roll_d6(dice: int, pips: int) -> tuple[list[int], int]:
    """ Roll six-sided dice and add pips, returns individual rolls, total. """
    results = [random.randint(1,6) for _ in range(dice)]
    return results, sum(results) + pips

def format_dice(dice: int, pips: int) -> str:
    return f'{dice}D+{pips}' if pips else f'{dice}D'
