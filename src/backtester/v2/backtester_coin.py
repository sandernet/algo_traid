# backtest	Тестирование стратегии на исторических данных.	
# Симуляция выполнения сделок. 
# Расчет метрик производительности (прибыльность, просадка, Sharpe Ratio).

from decimal import Decimal
from typing import Optional
# Логирование
# ====================================================
from src.utils.logger import get_logger
logger = get_logger(__name__)


from src.logical.strategy.zigzag_fibo.zigzag_and_fibo import ZigZagAndFibo
from src.orders_block.order import PositionManager,  make_order, Position
from src.orders_block.order import OrderType, Position_Status
from src.backtester.v2.execution_engine import ExecutionEngine

from src.orders_block.risk_manager import RiskManager
from src.data_fetcher.utils import select_range, shift_timestamp

ALLOWED_Z2_OFFSET = 1  # сколько баров назад допускается последняя точка zigzag

# ====================================================
# Запуск бэктеста для одной монеты
# ====================================================
def backtest_coin(data_df, data_df_1m, coin, allowed_min_bars) -> dict:
    """
    Запуск бэктеста с данными, загруженными из локального файла.
    :param data_df: pd.DataFrame — исторические данные по монете
    :param data_df_1m: pd.DataFrame — исторические данные по монете на 1 минуту
    :param coin: dict — конфигурация монеты
    :param allowed_min_bars: int — минимальное количество баров для расчета индикаторов
    """
    
    symbol = coin.get("SYMBOL")+"/USDT"
    # tick_size = coin.get("MINIMAL_TICK_SIZE")   
    timeframe = coin.get("TIMEFRAME")
    
        
    if allowed_min_bars > len(data_df):
        logger.error(f"Невозможно запустить бектест: не хватает баров для расчета индикаторов.")
        return {}
    
    # Инициализация стратегии    
    strategy = ZigZagAndFibo(coin=coin)
    # Создаём модель позиции и менеджер, который управляет этой позицией
    
    manager = PositionManager()
    engine = ExecutionEngine(manager)
    position: Optional[Position] = None

    
    
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
        logger.info(f"[{current_index.strftime("%d.%m.%Y %H:%M")}] [yellow]- open: {current_open}, high: {current_high}, low: {current_low}, close: {current_close}[/yellow]")    
        
        #-------------------------------------------------------------
        # Алгоритм входа в позицию и создание позиции
        #-------------------------------------------------------------
        # рассчитываем индикаторы стратегии ищем точку входа
        signal = strategy.find_entry_point(current_data)
        
        #-------------------------------------------------------------
        # проверяем если появился противоположный сигнал
        # закрываем позицию
        #-------------------------------------------------------------
        if position is not None and signal != {}:
            if position.direction != signal['direction']:
                logger.debug(f"⚠️ Внимание: получен противоположный сигнал, позиция открыта {position.id[:6]}.")
                logger.debug(f"🔶 Закрываем позицию по рынку перед открытием новой позиции.")
                
                # Отменяем все активные ордера
                manager.cansel_active_orders(position.id, close_bar=current_index)
                
                # создаем закрывающий маркет ордер по текущей рыночной цене
                manager.close_position_at_market(position.id, Decimal(str(current_open)), close_bar=current_index)
           
        #-------------------------------------------------------------
        # Если нет открытой позиции, и есть сигнал на вход
        #-------------------------------------------------------------
        if position is None and signal != {}:
            # создание новой позиции по сигналу
            logger.debug(f"[{symbol}]🔷 Сигнал на вход получен: {signal.get('direction')} по цене {signal.get('price')}")
            position = create_position(signal=signal, manager=manager, coin=coin, current_index=current_index)
            if position is None:
                logger.error(f"[{symbol}]🔴 Позиция не создана")
            else:    
                logger.debug(f"[{symbol}]--------------------------------------------------")
                


        #-------------------------------------------------------------
        # Обработка исполнения ордеров на текущем баре
        #-------------------------------------------------------------
        if position is not None: # если есть position   
            # перебираем текущий бар по минутным данным для более точного исполнения стопов и тейков
            start_1m    = current_index
            end__1m     = shift_timestamp(current_index, 1, timeframe, direction=+1)

            current_range_1m = select_range(data_df_1m, start_1m, end__1m)
            
            arr_1m = current_range_1m[['open','high','low','close']].copy()
            arr_1m['dt'] = current_range_1m.index.to_numpy()
            arr_1m = arr_1m.to_numpy()
            
            # обрабатываем исполнение ордеров
            process_orders(position=position, engine=engine,  current_range_1m=arr_1m)        
                    
        #-------------------------------------------------------------
        # Алгоритм закрытия позиции
        #-------------------------------------------------------------
        if position is not None and position.status in {Position_Status.TAKEN_FULL, Position_Status.STOPPED, Position_Status.TAKEN_PART, Position_Status.CANCELED}:
            # если активных ордеров нет, позиция закрыта
            manager.cansel_active_orders(position.id, close_bar=current_index)
            position.bar_closed = current_index

            # executed_positions.append(position)
            # сбрасываем позицию
            position: Optional[Position] = None
            

    return manager.positions

# создаем позицию по сигналу
def create_position(signal, manager, coin, current_index) -> Optional[Position]:
    direction = signal['direction']
    symbol = coin.get("SYMBOL")+"/USDT"
    tick_size = Decimal(str(coin.get("MINIMAL_TICK_SIZE")))

    # Риск менеджмент - установка объема позиции
    entry_price = signal.get("price")
    if entry_price is None:
        logger.error("Ошибка: цена входа не определена в сигнале.")
        return None
    else:
        # 1. создаем позицию
        position = manager.open_position(symbol=symbol, direction=direction, tick_size=tick_size, open_bar=current_index)
        
        entry_price = position.round_to_tick(Decimal(entry_price))
        # -------------------------------------------------------------
        # Добавить риск менеджмент - расчет объема позиции
        # -------------------------------------------------------------
        # объем позиции в нативной валюте (например, в BTC) покупаем по текущей цене
        rm = RiskManager(coin=coin)
        volume = rm.calculate_position_size(entry_price=entry_price)
        

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
        return position



# метод исполнения ордера на баре 
# перебор по минутному таймфрейму   
def process_orders(position: Position, engine: ExecutionEngine, current_range_1m):
    try:
        logger.debug (f"♻️ Проверка исполнения ордеров для позиции {position.id[:6]}")
        for j in range(len(current_range_1m)):
            bar1m = current_range_1m[j]
            # передаем бар в движок исполнения
            engine.process_bar(bar=bar1m, bar_index=bar1m[4])
            
            # проверяем исполнен ли TP после которого переводим SL в без убыточность
            if position.status == Position_Status.ACTIVE and position.check_stop_break():
                # если закрыт хотя бы один TP, двигаем стоп в безубыточность
                position.move_stop_to_break_even()
    except Exception as e:
        logger.error(f"Ошибка при обработке ордеров: {e}")
        raise
        
        
