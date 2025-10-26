import pandas as pd
import numpy as np

# Логирование
# ====================================================
from src.utils.logger import get_logger
logger = get_logger(__name__)

from src.config.config import config




# --- 1. Вспомогательный класс для имитации chart.point ---
class ZigZagPoint:
    def __init__(self, price, time):
        self.price = price
        self.time = time
    
    def copy(self):
        return ZigZagPoint(self.price, self.time)
    
    def __repr__(self):
        return f"({self.time}, {self.price:.4f})"

# --- 2. Вспомогательные функции для имитации Pine Script (упрощённые) ---
def calculate_barssince(condition_series):
    """
    Упрощённая эмуляция ta.barssince: считает, сколько баров прошло с последнего True.
    В реальной жизни это очень сложный расчёт, который должен учитывать исторические данные.
    Для цикла бар-за-баром:
    """
    barssince = []
    count = 0
    for val in condition_series:
        if val:
            count = 0
        else:
            count += 1
        barssince.append(count)
    return pd.Series(barssince, index=condition_series.index)

def calculate_highestbars(series, depth):
    """Эмуляция ta.highestbars (возвращает количество баров назад до максимального значения)."""
    return series.rolling(depth).apply(lambda x: np.argmax(x) + 1, raw=True).fillna(0).astype(int)

def calculate_lowestbars(series, depth):
    """Эмуляция ta.lowestbars (возвращает количество баров назад до минимального значения)."""
    return series.rolling(depth).apply(lambda x: np.argmin(x) + 1, raw=True).fillna(0).astype(int)


def calculate_zigzag(df):
    """
    Полная реализация логики Зигзаг с циклом для сохранения состояния.
    """
    
    # Получение настроек индикатора
    depth = config.get_setting("STRATEGY_SETTINGS", "ZIGZAG_DEPTH")
    deviation = config.get_setting("STRATEGY_SETTINGS", "ZIGZAG_DEVIATION")
    backstep = config.get_setting("STRATEGY_SETTINGS", "ZIGZAG_BACKTEP")
    
    # Расчёт вспомогательных серий для barssince (векторизация)
    
    # 1. high_max_idx = ta.highestbars(depth)
    high_max_idx = calculate_highestbars(df['high'], depth)
    # 2. low_min_idx = ta.lowestbars(depth)
    low_min_idx = calculate_lowestbars(df['low'], depth)
    
    # 3. Условия для hr и lr
    # (_high[-ta.highestbars(depth)] - _high > deviation*syminfo.mintick)
    high_diff = df['high'].shift(high_max_idx) - df['high']
    high_cond = high_diff > deviation * df['tick_size']
    
    # (_low - _low[-ta.lowestbars(depth)] > deviation*syminfo.mintick)
    low_diff = df['low'] - df['low'].shift(low_min_idx)
    low_cond = low_diff > deviation * df['tick_size']
    
    # 4. hr и lr: ta.barssince(not [cond][1])
    hr = calculate_barssince(~high_cond.shift(1).fillna(False))
    lr = calculate_barssince(~low_cond.shift(1).fillna(False))
    
    # Инициализация переменных состояния (var)
    z, z1, z2 = None, None, None
    prev_direction = 0
    
    # Список для хранения точек Зигзага (для графика)
    zigzag_points = []
    
    # Запуск цикла для эмуляции побарной работы Pine Script
    for i in range(len(df)):
        _time = df.index[i]
        _low = df.iloc[i]['low']
        _high = df.iloc[i]['high']
        
        # --- A. Инициализация на первом баре ---
        if i == 0:
            z = ZigZagPoint(_low, _time)
            z1 = ZigZagPoint(_low, _time)
            z2 = ZigZagPoint(_high, _time)
            df.loc[_time, 'direction'] = 1
            df.loc[_time, 'z1_time'] = z1.time
            df.loc[_time, 'z1_price'] = z1.price
            df.loc[_time, 'z2_time'] = z2.time
            df.loc[_time, 'z2_price'] = z2.price
            prev_direction = 1
            continue
            
        # --- B. Расчёт направления (direction) ---
        
        # direction = ta.barssince(not (hr > lr)) >= backstep ? -1: 1
        current_hr = hr.iloc[i]
        current_lr = lr.iloc[i]
        
        # Условие смены тренда: lr стало меньше hr (тренд меняется с Down на Up)
        # current_cond = not (current_hr > current_lr)
        current_cond = current_hr <= current_lr
        
        # Если условие (current_hr <= current_lr) истинно (Up-тренд)
        if current_cond and hr.iloc[i] >= backstep:
             direction = 1
        # Иначе (Down-тренд)
        elif not current_cond and lr.iloc[i] >= backstep:
             direction = -1
        else:
            # Если условия не выполнены, сохраняем предыдущее направление
            direction = prev_direction 
        
        df.loc[_time, 'direction'] = direction
        
        # --- C. Обновление точек Зигзага (z, z1, z2) ---
        
        # if ta.change(direction)
        if direction != prev_direction and z is not None and z2 is not None:
            z1 = z2.copy()
            z2 = z.copy()
            
            # Сохраняем новую точку (z1) в списке точек зигзага
            zigzag_points.append(z1)

        if direction > 0: # Движение вверх
            if _high > z2.price:
                z2 = ZigZagPoint(_high, _time)
                z = ZigZagPoint(_low, _time)
            elif _low < z.price:
                z = ZigZagPoint(_low, _time)

        elif direction < 0: # Движение вниз
            if _low < z2.price:
                z2 = ZigZagPoint(_low, _time)
                z = ZigZagPoint(_high, _time)
            elif _high > z.price:
                z = ZigZagPoint(_high, _time)

        # Сохранение текущих z1 и z2 для отрисовки
        df.loc[_time, 'z1_time'] = z1.time
        df.loc[_time, 'z1_price'] = z1.price
        df.loc[_time, 'z2_time'] = z2.time
        df.loc[_time, 'z2_price'] = z2.price
        
        # Удаление предыдущей линии (if direction == direction[1]: line.delete(zz[1]))
        # В Pandas это означает, что мы рисуем только одну линию от z1 до z2 на каждом баре.
        
        prev_direction = direction
        
    # После цикла добавляем последнюю точку z2
    zigzag_points.append(z2)
    
    return df, zigzag_points

# Запуск расчёта
df_result, zz_points = calculate_zigzag(df.copy())
