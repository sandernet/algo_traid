"""
Universal position & order management module for algorithmic trading.

Features:
- Order abstraction (ENTRY/TP/SL/CLOSE/..)
- Position with multi-entry & multi-exit support
- ExecutionEngine: simulates bar-by-bar execution (OHLC)
- PositionManager: manages multiple positions (hedging supported)
- Decimal arithmetic for prices/volumes
- Simple demonstration at bottom

Notes:
- Execution rules are simplified for backtest: when a bar's range touches a price, the order is considered filled at that price (or slight rules for stop/limit)
- Extend ExecutionEngine.should_execute logic to match your exchange/order model if needed.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from decimal import Decimal, ROUND_HALF_UP, getcontext
from typing import List, Optional, Dict, Any
from uuid import uuid4
import logging

from datetime import datetime, timedelta

# установите достаточно высокую десятичную точность
getcontext().prec = 18

# Configure logger
logger = logging.getLogger("position_module")
if not logger.handlers:
    h = logging.StreamHandler()
    h.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
    logger.addHandler(h)
logger.setLevel(logging.INFO)


# -------------------------
# перевод в Decimal
# -------------------------
def to_decimal(v: Any) -> Decimal:
    if isinstance(v, Decimal):
        return v
    return Decimal(str(v))


class Position_Status(Enum):
    ACTIVE = "active"
    TAKEN_PART = "part_taken"
    TAKEN_FULL = "taken_full"
    STOPPED = "stopped"
    CANCELED = "cancelled"
    NONE = "none"
    CREATED = "created"


class OrderType(Enum):
    ENTRY = "entry"     # вход в позицию
    TAKE_PROFIT = "tp"  # тейк-профит
    STOP_LOSS = "sl"    # стоп-лосс
    CLOSE = "close"     # закрытие позиции
    TRAILING_STOP = "trailing_stop" # трейлинг-стоп
    LIMIT = "limit"   # лимитный ордер
    MARKET = "market"  # рыночный ордер


class OrderStatus(Enum):
    ACTIVE = "active"
    FILLED = "filled"
    CANCELLED = "cancelled"
    PARTIAL = "partial"


class Direction(Enum):
    LONG = "long"
    SHORT = "short"


# -------------------------
# Core data structures
# -------------------------
@dataclass
class Execution:
    price: Decimal
    volume: Decimal
    bar_index: int
    order_id: str


@dataclass
class Order:
    id: str
    order_type: OrderType
    price: Optional[Decimal]  # Нет для рыночных ордеров
    volume: Decimal           # абсолютный объем в нативных единицах (не дробях)
    direction: Direction      #направление: ДЛИННОЕ или КОРОТКОЕ (влияет на интерпретацию стопов)
    status: OrderStatus = OrderStatus.ACTIVE
    filled: Decimal = field(default_factory=lambda: Decimal("0"))
    created_at: Optional[int] = None  # optional bar index when created
    created_dt: Optional[datetime] = None  # optional bar index when created
    meta: Dict[str, Any] = field(default_factory=dict)

    # ------------------------
    # Метод управления остатком объема ордера
    # ------------------------
    def remaining(self) -> Decimal:
        return max(Decimal("0"), self.volume - self.filled)

    # ------------------------
    # Метод управления заполнением ордера
    # ------------------------
    def mark_filled(self, amount: Decimal):
        self.filled += amount
        if self.filled >= self.volume:
            # полный объем ордера заполнен
            self.status = OrderStatus.FILLED
        else:
            # частичное заполнение ордера
            self.status = OrderStatus.PARTIAL
            



class Position:
    """
    Позиция объединяет ордера и исполнения.
    Он НЕ сам принимает решения о выполнении — это делает ExecutionEngine.
    """
    def __init__(self, symbol: str, direction: Direction, tick_size: Optional[float] = None):
        self.id = uuid4().hex # уникальный идентификатор позиции
        self.symbol = symbol      # торговый символ / инструмент
        self.direction = direction # направление позицией (long/short)
        self.status = Position_Status.CREATED
        self.orders: List[Order] = []        # все связанные заказы (entry, tp, sl, ...)
        self.executions: List[Execution] = []  # все исполнения, связанные с этой позицией
        self.opened_volume: Decimal = Decimal("0") # общий открытый объем
        self.closed_volume: Decimal = Decimal("0") # общий закрытый объем
        self.avg_entry_price: Optional[Decimal] = None # средняя цена входа
        self.profit: Decimal = Decimal("0")      # накопленная прибыль / убыток по позиции
        self.tick_size = to_decimal(tick_size) if tick_size is not None else None # размер тика для округления цен
        self.meta: Dict[str, Any] = {}          # дополнительная информация о позиции

    # ------------------------
    # Order management
    # ------------------------
    def add_order(self, order: Order):
        logger.debug(f"Position {self.id}: adding order {order.id} {order.order_type} {order.price} {order.volume}")
        self.orders.append(order)

    # Отмена ордера по ID
    def cancel_order(self, order_id: str):
        for o in self.orders:
            if o.id == order_id and o.status == OrderStatus.ACTIVE:
                o.status = OrderStatus.CANCELLED
                logger.info(f"Order {order_id} cancelled")

    # Отмена ордера по типу
    def cancel_orders_by_type(self, otype: OrderType):
        for o in self.orders:
            if o.order_type == otype and o.status == OrderStatus.ACTIVE:
                o.status = OrderStatus.CANCELLED
                logger.info(f"Order {o.id} of type {otype} cancelled")

    # ------------------------
    # Управление исполнением
    # ------------------------
    def record_execution(self, order: Order, price: Decimal, volume: Decimal, bar_index: int):
        """
        Применить исполнение к позиции и обновить состояние.
        1. Записать исполнение
        2. Обновить состояние позиции
        """
        ex = Execution(price=to_decimal(price), volume=to_decimal(volume), bar_index=bar_index, order_id=order.id)
        self.executions.append(ex)

        # по объему пометить ордер как заполненный (полностью или частично)
        # поменяет статус ордера соответственно
        order.mark_filled(to_decimal(volume))

        # update volumes and average price for entries/closings
        # управление объемами и средней ценой для входов/закрытий
        if order.order_type == OrderType.ENTRY:
            prev_total = self.opened_volume * (self.avg_entry_price or Decimal("0"))
            self.opened_volume += to_decimal(volume)
            if self.avg_entry_price is None:
                self.avg_entry_price = to_decimal(price)
            else:
                # пересчитать среднюю цену входа
                self.avg_entry_price = (prev_total + to_decimal(price) * to_decimal(volume)) / self.opened_volume

            # mark active if at least some opened
            self.status = Position_Status.ACTIVE

        # если это закрывающий ордер (TP/SL/CLOSE)
        elif order.order_type in {OrderType.TAKE_PROFIT, OrderType.CLOSE, OrderType.STOP_LOSS}:
            # обновить закрытый объем
            self.closed_volume += to_decimal(volume)
            # рассчитать PnL для закрытого объема
            if self.avg_entry_price is not None:
                if self.direction == Direction.LONG:
                    pnl = (to_decimal(price) - self.avg_entry_price) * to_decimal(volume)
                else:
                    pnl = (self.avg_entry_price - to_decimal(price)) * to_decimal(volume)
                self.profit += pnl

        # обновить статус позиции
        if self.opened_volume > Decimal("0") and self.closed_volume >= self.opened_volume:
            self.status = Position_Status.TAKEN_FULL if self.profit >= 0 else Position_Status.STOPPED

        logger.info(f"Executed {order.order_type.value} order {order.id} @ {price} x {volume} (pos {self.id}). "
                    f"opened_vol={self.opened_volume} closed_vol={self.closed_volume} avg_entry={self.avg_entry_price} pnl={self.profit}")

    # ------------------------
    # Позиционные утилиты
    # ------------------------
    # Оставшийся объем для закрытия
    def remaining_volume(self) -> Decimal:
        return max(Decimal("0"), self.opened_volume - self.closed_volume)
        # ------------------------
    # Метод расчета части объема ордера
    # ------------------------
    def part_volume(self, share: Decimal) -> Decimal:
        return (self.opened_volume * share).quantize(Decimal('1.'), rounding=ROUND_HALF_UP)
    
    # Получить активные заказы 
    
    def get_active_orders(self) -> List[Order]:
        return [o for o in self.orders if o.status == OrderStatus.ACTIVE]

    # Получить заказы по типу
    def get_orders_by_type(self, otype: OrderType) -> List[Order]:
        return [o for o in self.orders if o.order_type == otype and o.status == OrderStatus.ACTIVE]

    # Округление цены до размера тика
    def round_to_tick(self, price: Decimal) -> Decimal:
        if not self.tick_size:
            return price
        if self.tick_size <= 0:
            return price
        q = (to_decimal(price) / self.tick_size).quantize(Decimal('1'), rounding=ROUND_HALF_UP)
        return q * self.tick_size

    # Переместить стоп-лосс к безубыточности
    def move_stop_to_break_even(self):
        if self.avg_entry_price is None:
            logger.warning("Cannot move stop to break-even: no entries yet")
            return None
        be_price = self.avg_entry_price
        # cancel existing active stops and add new stop at entry price
        self.cancel_orders_by_type(OrderType.STOP_LOSS)
        new_stop = Order(
            id=uuid4().hex,
            order_type=OrderType.STOP_LOSS,
            price=self.round_to_tick(be_price),
            volume=self.remaining_volume(),
            direction=self.direction
        )
        self.add_order(new_stop)
        logger.info(f"Position {self.id}: stop moved to break-even at {new_stop.price}")
        return new_stop

    def __repr__(self):
        return f"<Position id={self.id[:6]} sym={self.symbol} dir={self.direction.value} status={self.status.value} opened={self.opened_volume} closed={self.closed_volume} avg_entry={self.avg_entry_price} pnl={self.profit}>"


# -------------------------
# Manager & Executor
# -------------------------
class PositionManager:
    """
    Управление позициями: открытие, закрытие, получение списка позиций.
    Поддерживает множественные позиции на один и тот же символ (хеджирование).
    """
    def __init__(self):
        self.positions: Dict[str, Position] = {}
    # ------------------------
    # открытие 
    # ------------------------
    def open_position(self, symbol: str, direction: Direction, tick_size: Optional[float] = None) -> Position:
        pos = Position(symbol=symbol, direction=direction, tick_size=tick_size)
        self.positions[pos.id] = pos
        logger.info(f"Открыта новая позиция {pos.id} {symbol} {direction.value}")
        return pos

    # ------------------------
    # закрытие по ID
    # ------------------------
    def close_position(self, position_id: str):
        pos = self.positions.get(position_id)
        if not pos:
            return
        # cancel active orders
        for o in pos.get_active_orders():
            o.status = OrderStatus.CANCELLED
        pos.status = Position_Status.CANCELED
        logger.info(f"Position {position_id} closed/cancelled by manager")

    # ------------------------
    # Получить позиции по символу и/или направлению
    # ------------------------
    def get_positions(self, symbol: Optional[str] = None, direction: Optional[Direction] = None) -> List[Position]:
        res = list(self.positions.values())
        if symbol:
            res = [p for p in res if p.symbol == symbol]
        if direction:
            res = [p for p in res if p.direction == direction]
        return res





# -------------------------
# Создание ордеров
# -------------------------
def make_order(order_type: OrderType, price: Optional[float], volume: float, direction: Direction, created_dt: Optional[datetime] = None, meta: Optional[Dict[str, Any]] = None) -> Order:
    """
    Создать ордер на основе параметров.
    
    :param order_type: тип ордера (MARKET, TAKE_PROFIT, STOP_LOSS, LIMIT, ENTRY)
    :param price: цена ордера (если достигнута)
    :param volume: объем ордера
    :param direction: направление ордера (LONG, SHORT)
    :param created_at: метка создания ордера (если не указана, то текущая метка)
    :param meta: мета-информация ордера (необязательный параметр)
    :return: созданный ордер
    """
    return Order(
        id=uuid4().hex,
        order_type=order_type,
        price=to_decimal(price) if price is not None else None,
        volume=to_decimal(volume),
        direction=direction,
        created_at=0,
        created_dt=created_dt,
        meta=meta or {}
    )


# # -------------------------
# # Demo / Example usage
# # -------------------------
# if __name__ == "__main__":
#     import random
    

#     # Simple demo: simulate a small synthetic series of OHLC bars and show position behavior
#     def generate_bars(n=30, start_price=100.0):
#         bars = []
#         p = float(start_price)
#         now = datetime.now()
#         for i in range(n):
#             # random walk
#             o = p
#             h = o + abs(random.gauss(0, 1.5))
#             l = o - abs(random.gauss(0, 1.5))
#             c = l + random.random() * (h - l)
#             bars.append({'time': now + timedelta(minutes=i), 'open': o, 'high': h, 'low': l, 'close': c})
#             p = c
#         return bars

#     # Setup manager and engine
#     manager = PositionManager()
#     # engine = ExecutionEngine(manager)

#     bars = generate_bars(n=60, start_price=100.0)

#     # открытие позиций (long и short)
#     pos_long = manager.open_position("BTCUSDT", Direction.LONG, tick_size=0.01)
#     pos_short = manager.open_position("BTCUSDT", Direction.SHORT, tick_size=0.01)

#     # Add entry orders (limit) for both (these are examples; they may or may not be hit)
#     entry_long = make_order(OrderType.ENTRY, price=99.0, volume=0.5, direction=Direction.LONG, created_dt=datetime.now())
#     entry_short = make_order(OrderType.ENTRY, price=102.0, volume=0.3, direction=Direction.SHORT, created_dt=datetime.now())
    
#     pos_long.add_order(entry_long)
#     pos_short.add_order(entry_short)

#     # Add stop & tp for the long (if entry filled)
#     # The strategy would normally add TP/SL after entry is filled; here we add in advance for demo.
#     tp1_long = make_order(OrderType.TAKE_PROFIT, price=105.0, volume=0.25, direction=Direction.LONG)
#     tp2_long = make_order(OrderType.TAKE_PROFIT, price=108.0, volume=0.25, direction=Direction.LONG)
    
#     sl_long = make_order(OrderType.STOP_LOSS, price=95.0, volume=0.5, direction=Direction.LONG)
#     pos_long.add_order(tp1_long)
#     pos_long.add_order(tp2_long)
#     pos_long.add_order(sl_long)

#     # Add stop & tp for the short
#     tp_short = make_order(OrderType.TAKE_PROFIT, price=96.0, volume=0.3, direction=Direction.SHORT)
#     sl_short = make_order(OrderType.STOP_LOSS, price=106.0, volume=0.3, direction=Direction.SHORT)
#     pos_short.add_order(tp_short)
#     pos_short.add_order(sl_short)

#     # Process bars
#     for idx, b in enumerate(bars):
#         logger.debug(f"Processing bar {idx} o={b['open']:.2f} h={b['high']:.2f} l={b['low']:.2f} c={b['close']:.2f}")
#         engine.process_bar(b, idx)

#         # Example dynamic logic: if long partial profit at TP1 done, move stop to BE
#         # (Simplified: check if TP1 was filled by inspecting orders)
#         active_tps = [o for o in pos_long.orders if o.order_type == OrderType.TAKE_PROFIT and o.price == to_decimal(105.0)]
#         if active_tps:
#             tp_o = active_tps[0]
#             if tp_o.status == OrderStatus.FILLED:
#                 # move stop to break-even after first TP executed
#                 pos_long.move_stop_to_break_even()
#                 # prevent further repeated moves: cancel this tp to avoid double-trigger (demo-only)
#                 # In real flow you would track via state
#         # quick stop: if both positions fully closed, break
#         if pos_long.status in {Position_Status.TAKEN_FULL, Position_Status.STOPPED} and pos_short.status in {Position_Status.TAKEN_FULL, Position_Status.STOPPED}:
#             # both ended
#             pass

#     # Print summary
#     print("=== Summary ===")
#     for pid, p in manager.positions.items():
#         print(p)
#         print("Orders:")
#         for o in p.orders:
#             print(f"  {o.order_type.value} id={o.id[:6]} price={o.price} vol={o.volume} status={o.status.value} filled={o.filled}")
#         print("Executions:")
#         for e in p.executions:
#             print(f"  exec {e.order_id[:6]} @ {e.price} x {e.volume} on bar {e.bar_index}")
#         print()


