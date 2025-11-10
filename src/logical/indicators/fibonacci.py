from src.config.config import config
# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# расчет уровней Фибоначчи
# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++
def fibonacci_levels(z1: float, z2: float, direction: int) -> dict:
    """
    Рассчитывает уровни коррекции Фибоначчи.

    :param z1: float — начальная точка (например, минимум)
    :param z2: float — конечная точка (например, максимум)
    :param direction: int — направление движения (1 — вверх, -1 — вниз)
    :return: dict — уровни коррекции в формате {уровень: значение}
    """
    fib_ratios = config.get_setting("STRATEGY_SETTINGS", "FIBONACCI_LEVELS")
    levels = {}

    if direction == 1:
        # коррекция вниз
        for r in fib_ratios:
            level = z1 + (z2 - z1) * r['level']
            levels[round(r['level'] * 100, 1)] = {'level_price': level, 'volume': r['volume']}
    elif direction == -1:
        # коррекция вверх
        for r in fib_ratios:
            level = z1 - (z1 - z2) * r['level']
            levels[round(r['level'] * 100, 1)] =  {'level_price': level, 'volume': r['volume']}
    else:
        raise ValueError("direction должен быть 'up' или 'down'")

    return levels
