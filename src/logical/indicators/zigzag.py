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
        self.backstep = config.get_setting("STRATEGY_SETTINGS", "ZIGZAG_BACKTEP") 
        self.mintick = 0.01
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
    def calculate_zigzag(self, df):
        """
        Вычисляет ZigZag индикатор и добавляет его в DataFrame.
        hr = ta.barssince(not (_high[-ta.highestbars(depth)] - _high > deviation*syminfo.mintick)[1])
        
        """
        # Расчёт
        df['hr'] = calc_hr(df, self.depth, self.deviation, self.mintick)
        df['lr'] = calc_lr(df, self.depth, self.deviation, self.mintick)
        
        df['direction'] = calc_direction(df['hr'], df['lr'], self.backstep)
       
        logger.info(f"hr = : {df['hr'][-1]}, lr = : {df['lr'][-1]} direction = : {df['direction'][-1]}")
        
        
        
        print(f"{'Index':<10}{'hr':<10}{'lr':<10}")
        print("-" * 40)
        for i in range(len(df)):
            print(f"index {df.index[i]}-------- {df['hr'][i]:<10} {df['lr'][i]:<10}  {df['direction'][i]:<10}")
            
        dir_prev = df['direction'].iat[-2]
        dir_curr = df['direction'].iat[-1]
        
        if dir_prev != dir_curr:
            return True
    

      
        
        return False
    
    
# === Аналог ta.highestbars() ===
def highestbars(series: pd.Series, length: int) -> pd.Series:
    """
    Возвращает количество баров назад до максимума за последние length баров.
    Для баров, где недостаточно данных — NaN.
    Устойчиво к nullable dtypes (конвертируем в numpy).
    """
    offsets = []
    n = len(series)
    for i in range(n):
        if i < length - 1:
            offsets.append(np.nan)
        else:
            # окно от i-length+1 до i включительно
            window = series.iloc[i - length + 1 : i + 1]

            # безопасно конвертируем в numpy-массив float (чтобы избежать ExtensionArray проблем)
            arr = window.to_numpy(dtype=float)

            # если все значения nan — возвращаем nan
            if np.all(np.isnan(arr)):
                offsets.append(np.nan)
            else:
                # nanargmax вернёт индекс максимального элемента в arr (0..length-1)
                idx_max = int(np.nanargmax(arr))
                offsets.append(length - 1 - idx_max)
    return pd.Series(offsets, index=series.index)

# === Аналог ta.lowestbars() ===
def lowestbars(series: pd.Series, length: int) -> pd.Series:
    """
    Возвращает количество баров назад до минимума за последние length баров.
    """
    offsets = []
    n = len(series)
    for i in range(n):
        if i < length - 1:
            offsets.append(np.nan)
        else:
            window = series.iloc[i - length + 1 : i + 1]
            arr = window.to_numpy(dtype=float)
            if np.all(np.isnan(arr)):
                offsets.append(np.nan)
            else:
                idx_min = int(np.nanargmin(arr))
                offsets.append(length - 1 - idx_min)
    return pd.Series(offsets, index=series.index)

# === Аналог ta.barssince() ===
def barssince(condition: pd.Series) -> pd.Series:
    """
    Возвращает количество баров, прошедших с последнего True.
    Если True ещё не было — NaN.
    """
    result = []
    count = np.nan
    for val in condition:
        if val:
            count = 0
        elif np.isnan(count):
            count = np.nan
        else:
            count += 1
        result.append(count)
    return pd.Series(result, index=condition.index)


# === Основная функция расчёта hr ===
def calc_hr(df: pd.DataFrame, depth: int, deviation: float, syminfo_mintick: float) -> pd.Series:
    """
    Аналог PineScript выражения:
    hr = ta.barssince(not (_high[-ta.highestbars(depth)] - _high > deviation * syminfo.mintick)[1])
    """
    _high = df['high']

    # 1. Смещения до максимумов
    offsets = highestbars(_high, depth)

    # 2. Значения high на тех барах, где был максимум
    _highest = [
        np.nan if np.isnan(offsets[i]) else _high.iloc[i - int(offsets[i])]
        for i in range(len(_high))
    ]
    _highest = pd.Series(_highest, index=_high.index)

    # 3. Условие (high[-highestbars] - high) > deviation * mintick
    cond = (_highest - _high) > (deviation * syminfo_mintick)

    # 4. Смещаем на 1 бар назад
    cond_prev = cond.shift(1)

    # 5) привести к булевому типу: NaN -> False (или можно выбрать другое поведение)
    #    затем инвертировать
    cond_prev_bool = cond_prev.fillna(False).astype(bool)
    cond_inv = ~cond_prev_bool

    # 6) barssince
    hr = barssince(cond_inv)

    return hr

# === lr ===
def calc_lr(df: pd.DataFrame, depth: int, deviation: float, syminfo_mintick: float) -> pd.Series:
    """
    Аналог:
    lr = ta.barssince(not (_low - _low[-ta.lowestbars(depth)] > deviation*syminfo.mintick)[1])
    """
    _low = df['low'].astype(float)
    offsets = lowestbars(_low, depth)

    _lowest = []
    for i in range(len(_low)):
        off = offsets.iat[i]
        if pd.isna(off):
            _lowest.append(np.nan)
        else:
            idx = i - int(off)
            _lowest.append(np.nan if idx < 0 else float(_low.iat[idx]))
    _lowest = pd.Series(_lowest, index=_low.index)

    cond = (_low - _lowest) > (deviation * syminfo_mintick)
    cond_prev = cond.shift(1)
    cond_prev_bool = cond_prev.fillna(False).astype(bool)
    cond_inv = ~cond_prev_bool

    return barssince(cond_inv)

def calc_direction(hr: pd.Series, lr: pd.Series, backstep: int) -> pd.Series:
    """
    Аналог строки:
    direction = ta.barssince(not (hr > lr)) >= backstep ? -1 : 1
    """
    # 1️⃣ Сравнение hr и lr
    cond = hr > lr

    # 2️⃣ Сдвиг, чтобы условие было как [1] в Pine (если нужно точно 1 бар назад)
    # Если не нужно — можно убрать.
    # cond = cond.shift(1)

    # 3️⃣ Преобразуем NaN → False и делаем инверсию
    cond_bool = cond.fillna(False).astype(bool)
    cond_inv = ~cond_bool

    # 4️⃣ ta.barssince(not (hr > lr))
    bars_since = barssince(cond_inv)

    # 5️⃣ Проверяем, >= backstep ?
    direction = np.where(bars_since >= backstep, -1, 1)

    return pd.Series(direction, index=hr.index)
