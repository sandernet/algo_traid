# backtest	Тестирование стратегии на исторических данных.	
# Симуляция выполнения сделок. 
# Расчет метрик производительности (прибыльность, просадка, Sharpe Ratio).

import pandas as pd
from pandas import Timedelta, DateOffset
# Логирование
# ====================================================
from src.utils.logger import get_logger
logger = get_logger(__name__)

from src.config.config import config
from src.logical.strategy.zigzag_fibo.zigzag_and_fibo import ZigZagAndFibo, PositionsManager
from src.orders_block.trade_position import Position, Position_Status, TakeProfit_Status, StopLoss

from src.backtester.repot import TradeReport, generate_html_report, get_export_path

ALLOWED_Z2_OFFSET = 1  # сколько баров назад допускается последняя точка zigzag

# ====================================================
# Запуск бэктеста для одной монеты
# ====================================================
def backtest_coin(data_df, data_df_1m, coin, allowed_min_bars) -> list:
    """
    Запуск бэктеста с данными, загруженными из локального файла.
    """
    
    full_datafile = config.get_setting("BACKTEST_SETTINGS", "FULL_DATAFILE")
    start_date = config.get_setting("BACKTEST_SETTINGS", "START_DATE")  
    end_date = config.get_setting("BACKTEST_SETTINGS", "END_DATE")
    

    
    symbol = coin.get("SYMBOL")+"/USDT"
    tick_size = coin.get("MINIMAL_TICK_SIZE")
    volume_size = coin.get("VOLUME_SIZE")
    timeframe = coin.get("TIMEFRAME")
    
    
    executed_positions = []  # Список для хранения исполненных позиций
    
    if allowed_min_bars > len(data_df):
        logger.error(f"Невозможно запустить бектест: не хватает баров для расчета индикаторов.")
        return executed_positions
    
    # Инициализация стратегии    
    strategy = ZigZagAndFibo(symbol)
    # Создаём модель позиции и менеджер, который управляет этой позицией
    position = Position(tick_size)
    pos_mgr = PositionsManager(position)
    # перебираем все бары начиная с минимального количества
    # Это нужно для того, чтобы индикаторы были заполнены
    for i in range(allowed_min_bars, len(data_df)):
        
        current_data = data_df.iloc[i-allowed_min_bars : i ]
        current_bar = data_df.iloc[i] # текущий бар который обрабатывается
        signal_bar = current_data.iloc[-1]
        current_index = current_bar.name
        current_open = current_bar["open"]
        current_high = current_bar["high"]
        current_low = current_bar["low"]
        current_close = current_bar["close"]
        
        logger.info(f"[yellow]----------------------------------------------------------- [/yellow]")
        logger.info(f"[yellow]== Обработка бара {current_index} signal_bar {signal_bar.name} === open: {current_open}, high: {current_high}, low: {current_low}, close: {current_close}[/yellow]")    
        
        #-------------------------------------------------------------
        # Алгоритм входа в позицию и создание позиции
        #-------------------------------------------------------------
        
        # рассчитываем индикаторы стратегии ищем точку входа
        signal = strategy.find_entry_point(current_data)
        
        # Если сигнал есть и позиция еще не закрыта
        if signal and position.bar_closed is None and position.bar_opened is not None:
            # TODO проверить если сигнал в обратную стророну надо закрыть позицию
            if signal.get("direction") != position.direction:
                pos_mgr.close_orders(current_bar)
                position = Position(tick_size)
                pos_mgr = PositionsManager(position)


        
        # Если сигнал есть и позиция еще не создана
        if signal and position.status == Position_Status.NONE:
            # TODO Проверить подходит ли сигнал для создания позиции
            # Условия для создания позиции
            # 1 свеча крайней точки сигнала индикатора ZigZag (signal.get("z2_index")) должна быть совпадать с текущим баром, либо быть меньше на 1 бар
            # 2 точка входа в long должна быть меньше точки первого уровня фибо
            # 3 точка входа в short должна быть больше точки первого уровня фибо    
                        
            # безопасные извлечения
            z2_index = signal.get("z2_index")
            direction = signal.get("direction")
            tps = signal.get("take_profits") or []
            sl_price = signal.get("stop_loss")
            sl_volume = signal.get("stop_loss_volume")
            entry_price = float(current_open)  # приводим к Decimal, берем цену открытия бара как предполагаемую цену входа

            # 1) обязательный z2_index
            if z2_index is None:
                logger.debug(f"Пропускаем сигнал: отсутствует z2_index")
                continue

            # 2) z2_index должен быть текущим баром или не более чем на ALLOWED_Z2_OFFSET баров раньше
            allowed_shifted = shift_timestamp(current_index, ALLOWED_Z2_OFFSET, timeframe, direction=-1)
            if not (z2_index == current_index or z2_index == allowed_shifted):
                logger.debug(f"Пропускаем сигнал: z2_index={z2_index} не в допустимом окне (текущий={current_index})")
                continue
    

            logger.info(f"Сигнала {signal.get("direction")} z2 = {z2_index} на баре  ({current_index})")
            # def setPosition(self, symbol, direction, entry_price: float, bar_index):
            position.setPosition(symbol, signal.get("direction"), float(current_open), current_index)
            if signal.get("take_profits") is not None:
                position.set_take_profits(signal.get("take_profits", []))

            
            if signal.get("stop_loss") is not None:
                stop_loss = signal["stop_loss"]
                stop_loss_volume = signal["stop_loss_volume"]
                position.set_stop_loss(StopLoss(price=float(stop_loss), volume=stop_loss_volume))        
        
            # # Если позиция только создана статус CREATED
            # # Рассчитываем по риск менеджмент объем позиции    
            # if position.status == Position_Status.CREATED:
            # 
            # TODO: Добавить в позицию модуль рискМенеджмента
            position.setVolume_size(volume_size)            
            
            
            position.status = Position_Status.ACTIVE
            logger.info(f"Создана позиция:  {position}")
        
        #-------------------------------------------------------------
        # Алгоритм ведение и выхода из позиции
        #-------------------------------------------------------------
                    
        # Если позиция активна
        if position.bar_closed is None and position.status == Position_Status.ACTIVE or position.status == Position_Status.TAKEN_PART:
            logger.info(f"Status позиции {position.status}")
            # проверяем на текущей свече сработал ли тейк-профит или стоп-лосс
            
            # перебираем минутный таймфрейм
            start_ts = current_index
            end_ts = shift_timestamp(current_index, 1, timeframe, direction=+1)
            
            # end_ts   = data_df.loc[i + 1, "timestamp"]
            current_range_1m = select_range(data_df_1m, start_ts, end_ts)
            for j in range(len(current_range_1m)):
                
                current_bar_1m = current_range_1m.iloc[j]
                 
                close_TP = pos_mgr.check_take_profit(current_bar_1m)

                close_SL = pos_mgr.check_stop_loss(current_bar_1m)

                # если закрыты все take_profits или stop_loss закрываем позицию
                if close_TP or close_SL:
                    pos_mgr.close_orders(current_bar)
                    logger.info(f"Закрываем позициию {position} по {current_bar}")

            
        # если позиция выполнена и заполнена дата закрытия
        if position.bar_closed is not None:
            
            # рассчитываем прибыль
            pos_mgr.Calculate_profit()
            # --- Сохраняем позицию в отчет ---
            report = TradeReport(position)
            executed_positions.append(report.to_dict())
            
            logger.info(f"-----------------------------------------------------------------------------")
            # --- Создаем чистую заготовку для позиции ---
            position = Position(tick_size)
            pos_mgr = PositionsManager(position)
   
    return executed_positions
        


