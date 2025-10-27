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
    Запуск расчета ZigZag и уровней Фибоначчи на переданных данных.
    """
    logger.info("Запуск расчета ZigZag и уровней Фибоначчи.")
    
    # Инициализация ZigZag с переданным DataFrame
    zigzag_indicator = ZigZag(data_df)
    
    # Расчет ZigZag
    zigzag_df = zigzag_indicator.calculate_zigzag()
    
    # Здесь можно добавить расчет уровней Фибоначчи, если это необходимо
    # fibo_levels = calculate_fibonacci_levels(zigzag_df)
    
    logger.info("Расчет ZigZag и уровней Фибоначчи завершен.")
    
    return zigzag_df  # , fibo_levels (если добавлен расчет Фибоначчи)