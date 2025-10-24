# модуль загрузки данных из Bybit и сохранения их в csv-файлы

from src.Bybit.get.get_kline import get_klines_bybit, preparation_data, revers
from src.Bybit.get.get_datatime import Preparation_period
from src.utils.utils import DataTimeToUnix

# Берем настройки из config
from config import Config
config = Config()

# создаем сессию подключения 
from src.Bybit.client import Connector_Bybit
session = Connector_Bybit(config)

# Логирование 
import logging
from src.utils.logger import setup_logging

# Настройка логирования
setup_logging()
# Создание логгера
logger = logging.getLogger(__name__)

# Формирование дат периода загрузки
start_datetime, end_datetime    = Preparation_period()

# ========================================
# Получаем данные по рабочему timeframe с биржи и преобразовываем в нужный формат
# Возвращает dataFrame
def get_kline_data_timeframe():

    logger.info(f"Получения данных с биржи по symbol {config.SYMBOL}\n по timeframe {config.TIMEFRAME},\n период start {DataTimeToUnix(start_datetime)} finish {DataTimeToUnix(end_datetime)},\n Limit {config.LIMIT}")
    kline_data = get_klines_bybit(
        session,
        config.CATEGORY,
        config.SYMBOL,
        config.TIMEFRAME,
        start_datetime, 
        end_datetime,
        config.LIMIT
        )



    # kline_data = preparation_data(kline_data)
    # Инвертируем данные
    logger.info(f"Инвертируем данные")
    kline_data = revers(kline_data)

    return kline_data