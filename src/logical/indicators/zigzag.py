# Логирование
# ====================================================
from src.utils.logger import get_logger
logger = get_logger(__name__)

from src.config.config import config


def zigzag(df):
    # Получение настроек индикатора
    depth = config.get_setting("STRATEGY_SETTINGS", "ZIGZAG_DEPTH")
    deviation = config.get_setting("STRATEGY_SETTINGS", "ZIGZAG_DEVIATION")
    backstep = config.get_setting("STRATEGY_SETTINGS", "ZIGZAG_BACKTEP")
    

        