# Простой тест для проверки Fast1mBarSelector
# src/backtester/engine/test_fast_selector.py

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from src.backtester.engine.fast_1m_selector import Fast1mBarSelector


def test_fast_selector():
    """Тест для проверки корректности работы Fast1mBarSelector"""
    
    # Создаем тестовые данные: 1000 минутных баров
    start = datetime(2024, 1, 1, 0, 0, 0)
    timestamps = [start + timedelta(minutes=i) for i in range(1000)]
    
    # Создаем случайные OHLC данные
    np.random.seed(42)
    data = {
        'open': 100 + np.random.randn(1000).cumsum(),
        'high': 100 + np.random.randn(1000).cumsum() + 0.5,
        'low': 100 + np.random.randn(1000).cumsum() - 0.5,
        'close': 100 + np.random.randn(1000).cumsum(),
        'volume': np.random.randint(100, 1000, 1000)
    }
    
    df = pd.DataFrame(data, index=timestamps)
    
    # Инициализируем селектор
    selector = Fast1mBarSelector(df)
    
    # Тест 1: Получение баров для одного часа (60 минут)
    htf_bar_time = pd.Timestamp(start + timedelta(hours=5))
    bars_1m = selector.get_bars_for_htf_bar(htf_bar_time, '1h')
    
    assert bars_1m is not None, "Должны быть получены бары"
    assert len(bars_1m) == 60, f"Ожидалось 60 баров, получено {len(bars_1m)}"
    assert bars_1m.shape[1] == 5, "Массив должен иметь 5 столбцов"
    
    # Проверяем формат данных
    assert isinstance(bars_1m[0, 4], pd.Timestamp), "Последний столбец должен содержать pd.Timestamp"
    
    # Тест 2: Получение баров для диапазона
    start_time = pd.Timestamp(start + timedelta(hours=2))
    end_time = pd.Timestamp(start + timedelta(hours=3))
    bars_range = selector.get_bars(start_time, end_time)
    
    assert bars_range is not None, "Должны быть получены бары для диапазона"
    assert len(bars_range) == 60, f"Ожидалось 60 баров, получено {len(bars_range)}"
    
    # Тест 3: Пустой диапазон (вне данных)
    future_start = pd.Timestamp(start + timedelta(days=10))
    future_end = pd.Timestamp(start + timedelta(days=11))
    empty_bars = selector.get_bars(future_start, future_end)
    
    assert empty_bars is None, "Для будущего диапазона должен вернуться None"
    
    # Тест 4: Проверка совместимости с ExecutionLoop
    # ExecutionLoop ожидает массив, где можно обратиться к bar[0], bar[1], bar[2], bar[3], bar[4]
    test_bar = bars_1m[0]
    assert len(test_bar) == 5, "Бар должен иметь 5 элементов"
    assert isinstance(test_bar[0], (int, float, np.number)), "bar[0] должен быть числом (open)"
    assert isinstance(test_bar[1], (int, float, np.number)), "bar[1] должен быть числом (high)"
    assert isinstance(test_bar[2], (int, float, np.number)), "bar[2] должен быть числом (low)"
    assert isinstance(test_bar[3], (int, float, np.number)), "bar[3] должен быть числом (close)"
    assert isinstance(test_bar[4], pd.Timestamp), "bar[4] должен быть pd.Timestamp"
    
    print("✅ Все тесты пройдены успешно!")
    print(f"   - Получено {len(bars_1m)} баров для 1h таймфрейма")
    print(f"   - Формат данных корректен")
    print(f"   - Совместимость с ExecutionLoop подтверждена")


if __name__ == "__main__":
    test_fast_selector()
