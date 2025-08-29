from config import Config
from Bybit.client import Connector_Bybit

from Bybit.get.get_kline import get_klines_strategy

# Логирование 
import logging


# Создание логгера
logger = logging.getLogger(__name__)

config = Config()

category    = config.CATEGORY
symbol      = config.SYMBOL

def run_get_data(timeframe, start_datetime, end_datetime,  limit_data):
    logger.info(f"Получения данных с биржи по timeframe {timeframe} ")
    logger.info(f"Период start {start_datetime} finish {end_datetime} ")
    logger.info(f"Limit_data {limit_data}")
    # Получаем данные по рабочему timeframe
    # создаем сессию подключения 
    session = Connector_Bybit(config)
    kline_data = get_klines_strategy(
        session, 
        category, 
        symbol, 
        timeframe, 
        start_datetime, 
        end_datetime, 
        limit_data, 
        reverse=True
        )
    
    return kline_data