# backtest	Тестирование стратегии на исторических данных.	
# Симуляция выполнения сделок. 
# Расчет метрик производительности (прибыльность, просадка, Sharpe Ratio).

import pandas as pd
# Логирование
# ====================================================
from src.utils.logger import get_logger
logger = get_logger(__name__)

from src.config.config import config
from src.logical.strategy.zigzag_fibo.zigzag_and_fibo import ZigZagAndFibo



# ====================================================
# Запуск бэктеста для одной монеты
# ====================================================
def backtest_coin(data_df, symbol, tick_size):
    """
    Запуск бэктеста с данными, загруженными из локального файла.
    """
    # Получение минимальное количество баров из настроек
    MIN_BARS = config.get_setting("STRATEGY_SETTINGS", "MINIMAL_BARS")
    
    if MIN_BARS > len(data_df):
        logger.error(f"Невозможно запустить бектест: не хватает баров для расчета индикаторов.")
        return
    
    # Инициализация стратегии    
    strategy = ZigZagAndFibo(symbol, tick_size)

    # перебираем все бары начиная с минимального количества
    # Это нужно для того, чтобы индикаторы были заполнены
    for i in range(MIN_BARS, len(data_df)):
        logger.info(f"[yellow]== Обработка бара {data_df.index[i]} === open: {data_df['open'].iloc[i]}, high: {data_df['high'].iloc[i]}, low: {data_df['low'].iloc[i]}, close: {data_df['close'].iloc[i]}[/yellow]")
        current_data = data_df.iloc[i-MIN_BARS : i ]
            
        # рассчитываем индикаторы стратегии
        position = strategy.calculate_strategy(current_data)
       
        if position is not None:
            logger.info(f"Сигнала нет, текущий бар")
        


# ====================================================
# Выбор диапазона дат для бэктеста
# ==================================================== 
def select_range(data_df):
    """
    Фильтрация DataFrame по заданному диапазону дат.
    Если full_datafile = True, то возвращаем исходный DataFrame
    
    :param data_df: pd.DataFrame — исходный DataFrame с данными
    :return: pd.DataFrame — отфильтрованный DataFrame
    """
    
    full_datafile = config.get_setting("MODE_SETTINGS", "FULL_DATAFILE")
    start_date = config.get_setting("MODE_SETTINGS", "START_DATE")  
    end_date = config.get_setting("MODE_SETTINGS", "END_DATE")
    
    # Если full_datafile = False, то возвращаем исходный DataFrame
    if full_datafile:
        logger.info("Используется полный исторический диапазон. full_datafile = True")
        return data_df
    
    # Преобразование строковых дат в datetime объекты
    start_dt = pd.to_datetime(start_date)
    end_dt = pd.to_datetime(end_date)
    logger.info(f"+++ Запуск бэктеста на диапазоне с: {start_dt} по {end_dt}")
    
    # Фильтрация DataFrame по диапазону дат
    filtered_df = data_df[(data_df.index >= start_dt) & (data_df.index <= end_dt)].copy()
    
    return filtered_df


# точка входа для бэктеста
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
        tick_size = coin.get("MINIMAL_TICK_SIZE")
        logger.info(f"🪙 Монета: [bold red]{symbol}[/bold red], ↔️ Таймфрейм: [bold red]{timeframe}[/bold red], Минимальный шаг цены {tick_size}")
        # 1. Инициализируем DataFetcher
        fetcher = DataFetcher( coin,
            exchange_id=exchange_id, 
            limit=limit,
            directory=data_dir,
            )
        # 2. Загрузка из файла
        data_df = fetcher.load_from_csv(file_type="csv")
    
        if data_df is not None:
            logger.info(f"🚀 Запуск стратегии для {symbol} с локальными данными.")
            select_data = select_range(data_df)
            #  Здесь вы передаете data_df в ваш модуль стратегии или бэктеста
            backtest_coin(select_data, symbol, tick_size)
        else:
            logger.error(f"Невозможно запустить бектест для {symbol}: данные не загружены.")
        
