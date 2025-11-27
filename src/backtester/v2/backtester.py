# backtest	Тестирование стратегии на исторических данных.	
# Симуляция выполнения сделок. 
# Расчет метрик производительности (прибыльность, просадка, Sharpe Ratio).

import pandas as pd
from pandas import Timedelta, DateOffset
from decimal import Decimal
from typing import Optional
# Логирование
# ====================================================
from src.utils.logger import get_logger, LoggingTimer
logger = get_logger(__name__)

from src.config.config import config
from src.logical.strategy.zigzag_fibo.zigzag_and_fibo import ZigZagAndFibo
from src.orders_block.order import PositionManager, Direction, make_order, Position, OrderStatus
from src.orders_block.order import OrderType, OrderStatus, Position_Status
from src.backtester.v2.execution_engine import ExecutionEngine

from src.orders_block.risk_manager import RiskManager

# from src.backtester.repot import TradeReport, generate_html_report, get_export_path
from src.backtester.v2.report_generator import generate_report

ALLOWED_Z2_OFFSET = 1  # сколько баров назад допускается последняя точка zigzag

# ====================================================
# Запуск бэктеста для одной монеты
# ====================================================
def backtest_coin(data_df, data_df_1m, coin, allowed_min_bars) -> list:
    """
    Запуск бэктеста с данными, загруженными из локального файла.
    :param data_df: pd.DataFrame — исторические данные по монете
    :param data_df_1m: pd.DataFrame — исторические данные по монете на 1 минуту
    :param coin: dict — конфигурация монеты
    :param allowed_min_bars: int — минимальное количество баров для расчета индикаторов
    """
    
    symbol = coin.get("SYMBOL")+"/USDT"
    tick_size = coin.get("MINIMAL_TICK_SIZE")
    timeframe = coin.get("TIMEFRAME")
    
    
    executed_positions = []  # Список для хранения исполненных позиций
    
    if allowed_min_bars > len(data_df):
        logger.error(f"Невозможно запустить бектест: не хватает баров для расчета индикаторов.")
        return executed_positions
    
    # Инициализация стратегии    
    strategy = ZigZagAndFibo(coin=coin)
    # Создаём модель позиции и менеджер, который управляет этой позицией
    
    manager = PositionManager()
    engine = ExecutionEngine(manager)
    position: Optional[Position] = None
    rm = RiskManager(coin=coin)
    
    
    # перебираем все бары начиная с минимального количества
    # Это нужно для того, чтобы индикаторы были заполнены
    arr = data_df[['open','high','low','close']].copy()
    arr['dt'] = data_df.index.to_numpy()
    arr = arr.to_numpy()
    
    for i in range(allowed_min_bars, len(arr)):

        
        current_data    = arr[i-allowed_min_bars:i] # окно для расчета индикаторов
        current_open    = arr[i][0] # текущий бар открытие
        current_high    = arr[i][1] # текущий бар высота
        current_low     = arr[i][2] # текущий бар низ
        current_close   = arr[i][3] # текущий бар закрытие
        current_index   = arr[i][4] # текущий бар индекс (Datetime)
        
        logger.debug(f"[yellow]----------------------------------------------------------- [/yellow]")
        logger.debug(f"[{current_index.strftime("%d.%m.%Y %H:%M")}] [yellow]- open: {current_open}, high: {current_high}, low: {current_low}, close: {current_close}[/yellow]")    
        
        #-------------------------------------------------------------
        # Алгоритм входа в позицию и создание позиции
        #-------------------------------------------------------------
        # рассчитываем индикаторы стратегии ищем точку входа
        signal = strategy.find_entry_point(current_data)
        
        if position is not None and signal != {}:
            if position.direction != signal['direction']:
                logger.debug(f"⚠️ Внимание: получен противоположный сигнал, позиция открыта {position.id[:6]}.")
                logger.debug(f"🔶 Закрываем позицию по рынку перед открытием новой позиции.")
                manager.close_position_at_market(position.id, Decimal(str(current_open)), close_bar=current_index)
                executed_positions.append(position)
                # сбрасываем позицию
                position: Optional[Position] = None
            
        
        # Если нет открытой позиции, ищем точку входа
        if position is None:
            if signal != {}:
                direction = signal['direction']
                logger.debug(f"🔷 Сигнал на вход получен: {direction} по цене {signal.get('price')}")

                # Риск менеджмент - установка объема позиции
                entry_price = signal.get("price")
                if entry_price is None:
                    logger.error("Ошибка: цена входа не определена в сигнале.")
                else:
                    # 1. создаем позицию
                    position = manager.open_position(symbol=symbol, direction=direction, tick_size=tick_size, open_bar=current_index)
                    
                    entry_price = position.round_to_tick(Decimal(entry_price))
                    # -------------------------------------------------------------
                    # Добавить риск менеджмент - расчет объема позиции
                    # -------------------------------------------------------------
                    # объем позиции в нативной валюте (например, в BTC) покупаем по текущей цене
                    volume = rm.calculate_position_size(entry_price=entry_price)
                    logger.debug(f"🔶 Размер позиции рассчитан RiskManager: {volume}")

                    # создаем ордер на вход
                    order = make_order(OrderType.ENTRY, price=entry_price, volume=volume, direction=direction, created_bar=current_index)
            
                    # добавляем ордер в позицию
                    position.add_order(order)
                    
                    # 2. Добовляем teke profit
                    if signal["take_profits"] is not None:
                        sum_tp_volume: Decimal = Decimal('0')
                        for tp in signal["take_profits"]: 
                            
                            tp_volume = position.round_to_tick(volume*Decimal(str(tp["volume"])))
                            tp_price = position.round_to_tick(Decimal(str(tp["price"])))
                            
                            if tp.get('tp_to_break', False):
                                tp_order = make_order(OrderType.TAKE_PROFIT, price=tp_price, volume=tp_volume, direction=direction, created_bar=current_index, meta={"tp_to_break": True})
                            else:
                                tp_order = make_order(OrderType.TAKE_PROFIT, price=tp_price, volume=tp_volume, direction=direction, created_bar=current_index)
                                
                            position.add_order(tp_order)
                            sum_tp_volume += tp_volume
                            
                        if sum_tp_volume < volume:
                            volume_diff = volume - sum_tp_volume
                            logger.debug(f"⚠️ Внимание: сумма объемов Take Profit ({sum_tp_volume}) меньше общего объема позиции ({volume}). Добавляем недостающий объем {volume_diff} к последнему TP.")
                            position.orders[-1].volume += volume_diff  # добавляем недостающий объем к последнему TP


                    # 3. Добавляем stop loss
                    if signal["sl"] is not None:
                        sum_sl_volume: Decimal = Decimal('0')
                        for sl in signal["sl"]:
                            sl_volume = position.round_to_tick(volume*Decimal(str(sl["volume"])))
                            sl_price = position.round_to_tick(Decimal(str(sl["price"])))
                            sl = make_order(order_type=OrderType.STOP_LOSS, price=sl_price, volume=sl_volume, direction=direction, created_bar=current_index)
                            position.add_order(order=sl)
                            sum_sl_volume += sl_volume
                        
                        if sum_sl_volume < volume:
                            volume_diff = volume - sum_sl_volume
                            logger.debug(f"⚠️ Внимание: сумма объемов Stop Loss ({sum_sl_volume}) меньше общего объема позиции ({volume}). Добавляем недостающий объем {volume_diff} к последнему SL.")
                            position.orders[-1].volume += volume_diff  # добавляем недостающий объем к последнему TP


        #-------------------------------------------------------------
        # Обработка исполнения ордеров на текущем баре
        #-------------------------------------------------------------
        if position is not None: # если есть position   
            logger.debug (f"♻️ Проверка исполнения ордеров для созданной позиции {position.id[:6]}")
            # перебираем текущий бар по минутным данным для более точного исполнения стопов и тейков
            start_1m    = current_index
            end__1m     = shift_timestamp(current_index, 1, timeframe, direction=+1)

            current_range_1m = select_range(data_df_1m, start_1m, end__1m)
            for j in range(len(current_range_1m)):
                bar1m = current_range_1m.iloc[j]
                # передаем бар в движок исполнения
                engine.process_bar(bar=bar1m, bar_index=bar1m.name)
                
                # проверяем исполнен ли TP после которого переводим SL в без убыточность
                if position.status == Position_Status.ACTIVE and position.check_stop_break():
                    # если закрыт хотя бы один TP, двигаем стоп в безубыточность
                    position.move_stop_to_break_even()
                    
                    

        if position is not None and position.status in {Position_Status.TAKEN_FULL, Position_Status.STOPPED, Position_Status.TAKEN_PART, Position_Status.CANCELED}:
            # если активных ордеров нет, позиция закрыта
            manager.close_position(position.id, close_bar=current_index)

            executed_positions.append(position)
            # сбрасываем позицию
            position: Optional[Position] = None
            

    return executed_positions


