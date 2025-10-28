from src.logical.indicators.zigzag import ZigZag


# Логирование
# ====================================================
from src.utils.logger import get_logger
logger = get_logger(__name__)
# конфигурация приложения
from src.config.config import config

# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# расчет стратегии ZigZag и Фибоначчи 
# на выходе получаем dtaframe с рассчитанными индикаторами
# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++
def start_zz_and_fibo(data_df):
    """
    Запуск стратегии ZigZag и уровней Фибоначчи на переданных данных.
    """
    logger.info("〽️ Запуск стратегии ZigZag и уровней Фибоначчи.")
    
    signal = None
    
    # Инициализация ZigZag с переданным DataFrame
    zigzag_distance = config.get_setting("STRATEGY_SETTINGS", "ZIGZAG_DISTANCE")
    # для расчета ZigZag отсекаем только нужный участок данных
    # zigzag_dataframe = data_df.tail(zigzag_distance)
    
    logger.info(f"Данные для расчета ZigZag: {len(data_df)} записей после отсечения первых записей.")    
    zigzag_indicator = ZigZag()
    zigzag_df = zigzag_indicator.calculate_zigzag(data_df)

    
    # Здесь можно добавить расчет уровней Фибоначчи, если это необходимо
    # fibo_levels = calculate_fibonacci_levels(zigzag_df)
    
    logger.info("Расчет ZigZag и уровней Фибоначчи завершен.")
    
    return signal  # , fibo_levels (если добавлен расчет Фибоначчи)