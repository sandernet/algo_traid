# Логирование
# ====================================================
from src.utils.logger import get_logger
logger = get_logger(__name__)
# конфигурация приложения
from src.config.config import config

# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# data_df - DataFrame с данными для расчета индикаторов Подается нужное кол-во баров для расчета
# расчет стратегии ZigZag и Фибоначчи 
# на выходе получаем dtaframe с рассчитанными индикаторами
# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++
def calculete_strategy(data_df):
    """
    Запуск стратегии ZigZag и уровней Фибоначчи на переданных данных.
    """
    try:
        # Расчет индикаторов ZigZag
        from src.logical.indicators.zigzag import ZigZag
        zigzag_indicator = ZigZag()
        # z1, z2, direction, z2_index = zigzag_indicator.calculate_zigzag(data_df)
        zigzag = zigzag_indicator.calculate_zigzag(data_df)
        
        # Расчет уровней Фибоначчи
        fiboLev = fibonacci_levels(zigzag["z1"], zigzag["z2"], zigzag["direction"]) # fiboLev = fibonacci_levels(z1, z2, direction)

        # return direction, z1, z2, fiboLev
        return zigzag, fiboLev
    except Exception as e:
        logger.error(f"Ошибка при запуске стратегии ZigZag и Фибоначчи: {e}")
        return None, None


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
            level = z1 + (z2 - z1) * r
            levels[round(r * 100, 1)] = level
    elif direction == -1:
        # коррекция вверх
        for r in fib_ratios:
            level = z1 - (z1 - z2) * r
            levels[round(r * 100, 1)] = level
    else:
        raise ValueError("direction должен быть 'up' или 'down'")

    return levels



