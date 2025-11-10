# backtest	Тестирование стратегии на исторических данных.	
# Симуляция выполнения сделок. 
# Расчет метрик производительности (прибыльность, просадка, Sharpe Ratio).

import pandas as pd
# Логирование
# ====================================================
from src.utils.logger import get_logger
logger = get_logger(__name__)

from src.config.config import config
from src.logical.strategy.zigzag_fibo.zigzag_and_fibo import calculate_strategy
from src.risk_manager.trade_position import Position, TakeProfitLevel, StopLoss


# ====================================================
# Запуск бэктеста для одной монеты
# ====================================================
def backtest_coin(data_df, symbol, tick_size):
    """
    Запуск бэктеста с данными, загруженными из локального файла.
    """
    MIN_BARS = config.get_setting("STRATEGY_SETTINGS", "MINIMAL_BARS")
    
    if MIN_BARS > len(data_df):
        logger.error(f"Невозможно запустить бектест: не хватает баров для расчета индикаторов.")
        return
    
    previous_direction = None
    for i in range(MIN_BARS, len(data_df)):
        logger.info(f"[yellow]== Обработка бара {data_df.index[i]} === open: {data_df['open'].iloc[i]}, high: {data_df['high'].iloc[i]}, low: {data_df['low'].iloc[i]}, close: {data_df['close'].iloc[i]}[/yellow]")
        current_data = data_df.iloc[i-MIN_BARS : i ]
            
        # рассчитываем индикаторы стратегии
        zigzag, fiboLev = calculate_strategy(current_data)
       
        if zigzag is None or fiboLev is None:
            logger.error(f"Стратегия не вернула корректные результаты.")
            continue

        logger.info(f"ZigZag / z1 =: {zigzag["z1"]}, z2 =: {zigzag["z2"]}, z2_index: {zigzag['z2_index']} direction: {zigzag['direction']}")        

        direction = zigzag["direction"]
        
        if direction == -1 and (previous_direction == 1 or previous_direction == None):
            logger.info(f"🎢 Расчет сделки на [bold green] BUY [/bold green] / на баре - {data_df.index[i]} ")
            
            entry_price = data_df["open"].iloc[i]
            stop_loss = fiboLev[161.8]
            
            # Создание сделки
            tps= []
            # перебираем все 5 тейков в обратном порядке 
            for level, value in list(fiboLev.items())[:5][::-1]:
                # logger.info(f"Уровень Фибоначчи {level}%: {value}")
                tps.append(TakeProfitLevel(price=value, volume=0.2, tick_size=tick_size)) 
        
            position = Position(
                symbol=symbol,
                direction='long',
                entry_price=entry_price,
                volume=0.2,
                bar_index=data_df.index[i],
                tick_size=tick_size,
            )
            position.set_take_profits(tps)
            position.add_stop_loss(StopLoss(price=stop_loss, volume=1, tick_size=tick_size))
            logger.info(f"Сделка создана: {position}, {position.status}")            
            previous_direction = -1
            
        if direction == 1 and (previous_direction == -1 or previous_direction == None):
            logger.info(f"🎢 Расчет сделки на [bold red] SELL [/bold red] / на баре - {data_df.index[i]} ")    

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
    if full_datafile:
        logger.info("Используется полный исторический диапазон.")
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
        
