# backtester	Тестирование стратегии на исторических данных.	
# Симуляция выполнения сделок. 
# Расчет метрик производительности (прибыльность, просадка, Sharpe Ratio).

import pandas as pd
# Логирование
# ====================================================
from src.utils.logger import get_logger
logger = get_logger(__name__)

from src.config.config import config

# точка входа для бэктестера
# ====================================================
def run_local_backtest():
    """Основной конвейер для получения и сохранения исторических данных по монетам из конфигурации."""

    # Получение настроек Биржи
    exchange_id = config.get_setting("EXCHANGE_SETTINGS", "EXCHANGE_ID")
    limit = config.get_setting("EXCHANGE_SETTINGS", "LIMIT")
    data_dir = config.get_setting("MODE_SETTINGS", "DATA_DIR")
    
    
    # 1. Получение массива монет из конфигурации
    try:
        coins_list = config.get_section("COINS")
        logger.info(f"Загружено {len(coins_list)} монет из конфигурации.")
    except KeyError as e:
        # Хотя валидация должна была поймать это, это хорошая защита
        logger.error(f"Критическая ошибка: {e}")
        coins_list = [] # Устанавливаем пустой список для безопасной работы
        
    # Подключение модуля с загрузчиком данных
    from src.logical.data_fetcher.data_fetcher import DataFetcher
    # 2. Обработка каждой монеты   
    for coin in coins_list:
        logger.info("============================================================================")
        symbol = coin.get("SYMBOL")+"/USDT"
        timeframe = coin.get("TIMEFRAME")
        logger.info(f"🪙 Монета: {symbol}, ↔️ Таймфрейм: {timeframe}")
        # 1. Инициализируем DataFetcher
        fetcher = DataFetcher( 
            symbol=symbol, 
            timeframe=timeframe, 
            exchange_id=exchange_id, 
            limit=limit,
            directory=data_dir,
            )
        # 2. Загрузка из файла
        data_df = fetcher.load_from_csv(file_type="csv")
    
        if data_df is not None:
            logger.info(f"🚀 Запуск стратегии для {symbol} с локальными данными.")
            select_data = select_range(data_df)
            #  Здесь вы передаете data_df в ваш модуль стратегии или бэктестера
            backtest_coin(select_data)
        else:
            logger.error(f"Невозможно запустить бэктест для {symbol}: данные не загружены.")
        

# ====================================================
# Запуск бэктеста для одной монеты
# ====================================================
def backtest_coin(data_df):
    """
    Запуск бэктеста с данными, загруженными из локального файла.
    """
    MIN_BARS = config.get_setting("STRATEGY_SETTINGS", "MINIMAL_BARS")
    
    if MIN_BARS > len(data_df):
        logger.error(f"Невозможно запустить бэктест: не хватает баров для расчета индикаторов.")
        return
    
    previous_direction = None
    for i in range(MIN_BARS, len(data_df)):
        logger.info("============================================================================")
        logger.info(f"Обработка бара {data_df.index[i]}")
        current_data = data_df.iloc[i-MIN_BARS : i ]
        
        logger.info(f"Взято {len(current_data)} баров для расчета индикаторов.")
    
        from src.logical.strategy.zigzag_fibo.zigzag_and_fibo import calculete_strategy
        # Применяем функцию к каждой строке
        direction, z1, z2, fiboLev =    calculete_strategy(current_data)
            
        if direction is None or z1 is None or z2 is None or fiboLev is None:
            logger.error(f"Стратегия не вернула корректные результаты для .")
            continue
        
        if direction == -1 and (previous_direction == 1 or previous_direction == None):
            logger.info("🎢 Запуск расчета данных по ордерам по стратегии.")
            logger.info(f"------------Сигнал на покупку {data_df.index[i]} Buy")
            logger.info(f"Направление ZigZag: {direction}, z1 = {z1} z1 = {z2}")

            for level, value in fiboLev.items():
                logger.info(f"Уровень Фибоначчи {level}%: {value}")
            
            # запускаем расчет ордеров по стратегии
            # from src.risk_manager.risk_manager import RiskManager
            # risk_manager = RiskManager()
            # risk_manager.calculate_position_size()
            previous_direction = -1
            
        if direction == 1 and (previous_direction == -1 or previous_direction == None):
            logger.info("🎢 Запуск расчета данных по ордерам по стратегии.")
            logger.info(f"------------Сигнал на покупку {data_df.index[i]} sell")
            logger.info(f"Направление ZigZag: {direction}, z1 = {z1} z1 = {z2}")

            for level, value in fiboLev.items():
                logger.info(f"Уровень Фибоначчи {level}%: {value}")
            # запускаем расчет ордеров по стратегии
            # from src.risk_manager.risk_manager import RiskManager
            # risk_manager = RiskManager()
            # risk_manager.calculate_position_size()
            previous_direction = 1

    
def select_range(data_df):
    """
    Фильтрация DataFrame по заданному диапазону дат.
    
    :param data_df: pd.DataFrame — исходный DataFrame с данными
    :return: pd.DataFrame — отфильтрованный DataFrame
    """
    
    full_datafile = config.get_setting("MODE_SETTINGS", "FULL_DATAFILE")
    start_date = config.get_setting("MODE_SETTINGS", "START_DATE")  
    end_date = config.get_setting("MODE_SETTINGS", "END_DATE")
    
    # Если full_datafile = False, то возвращаем исходный DataFrame
    if not full_datafile:
        return data_df
    
    # Преобразование строковых дат в datetime объекты
    start_dt = pd.to_datetime(start_date)
    end_dt = pd.to_datetime(end_date)
    
    # Фильтрация DataFrame по диапазону дат
    filtered_df = data_df[(data_df.index >= start_dt) & (data_df.index <= end_dt)].copy()
    
    return filtered_df
