# ================= ИМПОРТ =================
import joblib
from src.logical.loading_data import get_kline_data_timeframe
from src.logical.education import education
from src.logical.predictions import make_prediction
from src.Bybit.get.get_kline import get_klines_bybit
import pandas as pd
import time
from datetime import datetime

# Логирование 
import logging
from src.utils.logger import setup_logging
# Настройка логирования
setup_logging()
# Создание логгера
logger = logging.getLogger(__name__)

# Берем настройки из config
from config import Config
config = Config()

# создаем сессию подключения 
from src.Bybit.client import Connector_Bybit
session = Connector_Bybit(config)


# Загрузка OHLCV данных с Bybit через REST API за указанный период.
def get_bybit_ohlcv(symbol: str, timeframe: int, start, end) -> pd.DataFrame:

# Чтение дат из конфига
    start_date = datetime.strptime(start, "%d-%m-%Y")
    end_date = datetime.strptime(end, "%d-%m-%Y")
    
    start_ts = int(pd.Timestamp(start_date).timestamp()) * 1000
    end_ts   = int(pd.Timestamp(end_date).timestamp()) * 1000

    all_data = []
    cur = start_ts

    while cur < end_ts:

        logger.info(f"Получаем данные по timeframe {timeframe} за период {start} - {end}")
        df = get_klines_bybit(
            session,
            config.CATEGORY,
            symbol,
            timeframe,
            cur,
            end_ts,
            config.LIMIT)
        
        logger.info(df)
        if df is None:
            break
        
        all_data.append(df)

        # передвигаем указатель
        cur = int(df["DateTime"].iloc[-1].timestamp()) * 1000 + 1
        time.sleep(0.1)  # пауза, чтобы не словить rate-limit

    if not all_data:
        return pd.DataFrame()

    df_all = pd.concat(all_data, ignore_index=True)
    df_all = df_all.drop_duplicates(subset="ts").sort_values("ts")
    df_all = df_all.set_index("ts")
    return df_all


def starting():

    logger.info("Получаем данные для обучения")
    data = get_bybit_ohlcv(config.SYMBOL, config.TIMEFRAME, config.START_DATETIME, config.END_DATETIME) 
    
    # logger.info("Запускаем обучение моделей")
    # # обучение моделей
    # education(data)
    
    
    logger.info("Получаем предсказания")
    clf = joblib.load("clf_model.pkl")
    reg = joblib.load("reg_model.pkl")
    
    proba_down, proba_up, y_pred_reg = make_prediction(data,clf, reg)
    logger.info(f"Вероятность роста: {round( proba_up, 2)}%")
    logger.info(f"Вероятность падения: {round(proba_down, 2)}%")

    logger.info(f"Ожидаемая доходность: {round(y_pred_reg, 2)}%")