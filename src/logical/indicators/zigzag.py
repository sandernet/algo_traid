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
    #   ZIGZAG_DEPTH: 12
    #   ZIGZAG_DEVIATION: 5
    #   ZIGZAG_BACKTEP: 2
        self.depth = config.get_setting("STRATEGY_SETTINGS", "ZIGZAG_DEPTH")
        self.deviation = config.get_setting("STRATEGY_SETTINGS", "ZIGZAG_DEVIATION")    
        # self.price = config.get_setting("STRATEGY_SETTINGS", "ZIGZAG_BACKTEP")
    
    # === Методы класса ===
    # ----------------------
    # Вспомогательные методы для работы с точками ZigZag
    # ----------------------
    
    
    def _highestbars(self, series: pd.Series, length: int):
        """
        Аналог ta.highestbars() из Pine Script.
        Возвращает смещение (количество баров назад), 
        где находится максимум за последние length баров.
        """
        # Проверка на достаточную длину
        if len(series) < length:
            return np.nan
        
        # Смотрим последний срез данных
        window = series[-length:]
        # Индекс максимального значения в окне
        idx_max = window.idxmax()
        # Смещение относительно последнего бара
        offset = series.index[-1] - idx_max
        return offset
    
    def _lowestbars(self, series: pd.Series, length: int):
        """
        Аналог ta.highestbars() из Pine Script.
        Возвращает смещение (количество баров назад), 
        где находится максимум за последние length баров.
        """
        # Проверка на достаточную длину
        if len(series) < length:
            return np.nan
        
        # Смотрим последний срез данных
        window = series[-length:]
        # Индекс максимального значения в окне
        idx_min = window.idxmin()
        # Смещение относительно последнего бара
        offset = series.index[-1] - idx_min
        return offset
    
    
    # ----------------------
    # Расчет индикатора ZigZag
    # ----------------------
    def calculate_zigzag(self, df, mintick=0.01):
        """Вычисляет ZigZag индикатор и добавляет его в DataFrame."""

        # # Данные должны идти по времени (старые -> новые)
        # df = df.iloc[::-1].reset_index(drop=True)
        
        # определяем направление
        
        highs = df['high'].values
        lows = df['low'].values
        
        df['highs'] = None
        df['lows'] = None
        
        maxin = self._highestbars(pd.Series(highs), self.depth)
        minin = self._lowestbars(pd.Series(lows), self.depth)
        
        
        logger.info(f"ZigZag maxin: {maxin}, minin: {minin}")
        logger.info(f"ZigZag highs: {highs[len(highs) - maxin-1]}, \
                    lows: {lows[len(lows) - minin-1]} ")
        
        
        x = highs[len(highs) - maxin - 1]
        y = highs[-1]
        
        d = self.deviation*mintick
        
        if highs[len(highs) - maxin-1] - highs[-1] > self.deviation*mintick:
            logger.info("ZigZag detected HIGH")
            df[-1,'highs'] = highs[-1]
            
        if lows[-1] - lows[len(lows) - minin-1] > self.deviation*mintick:
            logger.info("ZigZag detected LOW")
            df[-1,'lows'] = lows[-1]
       
        # h = highs[len(highs) - maxin-1] - highs[-1] > self.deviation*mintick
        # l = lows[-1] - lows[len(lows) - minin-1] > self.deviation*mintick 
        
        logger.info(f"ZigZag h: df[-1,'highs']: {df[-1,'highs']}, \
                    l: df[-1,'lows']: {df[-1,'lows']}") 
        
        # # Храним экстремумы
        # peaks = []
        # troughs = []
        
        # for i in range(self.depth, len(df) - self.depth):
        #     local_high = highs[i - self.depth:i + self.depth + 1].max()
        #     local_low = lows[i - self.depth:i + self.depth + 1].min()
            
        #     # Проверяем, является ли текущий бар экстремумом
        #     if highs[i] == local_high:
        #         if not peaks or (abs(highs[i] - peaks[-1][1]) / peaks[-1][1] * 100 > self.deviation):
        #             peaks.append((i, highs[i]))
        #     if lows[i] == local_low:
        #         if not troughs or (abs(lows[i] - troughs[-1][1]) / troughs[-1][1] * 100 > self.deviation):
        #             troughs.append((i, lows[i]))
        
        # # Объединяем пики и впадины в один список и сортируем по индексу
        # all_points = sorted(peaks + troughs, key=lambda x: x[0])
        
        
        direction, z1, z2, signal = None, None, None, None
        
        return direction, z1, z2, signal