# ====================================================
# точка входа для бэктеста
# ====================================================
def run_local_backtest():
    """Основной конвейер для получения и сохранения исторических данных по монетам из конфигурации."""

    # Получение настроек Биржи
    exchange = config.get_section("EXCHANGE_SETTINGS")
    # exchange = config.get_setting("EXCHANGE_SETTINGS", "EXCHANGE_ID")
    # limit = config.get_setting("EXCHANGE_SETTINGS", "LIMIT")
    
    # директории данных
    data_dir = config.get_setting("BACKTEST_SETTINGS", "DATA_DIR")

    
    # Параметры бэктеста
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
        # try:
        logger.info("============================================================================")
        logger.info(f"[bold yellow] [{coin.get('SYMBOL')}/USDT][/bold yellow] 🚀 Запуск бэктеста ...")
        logger.info("============================================================================")

        symbol = coin.get("SYMBOL")+"/USDT"
        timeframe = coin.get("TIMEFRAME")
        tick_size = coin.get("MINIMAL_TICK_SIZE")
        logger.info(f"[{symbol}] 🪙, 🕒 Таймфрейм: [bold yellow]{timeframe}[/bold yellow], Минимальный шаг цены {tick_size}")
        # 1. Загрузка из файла
        # Инициализируем DataFetcher
        fetcher = DataFetcher( coin,
            exchange=exchange, 
            directory=data_dir,
            )
        # Загружаем данные из CSV файла
        with LoggingTimer("[symbol] Загрузка данных торгового таймфрейма для бэктеста"):
            data_df = fetcher.load_from_csv(file_type="csv", timeframe=timeframe) # загружаем данные нужного таймфрейма
        with LoggingTimer("[symbol] Загрузка минутных данных для точного исполнения стопов и тейков"):
            data_df_1m = fetcher.load_from_csv(file_type="csv") # загружаем минутные данные для точного исполнения стопов и тейков
        
        if data_df is not None:
            logger.info(f"🚀 Запуск стратегии для {symbol} с локальными данными.")
            
            # 2. Выбор периода для бэктеста
            with LoggingTimer("[symbol] Формируем данные для бэктеста"):
                select_data = select_range_becktest(data_df, timeframe, full_datafile, MIN_BARS, start_date, end_date)
                if not full_datafile:
                    logger.info(f"[symbol] Данные для бэктеста отобраны с {select_data.index[0]} по {select_data.index[-1]}. Всего баров: {len(select_data)}")
                    start_date = select_data.index[0]
                    end_date = select_data.index[-1]

            # 3. Выполнение бэктеста
            #  Здесь вы передаете data_df в ваш модуль стратегии или бэктеста
            with LoggingTimer("[symbol] Выполнение бэктеста"):
                executed_positions = backtest_coin(select_data,data_df_1m, coin, MIN_BARS)
            
            # 4. Генерация отчета по результатам бэктеста
            with LoggingTimer("[symbol] Генерация отчета"):
                generate_report(select_data, executed_positions, coin, start_date, end_date)
            
            logger.info(f"[symbol] Закончена обработка бэктеста. Всего позиций: {len(executed_positions)}")
            
        else:
            logger.error(f"Невозможно запустить бектест для {symbol}: данные не загружены.")
        # except Exception as e:
        #     logger.error(f"Ошибка при бэктесте для монеты {coin.get('SYMBOL')}/USDT: {e}")
        
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
