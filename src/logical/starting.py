import joblib

from src.logical.loading_data import get_kline_data_timeframe
from src.logical.education import education
from src.logical.predictions import make_prediction

# Логирование 
import logging
from src.utils.logger import setup_logging


# Настройка логирования
setup_logging()
# Создание логгера
logger = logging.getLogger(__name__)

def starting():

    logger.info("Получаем данные для обучения")
    data = get_kline_data_timeframe()
    
    # logger.info("Запускаем обучение моделей")
    # обучение моделей
    # education(data)
    logger.info("Получаем предсказания")
    
    clf = joblib.load("clf_model.pkl")
    reg = joblib.load("reg_model.pkl")
    
    proba_down, proba_up, y_pred_reg = make_prediction(data,clf, reg)
    logger.info(f"Вероятность роста: {round( proba_up, 2)}%")
    logger.info(f"Вероятность падения: {round(proba_down, 2)}%")

    logger.info(f"Ожидаемая доходность: {round(y_pred_reg, 2)}%")