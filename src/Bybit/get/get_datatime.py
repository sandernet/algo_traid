# from utils.utilsDate import get_time_interval
from config import Config
from src.Bybit.client import Connector_Bybit

from datetime import timedelta
import pandas as pd

config = Config()

# Логирование 
import logging
# Создание логгера
logger = logging.getLogger(__name__)

# создаем сессию подключения 
session = Connector_Bybit(config)


# Функция для получения текущей даты и даты 50 дней назад в формате timestamp
def get_time_interval(current_time, interval_day):
    
    current_time = int(current_time)
    current_time = pd.to_datetime(current_time, unit='ns')

    # current_time = datetime.utcnow()  # Текущая дата и время (UTC)
    start_time = current_time - timedelta(days=interval_day)  


    # Преобразуем даты в Unix timestamp (в миллисекундах)
    start_datetime = int(start_time.timestamp() * 1000)
    end_datetime = int(current_time.timestamp() * 1000)
    
    return start_datetime, end_datetime


# берем текущее время с биржи
def get_current_datetime(interval_day):
    try:
        current_datetime = session.get_server_time()["result"]["timeNano"]
        start_timestamp, end_timestamp = get_time_interval(current_datetime, interval_day )
        return start_timestamp, end_timestamp
    except Exception as e:
        logger.error("Ошибка в получении текущей даты с биржи модуль get_datatime")
        return None


# Функция для подготовки временного периода
def Preparation_period():
    # если в конфиге заданы параметры времени берем их
    if config.START_DATETIME is not None and config.END_DATETIME is not None:
        start_datetime  = config.START_DATETIME
        end_datetime    = config.END_DATETIME
    else:
        # Подготавливаем временной период в виде начальной и конечной датой и времени
        start_datetime, end_datetime = get_current_datetime(config.INTERVAL_DAY) or (None, None)
    return  start_datetime, end_datetime