# ====================================================
# Выбор диапазона дат для бэктеста
# ==================================================== 
def select_range_becktest(data_df, timeframe, full_datafile, allowed_min_bars, start_date = None, end_date = None)  -> pd.DataFrame:
    """
    Фильтрация DataFrame по заданному диапазону дат.
    Если full_datafile = True, то возвращаем исходный DataFrame
    
    :param data_df: pd.DataFrame — исходный DataFrame с данными
    :return: pd.DataFrame — отфильтрованный DataFrame
    """
    

    if full_datafile:
        logger.info("Используется полный исторический диапазон. full_datafile = True")
        return data_df
    else:
        start_date = shift_timestamp(start_date, allowed_min_bars, timeframe, direction=-1)
        logger.info(f"📅 Период тестированияыы: {start_date} ↔️   {end_date}")
        return select_range(data_df, start_date, end_date)
    
def select_range(data_df, start_date, end_date):
    # Преобразование строковых дат в datetime объекты
    start_dt = pd.to_datetime(start_date)
    end_dt = pd.to_datetime(end_date)

    
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
    
    full_datafile = config.get_setting("BACKTEST_SETTINGS", "FULL_DATAFILE")
    start_date = config.get_setting("BACKTEST_SETTINGS", "START_DATE")
    end_date = config.get_setting("BACKTEST_SETTINGS", "END_DATE")
        # Получение минимальное количество баров из настроек
    MIN_BARS = config.get_setting("STRATEGY_SETTINGS", "MINIMAL_BARS")
        
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
        data_df = fetcher.load_from_csv(file_type="csv", timeframe=timeframe)
        data_df_1m = fetcher.load_from_csv(file_type="csv")
    
        if data_df is not None:
            logger.info(f"🚀 Запуск стратегии для {symbol} с локальными данными.")
            
            # 3. Выбор периода для бэктеста
            select_data = select_range_becktest(data_df, timeframe, full_datafile, MIN_BARS, start_date, end_date)
            
            #  Здесь вы передаете data_df в ваш модуль стратегии или бэктеста
            executed_positions = backtest_coin(select_data,data_df_1m, coin, MIN_BARS)
            
            files_report = get_export_path(symbol=symbol, file_extension="html")
            files_report_csv = get_export_path(symbol=symbol, file_extension="csv")
            
            path = generate_html_report(
                executed_reports = executed_positions,
                symbol = symbol, 
                period_start =start_date,
                period_end =end_date,
                target_path = files_report, 
                template_dir = template_dir
                )
            
            
            logger.info(f"Отчет сохранен в: {path}")
            
            executed_positions_df = pd.DataFrame(executed_positions)
            executed_positions_df.to_csv(files_report_csv, index=False)
            
        else:
            logger.error(f"Невозможно запустить бектест для {symbol}: данные не загружены.")
        
