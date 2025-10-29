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
        self.deviation = config.get_setting("STRATEGY_SETTINGS", "ZIGZAG_DEVIATION")    
        # self.price = config.get_setting("STRATEGY_SETTINGS", "ZIGZAG_BACKTEP")
    
    # === Методы класса ===
    # ----------------------
    # Вспомогательные методы для работы с точками ZigZag
    # ----------------------
    
    
    # ----------------------
    # Расчет индикатора ZigZag
    # ----------------------
    def calculate_zigzag(self, df):
        """Вычисляет ZigZag индикатор и добавляет его в DataFrame."""



    # def zigzag(df, depth=12, deviation=5, backstep=2):
        """
        Аналог функции zigzag из Pine Script.
        
        df: DataFrame с колонками ['open', 'high', 'low', 'close']
        depth: окно для поиска локальных экстремумов
        deviation: минимальное отклонение (%)
        backstep: количество свечей для подтверждения направления
        
        Возвращает:
            direction: 1 (вверх) или -1 (вниз)
            last_peaks: список из двух последних точек [(index, price)]
        """
        # Данные должны идти по времени (старые -> новые)
        df = df.iloc[::-1].reset_index(drop=True)
        
        highs = df['high'].values
        lows = df['low'].values
        
        # Храним экстремумы
        peaks = []
        troughs = []
        
        for i in range(self.depth, len(df) - self.depth):
            local_high = highs[i - self.depth:i + self.depth + 1].max()
            local_low = lows[i - self.depth:i + self.depth + 1].min()
            
            # Проверяем, является ли текущий бар экстремумом
            if highs[i] == local_high:
                if not peaks or (abs(highs[i] - peaks[-1][1]) / peaks[-1][1] * 100 > self.deviation):
                    peaks.append((i, highs[i]))
            if lows[i] == local_low:
                if not troughs or (abs(lows[i] - troughs[-1][1]) / troughs[-1][1] * 100 > self.deviation):
                    troughs.append((i, lows[i]))
        
        # Объединяем пики и впадины в один список и сортируем по индексу
        all_points = sorted(peaks + troughs, key=lambda x: x[0])
        
        if len(all_points) < 2:
            return None, None
        
        # Последние две точки
        z1, z2 = all_points[-2], all_points[-1]
        
        # Определяем направление
        direction = 1 if z2[1] > z1[1] else -1
        
        # Преобразуем обратно в исходный порядок (новые свечи первыми)
        last_peaks = [(1, z1[1]), (2, z2[1])]
        
        return direction, last_peaks
