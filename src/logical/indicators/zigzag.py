import pandas as pd
import numpy as np

# Логирование
# ====================================================
from src.utils.logger import get_logger
logger = get_logger(__name__)
# конфигурация приложения
from src.config.config import config



class ZigZag:
    def __init__(self):
        # Получение настроек индикатора
        # depth = config.get_setting("STRATEGY_SETTINGS", "ZIGZAG_DEPTH")
        # deviation = config.get_setting("STRATEGY_SETTINGS", "ZIGZAG_DEVIATION")
        # backstep = config.get_setting("STRATEGY_SETTINGS", "ZIGZAG_BACKTEP")
        self.depth = config.get_setting("STRATEGY_SETTINGS", "ZIGZAG_DEPTH")
        self.price = config.get_setting("STRATEGY_SETTINGS", "ZIGZAG_DEVIATION")    
        self.price = config.get_setting("STRATEGY_SETTINGS", "ZIGZAG_BACKTEP")
    
    # === Методы класса ===
    # ----------------------
    # Вспомогательные методы для работы с точками ZigZag
    # ----------------------
    
    
    # ----------------------
    # Расчет индикатора ZigZag
    # ----------------------
    def calculate_zigzag(self, df):
        """Вычисляет ZigZag индикатор и добавляет его в DataFrame."""
        # Используем ExcelWriter, чтобы избежать предупреждений
        writer = pd.ExcelWriter("zigzag.xlsx", engine='openpyxl')
        df.to_excel(writer, sheet_name='OHLCV Data', index=True)
        writer.close()

        high = df['high'].values
        low = df['low'].values
        close = df['close'].values
        length = len(df)

