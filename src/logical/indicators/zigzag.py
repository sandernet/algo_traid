import pandas as pd
import numpy as np

# Логирование
# ====================================================
from src.utils.logger import get_logger
logger = get_logger(__name__)
# конфигурация приложения
from src.config.config import config



class ZigZag:
    def __init__(self, df):
        # Получение настроек индикатора
        # depth = config.get_setting("STRATEGY_SETTINGS", "ZIGZAG_DEPTH")
        # deviation = config.get_setting("STRATEGY_SETTINGS", "ZIGZAG_DEVIATION")
        # backstep = config.get_setting("STRATEGY_SETTINGS", "ZIGZAG_BACKTEP")
        self.dataFrame = df
        self.depth = config.get_setting("STRATEGY_SETTINGS", "ZIGZAG_DEPTH")
        self.price = config.get_setting("STRATEGY_SETTINGS", "ZIGZAG_DEVIATION")    
        self.price = config.get_setting("STRATEGY_SETTINGS", "ZIGZAG_BACKTEP")
    
    # === Методы класса ===
    # ----------------------
    # Вспомогательные методы для работы с точками ZigZag
    # ----------------------
    
    def calculate_zigzag(self):
        """Вычисляет ZigZag индикатор и добавляет его в DataFrame."""
        df = self.dataFrame.copy()
        high = df['high'].values
        low = df['low'].values
        close = df['close'].values
        length = len(df)