# сдвиг метки времени
def shift_timestamp(index, bars: int, timeframe: str, direction: int = -1):
    """
    Сдвигает метку времени на заданное количество баров для заданного таймфрейма.

    index: pandas.Timestamp или числовой индекс (int)
    bars: число баров (int, >=0)
    timeframe: строка таймфрейма, поддерживает: числовые минуты ('1','3','5','15',...),
               единицы 'D','W','M' или форматы с суффиксом ('15m','1h').
    direction: -1 для сдвига назад (index - bars*tf), +1 для вперёд.

    Возвращает новый индекс того же типа, что и входной (Timestamp или int).
    """
    index = pd.Timestamp(index)
    # если индекс не временной (например, целочисленный индекс), просто сдвигаем по числу баров
    if not isinstance(index, (pd.Timestamp, pd.DatetimeIndex)):
        try:
            # предполагаем, что index — целое число (позиция/номер строки)
            return index + direction * bars
        except Exception:
            return index

    tf = str(timeframe).strip()
    # normalize
    tf_upper = tf.upper()

    # минутные значения — либо чисто число ("15"), либо с суффиксом m ("15m")
    try:
        if tf_upper.endswith('M') and not tf_upper.isdigit():
            # could be '15M' meaning minutes or 'M' meaning month -> distinguish
            # if single 'M' treat as month
            if tf_upper == 'M':
                delta = DateOffset(months=bars)
            else:
                # numeric part
                num = int(tf_upper[:-1])
                delta = Timedelta(minutes=num * bars)
        elif tf_upper.endswith('H'):
            num = int(tf_upper[:-1])
            delta = Timedelta(minutes=60 * num * bars)
        elif tf_upper in ('D', 'W', 'M'):
            if tf_upper == 'D':
                delta = DateOffset(days=bars)
            elif tf_upper == 'W':
                delta = DateOffset(weeks=bars)
            else:  # 'M'
                delta = DateOffset(months=bars)
        else:
            # try parse as integer minutes
            num = int(tf_upper)
            delta = Timedelta(minutes=num * bars)
    except Exception:
        # fallback: try parsing common patterns like '15m', '1h'
        s = tf_upper
        if s.endswith('M') and len(s) > 1:
            num = int(s[:-1])
            delta = Timedelta(minutes=num * bars)
        elif s.endswith('H'):
            num = int(s[:-1])
            delta = Timedelta(minutes=60 * num * bars)
        else:
            # as last resort — treat timeframe as minutes if numeric part exists
            digits = ''.join(ch for ch in s if ch.isdigit())
            if digits:
                delta = Timedelta(minutes=int(digits) * bars)
            else:
                # Unknown timeframe — возврат оригинального индекса
                return index

    if direction < 0:
        return index - delta
    return index + delta