# модуль загрузки данных из Bybit и сохранения их в csv-файлы


from src.Bybit.get.get_kline import get_klines_bybit
from src.Bybit.get.get_datatime import preparation_date

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
start_datetime, end_datetime    = preparation_date()


logger.info(f"Получения данных с биржи по symbol {config.SYMBOL} по timeframe {config.TIMEFRAME}, период start {start_datetime} finish {end_datetime}, Limit_data {config.LIMIT}")
kline_data = get_klines_bybit(
    session,
    config.CATEGORY,
    config.SYMBOL,
    config.TIMEFRAME,
    start_datetime, 
    end_datetime,
    config.LIMIT
    )


logger.info(kline_data)