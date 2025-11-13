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
from src.orders_block.trade_position import Position, PositionStatus, TakeProfit_Status, StopLoss
from src.backtester.repot import TradeReport, generate_html_report, get_export_path


# ====================================================
# Запуск бэктеста для одной монеты
# ====================================================
def backtest_coin(data_df, coin) -> list:
    """
    Запуск бэктеста с данными, загруженными из локального файла.
    """
    
    # Получение минимальное количество баров из настроек
    MIN_BARS = config.get_setting("STRATEGY_SETTINGS", "MINIMAL_BARS")
    
    symbol = coin.get("SYMBOL")+"/USDT"
    tick_size = coin.get("MINIMAL_TICK_SIZE")
    volume_size = coin.get("VOLUME_SIZE")
    
    executed_positions = []  # Список для хранения исполненных позиций
    
    if MIN_BARS > len(data_df):
        logger.error(f"Невозможно запустить бектест: не хватает баров для расчета индикаторов.")
        return executed_positions
    
    # Инициализация стратегии    
    strategy = ZigZagAndFibo(symbol)
    position = Position(tick_size)
    # перебираем все бары начиная с минимального количества
    # Это нужно для того, чтобы индикаторы были заполнены
    for i in range(MIN_BARS, len(data_df)):
        logger.info(f"[yellow]----------------------------------------------------------- [/yellow]")
        logger.info(f"[yellow]== Обработка бара {data_df.index[i]} === open: {data_df['open'].iloc[i]}, high: {data_df['high'].iloc[i]}, low: {data_df['low'].iloc[i]}, close: {data_df['close'].iloc[i]}[/yellow]")
        current_data = data_df.iloc[i-MIN_BARS : i ]
        current_bar = data_df.iloc[i]
        # current_bar = data_df.index[i]
            
        # рассчитываем индикаторы стратегии ищем точку входа
        signal = strategy.find_entry_point(current_data)
        
        if signal and position.status == PositionStatus.NONE:
            logger.info(f"Сигнала {signal.get("direction")} на баре {current_bar}")
            position = Position(tick_size)
            # def setPosition(self, symbol, direction, entry_price: Decimal, bar_index):
            position.setPosition(symbol, signal.get("direction"), position.round_to_step(current_bar["open"]), current_bar.name)
            if signal.get("take_profits") is not None:
                position.set_take_profits(signal.get("take_profits", []))
            
            if signal.get("stop_loss") is not None:
                stop_loss = signal["stop_loss"]
                stop_loss_volume = signal["stop_loss_volume"]
                position.set_stop_loss(StopLoss(price=position.round_to_step(stop_loss), volume=stop_loss_volume))        
                continue
        
        
       
        
        # Алгоритм ведение и выхода из позиции
        
        # Если позиция только создана по стратегии добавляем объем позиции    
        if position.status == PositionStatus.CREATED:
            # TODO: Добавить в позицию модуль рискМенеджмента
            position.setVolume_size(volume_size)            
            
            position.status = PositionStatus.ACTIVE
            logger.info(f"Создана позиция:  {position}")
            
        # Если позиция активна
        if position.status == PositionStatus.ACTIVE or position.status == PositionStatus.TAKEN_PART:
            # Добавляем в позицию объем либо подключаем  модуль рискМенеджмента
            # проверяем на текущей свече сработал ли тейк-профит или стоп-лосс
            position.check_take_profit(current_bar)
            
            # position.stop_loss_not_loss(current_bar)
            position.check_stop_loss(current_bar)
            
            

        # рассчитываем прибыль если позиция исполнена
        if position.status == PositionStatus.TAKEN_FULL or position.status == PositionStatus.STOPPED:
            position.Calculate_profit()
            # --- Сохраняем копию позиции в отчет ---
            report = TradeReport(position)
            executed_positions.append(report.to_dict())
            
            logger.info(f"Исполнена позиция статус: {report.to_json()}")
            logger.info(f"-----------------------------------------------------------------------------")
            # --- Создаем чистую заготовку для позиции ---
            position = Position(tick_size)
                
            # Отменяем все оставшиеся ордера
            # position.cancel_orders()

        continue
    
    return executed_positions
        


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
    
    full_datafile = config.get_setting("BACKTEST_SETTINGS", "FULL_DATAFILE")
    start_date = config.get_setting("BACKTEST_SETTINGS", "START_DATE")  
    end_date = config.get_setting("BACKTEST_SETTINGS", "END_DATE")
    
    # Если full_datafile = False, то возвращаем исходный DataFrame
    if full_datafile:
        logger.info("Используется полный исторический диапазон. full_datafile = True")
        return data_df
    
    # Преобразование строковых дат в datetime объекты
    start_dt = pd.to_datetime(start_date)
    end_dt = pd.to_datetime(end_date)
    logger.info(f"📅 Период тестированияыы: {start_dt} ↔️   {end_dt}")
    
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
    data_dir = config.get_setting("BACKTEST_SETTINGS", "DATA_DIR")
    template_dir = config.get_setting("BACKTEST_SETTINGS", "TEMPLATE_DIRECTORY")
        
    # 1. Получение массива монет из конфигурации
    try:
        coins_list = config.get_section("COINS")
        logger.info(f"Загружено {len(coins_list)} монет из конфигурации.")
    except KeyError as e:
        # Хотя валидация должна была поймать это, это хорошая защита
        logger.error(f"Критическая ошибка: {e}")
        coins_list = [] # Устанавливаем пустой список для безопасной работы
        
    # Подключение модуля с загрузчиком данных
    from src.data_fetcher.data_fetcher import DataFetcher
    # 2. Обработка каждой монеты   
    for coin in coins_list:
        logger.info("============================================================================")
        
        symbol = coin.get("SYMBOL")+"/USDT"
        timeframe = coin.get("TIMEFRAME")
        tick_size = coin.get("MINIMAL_TICK_SIZE")
        logger.info(f"🪙 Монета: [bold yellow]{symbol}[/bold yellow], ↔️ Таймфрейм: [bold yellow]{timeframe}[/bold yellow], Минимальный шаг цены {tick_size}")
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
            executed_positions = backtest_coin(select_data, coin)
            
            files_report = get_export_path(symbol=symbol, file_extension="html")
            files_report_csv = get_export_path(symbol=symbol, file_extension="csv")
            path = generate_html_report(executed_positions,symbol, files_report, template_dir)
            logger.info(f"Отчет сохранен в: {path}")
            
            executed_positions_df = pd.DataFrame(executed_positions)
            executed_positions_df.to_csv(files_report_csv, index=False)
            
        else:
            logger.error(f"Невозможно запустить бектест для {symbol}: данные не загружены.")
        
