# backtest	Тестирование стратегии на исторических данных.	
# Симуляция выполнения сделок. 
# Расчет метрик производительности (прибыльность, просадка, Sharpe Ratio).
from uuid import uuid4
from typing import Dict, Any, Tuple, List
from pandas import DataFrame
import pandas as pd

from decimal import Decimal
from typing import Optional
# Логирование
# ====================================================
from src.utils.logger import get_logger
logger = get_logger(__name__)


from src.logical.strategy.zigzag_fibo.zigzag_and_fibo import ZigZagAndFibo
from src.trading_engine.managers.position_manager import PositionManager, Position
from src.trading_engine.orders.order_factory import  make_order
from src.trading_engine.core.enums import OrderType, Position_Status
from src.backtester.v3.engine.execution_engine import ExecutionEngine
from src.risk_manager.risk_manager import RiskManager

from src.data_fetcher.utils import select_range, shift_timestamp

ALLOWED_Z2_OFFSET = 1  # сколько баров назад допускается последняя точка zigzag

# Класс Test 
class Test():
    """
    Класс тестирования стратегии на исторических данных.
    содержит результаты тестирования и расчетную статистику
    """
    def __init__(self, data, coin, settings_test):
        # параметры теста
        self.id = uuid4().hex
        self.coin = coin # монета и её настройки из файла конфигурации
        self.settings_test = settings_test # настройки тестирования из файла конфигурации
        self.symbol, self.timeframe = coin.get("SYMBOL"), coin.get("TIMEFRAME")
        
        # Результаты теста
        self.ohlcv = data # данные истории по которым проводится тест
        self.positions = {} # список позиций в каждой позиции есть ордера 
        self.equity_curve = []               # equity на каждом баре
        self.drawdown_curve = []             # просадка на каждом баре
        # у позиции есть ордера 
        # входа и выхода, 
        # направление long и short,
        # дата и время исполнения,
        # объем 
        # цена исполнения
        
        # статистика теста расчитывается после получения результатов тестирования
        self.balance = self.coin.get("START_DEPOSIT_USDT")  # только закрытые сделки
        self.equity = self.coin.get("START_DEPOSIT_USDT")   # balance + floating_profit  
        self.max_drawdown = Decimal("0")
        self.metrics = {}
        
        # self.realized_pnl          = Decimal("0") # общий PnL
        
        # self.total_pnl          = Decimal("0") # общий PnL
        # self.total_loss         = Decimal("0") # общий убыток
        # self.total_win          = Decimal("0") # общий прибыль
        # self.wins               = Decimal("0") # общее количество побед
        # self.losses             = Decimal("0") # общее количество проигрышей
        # self.count_positions    = Decimal("0") # общее количество позиций
        # self.winrate            = Decimal("0") # процент побед
        

        
    # def calculate_statistics(self):
        
    #     # TODO: Добавить расчеты статистики
    #     self.total_pnl = sum(pos.realized_pnl for pos in self.positions.values())
    #     self.total_win = sum(pos.realized_pnl for pos in self.positions.values() if pos.realized_pnl > 0)
    #     self.total_loss = sum(pos.realized_pnl for pos in self.positions.values() if pos.realized_pnl < 0)
    #     self.wins = sum(1 for pos in self.positions.values() if pos.realized_pnl > 0)
    #     self.losses = sum(1 for pos in self.positions.values() if pos.realized_pnl < 0)
    #     self.count_positions = len(self.positions)
    #     self.winrate = (self.wins / self.count_positions * 100) if self.count_positions > 0 else 0
        
        # Максимальная просадка
        
    #     # TODO: Добавить расчеты статистики прибыльности
    #     # ==================================
    #     # ? Добавить вызовы расчетов:
    #     # ==================================



    # ====================================================
    # ? Запуск бэктеста для одной монеты
    # ====================================================
    def backtest_coin(self, data_df_1m):
        # * Запуск бэктеста с данными, загруженными из локального файла.
        # *:param data_df: pd.DataFrame — исторические данные по монете
        # *:param data_df_1m: pd.DataFrame — исторические данные по монете на 1 минуту
        # *:param coin: dict — конфигурация монеты
        
        # ! Инициализация стратегии    
        strategy = ZigZagAndFibo(coin=self.coin)
        
        manager = PositionManager()
        engine = ExecutionEngine(manager)
        position: Optional[Position] = None
        
        
        
        # Это нужно для того, чтобы индикаторы были заполнены
        arr = self.ohlcv[['open','high','low','close']].copy()
        arr['dt'] = self.ohlcv.index.to_numpy()
        arr = arr.to_numpy()
        
        # ! перебираем все бары начиная с минимального количества нужного для расчета стратегии
        for i in range(strategy.allowed_min_bars, len(arr)):
            current_data    = arr[i-strategy.allowed_min_bars:i] # окно для расчета индикаторов
            current_open    = arr[i][0] # текущий бар открытие
            current_high    = arr[i][1] # текущий бар высота
            current_low     = arr[i][2] # текущий бар низ
            current_close   = arr[i][3] # текущий бар закрытие
            current_index   = arr[i][4] # текущий бар индекс (Datetime)
            
            logger.debug(f"[yellow]----------------------------------------------------------- [/yellow]")
            logger.debug(f"[{current_index.strftime("%d.%m.%Y %H:%M")}] [yellow]- open: {current_open}, high: {current_high}, low: {current_low}, close: {current_close}[/yellow]")    
            
            #-------------------------------------------------------------
            #  * Запуск расчета стратегии
            #-------------------------------------------------------------
            # ! рассчитываем индикаторы стратегии ищем точку входа
            signal = strategy.find_entry_point(current_data)
            
            # TODO Перенести в торговую логику
            #-------------------------------------------------------------
            # ! появился противоположный сигнал закрываем позицию
            #-------------------------------------------------------------
            if position is not None and signal != {}:
                if position.direction != signal['direction']:
                    logger.debug(f"⚠️ Внимание: получен противоположный сигнал, позиция открыта {position.id[:6]}.")
                    logger.debug(f"🔶 Закрываем позицию по рынку перед открытием новой позиции.")
                    
                    # Отменяем все активные ордера
                    manager.cansel_active_orders(position.id, close_bar=current_index)
                    
                    # создаем закрывающий маркет ордер по текущей рыночной цене
                    manager.close_position_at_market(position.id, Decimal(str(current_open)), close_bar=current_index)

            # TODO Перенести в торговую логику
            #-------------------------------------------------------------
            # Если нет открытой позиции, и есть сигнал на вход
            #-------------------------------------------------------------
            if position is None and signal != {}:
                # создание новой позиции по сигналу
                logger.debug(f"[{self.symbol}]🔷 Сигнал на вход получен: {signal.get('direction')} по цене {signal.get('price')}")
                position = self.create_position(signal=signal, manager=manager, coin=self.coin, current_index=current_index)
                if position is None:
                    logger.error(f"[{self.symbol}]🔴 Позиция не создана")
                else:    
                    logger.debug(f"[{self.symbol}]--------------------------------------------------")

            
            
            #-------------------------------------------------------------
            # ! Обработка исполнения ордеров на текущем баре
            # TODO Перебрать все позиции по текущему symbol 
            #-------------------------------------------------------------
            if position is not None: # если есть position   
                # перебираем текущий бар по минутным данным для более точного исполнения стопов и тейков
                start_1m    = current_index
                end__1m     = shift_timestamp(current_index, 1, self.timeframe, direction=+1)

                current_range_1m = select_range(data_df_1m, start_1m, end__1m)
                
                arr_1m = current_range_1m[['open','high','low','close']].copy()
                arr_1m['dt'] = current_range_1m.index.to_numpy()
                arr_1m = arr_1m.to_numpy()
                
                # обрабатываем исполнение ордеров
                self.process_orders(position=position, engine=engine,  current_range_1m=arr_1m)        
                        
            #-------------------------------------------------------------
            # ! Алгоритм закрытия позиции
            #-------------------------------------------------------------
            if position is not None and position.status in {
                Position_Status.ACTIVE, 
                Position_Status.TAKEN_FULL, 
                Position_Status.STOPPED, 
                Position_Status.TAKEN_PART, 
                Position_Status.CANCELED
                }:
                
                # если активных ордеров нет, позиция закрыта
                manager.cansel_active_orders(position.id, close_bar=current_index)
                position.bar_closed = current_index
                position = None
                
            # ============================================================
            # ! РАСЧЕТ PnL / EQUITY / DRAWDOWN НА БАРЕ
            # ============================================================
            # TODO расчет баланса на баре
            # TODO расчет PnL на баре
            
            # ============================================================
            # РАСЧЕТ PnL / EQUITY / DRAWDOWN НА БАРЕ (ИСПРАВЛЕННЫЙ)
            # ============================================================
            current_price = Decimal(str(current_close))
            
            # 1. Реализованный PnL за этот бар
            realized_pnl = self.calculate_realized_pnl_on_bar(
                manager=manager,
                current_index=current_index
            )
            
            # 2. Обновляем баланс (только реализованный PnL)
            self.balance += realized_pnl
            
            # 3. Плавающий PnL по всем активным позициям
            floating_pnl = self.calculate_floating_pnl_on_bar(
                manager=manager,
                high_price=Decimal(str(current_high)),
                low_price=Decimal(str(current_low))
            )
            
            # 4. Equity = баланс + плавающий PnL
            self.equity = self.balance + floating_pnl
            
            # # 7. Сохраняем все метрики
            # self.equity_curve.append({
            #     'timestamp': current_index,
            #     'equity': self.equity,
            #     'balance': self.balance,
            #     'floating_pnl': floating_pnl,
            #     'realized_pnl_delta': realized_pnl,
                
            # })
            
            # # 8. Сохраняем просадку отдельно
            # self.drawdown_curve.append(drawdown_stats['drawdown_pct'])
            
            # Логирование для отладки (можно уменьшить частоту)
            logger.info(f"[{current_index.strftime('%d.%m.%Y %H:%M')}] "
                f"Баланс: {self.balance:.2f}, "
                f"Эквити: {self.equity:.2f}, ")
            
            
            
            
        self.positions = manager.positions
        # return manager.positions


    
    # создаем позицию по сигналу
    def create_position(self, signal, manager: PositionManager, coin, current_index) -> Optional[Position]:
        direction = signal['direction']
        symbol = coin.get("SYMBOL")+"/USDT"
        tick_size = Decimal(str(coin.get("MINIMAL_TICK_SIZE")))

        # Риск менеджмент - установка объема позиции
        entry_price = signal.get("price", None)
        if entry_price is None:
            logger.error("Ошибка: цена входа не определена в сигнале.")
            return None
        else:
            # 1. создаем позицию
            position = manager.open_position(symbol=symbol, direction=direction, tick_size=tick_size, open_bar=current_index)
            
            # Цена входа округляем до ближайшего тикера
            entry_price = position.round_to_tick(Decimal(entry_price))
            

            # Риск менеджмент - расчет объема позиции
            # объем позиции в нативной валюте (например, в BTC) покупаем по текущей цене
            rm = RiskManager(coin=coin)
            volume = rm.calculate_position_size(entry_price=entry_price)
            

            # создаем ордер на вход в позицию
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
    def process_orders(self, position: Position, engine: ExecutionEngine, current_range_1m):
        try:
            logger.debug (f"♻️ Проверка исполнения ордеров для позиции {position.id[:6]}")
            for j in range(len(current_range_1m)):
                bar1m = current_range_1m[j]
                # передаем бар в движок исполнения
                engine.process_bar(bar=bar1m, bar_index=bar1m[4])
                
        except Exception as e:
            logger.error(f"Ошибка при обработке ордеров: {e}")
            raise
        
        
    # # ------------------------------------------------------------------------------------
    # # ? Модуль расчета показателей на баре 
    # # ------------------------------------------------------------------------------------
    # Расчет реализованного PnL на баре
    def calculate_realized_pnl_on_bar(self, manager: PositionManager, current_index) -> Decimal:
        realized = Decimal("0")

        for pos in manager.positions.values():
            for exec in pos.executions:
                if exec.bar_index == current_index:
                    realized += exec.realized_pnl

        return realized
    
    
    def calculate_floating_pnl_on_bar(
        self,
        manager: PositionManager,
        high_price: Decimal, low_price: Decimal
    ) -> Decimal:
        floating = Decimal("0")

        for pos in manager.positions.values():
            if pos.status == Position_Status.ACTIVE:
                unrealized = pos.calc_worst_unrealized_pnl(high_price, low_price)
                floating += unrealized
        
        return floating




