from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from decimal import Decimal, ROUND_HALF_UP, getcontext
from typing import List, Optional, Dict, Any
from uuid import uuid4
from datetime import datetime


# Логирование
# ====================================================
from src.utils.logger import get_logger
logger = get_logger(__name__)


# установите достаточно высокую десятичную точность
getcontext().prec = 18


# -------------------------
# перевод в Decimal
# -------------------------
def to_decimal(v: Any) -> Decimal:
    if isinstance(v, Decimal):
        return v
    return Decimal(str(v))


class Position_Status(Enum):
    ACTIVE = "active"           #активная позиция
    TAKEN_PART = "part_taken"   #финальный статус, когда позиция была исполнена частично
    TAKEN_FULL = "taken_full"   #финальный статус, когда позиция была исполнена полностью
    STOPPED = "stopped"         #финальный статус, когда позиция была остановлена по стоп-лоссу в минусе
    CANCELED = "cancelled"      #финальный статус, когда позиция была отменена (профит может быть как положительный так и отрицательный)
    NONE = "none"               #начальный статус, когда позиция не создана
    CREATED = "created"         #начальный статус, когда позиция создана


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
    bar_index: Optional[datetime]  # индекс бара исполнения
    order_id: str
    realized_pnl: Decimal = Decimal("0")



@dataclass
class Order:
    id: str
    order_type: OrderType
    price: Optional[Decimal]  # Нет для рыночных ордеров
    volume: Decimal           # абсолютный объем в нативных единицах (не дробях)
    direction: Direction      #направление: ДЛИННОЕ или КОРОТКОЕ (влияет на интерпретацию стопов)
    profit: Optional[Decimal] = Decimal("0")  # результат исполнения ордера
    status: OrderStatus = OrderStatus.ACTIVE
    filled: Decimal = field(default_factory=lambda: Decimal("0"))
    created_bar: Optional[datetime] = None  # optional bar index when created
    close_bar: Optional[datetime] = None  # optional bar index when closed
    meta: Dict[str, Any] = field(default_factory=dict)

    # ------------------------
    # Метод управления остатком объема ордера
    # ------------------------
    def remaining(self) -> Decimal:
        return max(Decimal("0"), self.volume - self.filled)

    # ------------------------
    # Метод управления заполнением ордера
    # ------------------------
    def mark_filled(self, amount: Decimal, close_bar: datetime):
        self.filled += amount
        if self.filled >= self.volume:
            # полный объем ордера заполнен
            self.status = OrderStatus.FILLED
            self.close_bar = close_bar
        else:
            # частичное заполнение ордера
            # self.status = OrderStatus.FILLED
            self.status = OrderStatus.PARTIAL
            self.close_bar = close_bar
    
    # Расчет профита
    def calculate_profit(self, current_price: Decimal):
        if self.order_type in {OrderType.TAKE_PROFIT, OrderType.STOP_LOSS, OrderType.CLOSE} and self.price and self.volume:
            if self.direction == Direction.LONG:
                self.profit = (current_price - self.price) * self.volume
            else:
                self.profit = (self.price - current_price) * self.volume

    # Расчет профита
    def cancel_order(self, current_price: Decimal):
        if self.order_type in {OrderType.TAKE_PROFIT, OrderType.STOP_LOSS, OrderType.CLOSE} and self.price and self.volume:
            if self.direction == Direction.LONG:
                self.profit = (current_price - self.price) * self.volume
            else:
                self.profit = (self.price - current_price) * self.volume


class Position:
    """
    Позиция объединяет ордера и исполнения.
    Он НЕ сам принимает решения о выполнении — это делает ExecutionEngine.
    """
    def __init__(self, symbol: str, direction: Direction, tick_size: Optional[Decimal] = None):
        self.id = uuid4().hex # уникальный идентификатор позиции
        self.symbol = symbol      # торговый символ / инструмент
        self.direction = direction # направление позицией (long/short)
        self.status = Position_Status.CREATED
        self.orders: List[Order] = []        # все связанные заказы (entry, tp, sl, ...)
        self.executions: List[Execution] = []  # все исполнения, связанные с этой позицией
        self.opened_volume: Decimal = Decimal("0") # общий открытый объем
        self.closed_volume: Decimal = Decimal("0") # общий закрытый объем
        self.bar_opened: Optional[datetime] = None  # индекс бара, в котором была открыта позиция
        self.bar_closed: Optional[datetime] = None  # индекс бара, в котором была закрыта позиция
        self.avg_entry_price: Decimal = Decimal("0") # средняя цена входа
        self.realized_pnl: Decimal = Decimal("0")      # накопленная прибыль / убыток по позиции
        self.tick_size = tick_size if tick_size is not None else None # размер тика для округления цен
        self.meta: Dict[str, Any] = {}  # дополнительная информация о позиции  без убытка moved_to_break=true

    # ------------------------
    # Order management
    # ------------------------
    def add_order(self, order: Order):
        logger.info(f"[{self.symbol}] Позиция {self.id[:6]}: ордер {order.id[:6]} {order.order_type} /price = {order.price} /volume = {order.volume} /status = {order.status}")
        self.orders.append(order)

    # Отмена ордера по ID
    def __cancel_order(self, order_id: str):
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
    
    # проверка по переводу стопа в безубыточность
    def check_stop_break(self) -> bool:
        if self.opened_volume >= self.closed_volume and self.realized_pnl > Decimal("0"):
            checked = False
            for o in self.orders:
                if o.order_type == OrderType.TAKE_PROFIT and o.meta.get("tp_to_break") and o.status == OrderStatus.FILLED:
                    checked = True
                    continue
                
                if checked and o.order_type == OrderType.STOP_LOSS and not o.meta.get("moved_to_break") and o.status == OrderStatus.ACTIVE:
                    return True
        return False
    

    # ------------------------
    # Управление исполнением
    # ------------------------
    def record_execution(self, order: Order, price: Decimal, volume: Decimal, bar_index: datetime):
        """
        Применить исполнение к позиции и обновить состояние.
        1. Записать исполнение
        2. Обновить состояние позиции
        """
        # по объему пометить ордер как заполненный (полностью или частично)
        # поменяет статус ордера соответственно
        order.mark_filled(volume, bar_index)

        # ! управление объемами и средней ценой для входов/закрытий
        if order.order_type == OrderType.ENTRY:
            prev_total = self.opened_volume * self.avg_entry_price
            
            self.opened_volume += to_decimal(volume)
            
            if self.avg_entry_price == 0:
                self.avg_entry_price = to_decimal(price)
            else:
                # пересчитать среднюю цену входа
                self.avg_entry_price = (prev_total + to_decimal(price) * to_decimal(volume)) / self.opened_volume

            # mark active if at least some opened
            self.status = Position_Status.ACTIVE
            logger.info(f"☑️ Ордер {order.id[:6]} Тип: {order.order_type.value} Исполнен.  Объем: {order.volume}, Средняя цена входа: {self.avg_entry_price}")  

        # если это закрывающий ордер (TP/SL/CLOSE)
        elif order.order_type in {OrderType.TAKE_PROFIT, OrderType.CLOSE, OrderType.STOP_LOSS}:
            # обновить закрытый объем
            self.closed_volume += to_decimal(volume)
            # рассчитать PnL для закрытого объема
            if self.avg_entry_price is not None:
                if self.direction == Direction.LONG:
                    pnl = (price - self.avg_entry_price) * volume
                else:
                    pnl = (self.avg_entry_price - price) * volume
                self.realized_pnl += pnl
                order.profit = pnl
                logger.info(f"☑️ Ордер {order.id[:6]} [bool cyan] Тип:{order.order_type.value}[/bool cyan] Исполнен. Объем: {order.volume} profit: {order.profit}")

        # обновить статус позиции

        if  self.opened_volume > Decimal("0") and self.closed_volume >=  self.opened_volume:
            # закрыт весь объем позиции
            # Меняет Статус на закрывающий. Может быть TAKEN_FULL, STOPPED, TAKEN_PART
            self.setStatus()


        elif self.closed_volume > Decimal("0") and self.closed_volume  < self.opened_volume:
            # закрыта частично
            logger.info(f"[symbol]🟢 Позиция {self.id[:6]} частично закрыта. Статус: {self.status.value}")
            
        # записываем исполнение
        ex = Execution(price=price, volume=volume, bar_index=bar_index, realized_pnl=(order.profit or Decimal("0")), order_id=order.id) 
        self.executions.append(ex)



    # ------------------------
    # Позиционные утилиты
    # ------------------------
    
    # Расчет плавающего PnL
    def calc_worst_unrealized_pnl(self, high_price: Decimal, low_price: Decimal) -> Decimal:
        """
        Расчет плавающего PnL для активной позиции
        """
        if self.opened_volume <= Decimal("0") or self.status not in {
            Position_Status.ACTIVE, Position_Status.CREATED}:
            return Decimal("0")
        
        remaining_volume = self.opened_volume - self.closed_volume
        
        if remaining_volume <= Decimal("0"):
            return Decimal("0")
        
        if self.direction == Direction.LONG:
            # Для лонга: profit = (текущая цена - средняя цена входа) * оставшийся объем
            return (low_price - self.avg_entry_price) * remaining_volume
        else:
            # Для шорта: profit = (средняя цена входа - текущая цена) * оставшийся объем
            return (self.avg_entry_price - high_price) * remaining_volume
        
    
    
    # Устанавливает статус позиции
    def setStatus(self):
        if self.status == Position_Status.ACTIVE:
            sum_vol_tp = Decimal("0")
            sum_vol_sl = Decimal("0")
            sum_vol_cl = Decimal("0")
            
            for o in self.orders:
                if o.status in {OrderStatus.FILLED, OrderStatus.PARTIAL} and o.order_type == OrderType.TAKE_PROFIT:
                    sum_vol_tp += o.volume
                if o.status in {OrderStatus.FILLED, OrderStatus.PARTIAL} and o.order_type == OrderType.STOP_LOSS:
                    sum_vol_sl += o.volume
                if o.status in {OrderStatus.FILLED, OrderStatus.PARTIAL} and o.order_type == OrderType.CLOSE:
                    sum_vol_cl += o.volume

            if sum_vol_cl > Decimal("0"):
                self.status = Position_Status.CANCELED
                logger.info(f"✅ Позиция {self.id[:6]} закрыта. Статус: {self.status.value}"
                            )
            elif sum_vol_tp > Decimal("0") and sum_vol_sl > Decimal("0"):
                self.status = Position_Status.TAKEN_PART
                logger.info(f"✅ Позиция {self.id[:6]} частично закрыта в профит и закрыта в без убыток. Статус: {self.status.value}")
                
            elif sum_vol_tp >= self.opened_volume:
                self.status = Position_Status.TAKEN_FULL
                logger.info(f"✅ Позиция {self.id[:6]} полностью закрыта в профит Закрыты все TP. Статус: {self.status.value}")
                
            elif sum_vol_sl >= self.opened_volume:
                self.status = Position_Status.STOPPED
                logger.info(f"✅ Позиция {self.id[:6]} полностью закрыта по SL. Статус: {self.status.value}")
                
                
                
    # Оставшийся объем для закрытия
    def remaining_volume(self) -> Decimal:
        return max(Decimal("0"), self.opened_volume - self.closed_volume)
    
    # Получить активные заказы 
    def get_active_orders(self) -> List[Order]:
        return [o for o in self.orders if o.status == OrderStatus.ACTIVE]

    # Получить ордера по типу только активные
    def get_orders_by_type(self, otype: OrderType, active_only: bool = True) -> List[Order]:
        if active_only:
            return [o for o in self.orders if o.order_type == otype and o.status == OrderStatus.ACTIVE]
        else:
            return [o for o in self.orders if o.order_type == otype]

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
            logger.warning("Невозможно переместить стоп в безубыток: записей пока нет.")
            return None
        be_price = self.avg_entry_price # Средняя цена входа
        # отменить существующие активные стопы и добавить новый стоп по цене входа
        self.cancel_orders_by_type(OrderType.STOP_LOSS)
        new_stop = Order(
            id=uuid4().hex,
            order_type=OrderType.STOP_LOSS,
            price=self.round_to_tick(be_price),
            volume=self.remaining_volume(),
            direction=self.direction,
            meta={"moved_to_break": True}
        )
        self.add_order(new_stop)
        logger.info(f"Позиция {self.id[:6]}: стоп перенесен в точку безубыточности цена: {new_stop.price}, volume={new_stop.volume}")
        return new_stop



    def __repr__(self):
        return f"<Position id={self.id[:6]} sym={self.symbol} dir={self.direction.value} status={self.status.value} opened={self.opened_volume} closed={self.closed_volume} avg_entry={self.avg_entry_price} pnl={self.realized_pnl}>"


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
    def open_position(self, symbol: str, direction: Direction, tick_size: Optional[Decimal] = None, open_bar: Optional[datetime] = None) -> Position:
        pos = Position(symbol=symbol, direction=direction, tick_size=tick_size)
        self.positions[pos.id] = pos
        self.positions[pos.id].bar_opened = open_bar
        logger.debug(f"[{symbol}] 📚 Создана новая позиция  {direction.value} id: {pos.id} ")
        return pos

    # ------------------------
    # закрытие по ID
    # ------------------------
    def cansel_active_orders(self, position_id: str, close_bar: Optional[datetime] = None):
        pos = self.positions.get(position_id)
        if not pos:
            return
        # cancel active orders
        for o in pos.get_active_orders():
            o.status = OrderStatus.CANCELLED
        
        logger.debug(f"📚По позиции {position_id[:6]} Все активные ордера отменены на баре {pos.bar_closed}")

    # ------------------------
    # Закрытие позиции по текущей цене
    # ------------------------
    def close_position_at_market(self, position_id: str, current_price: Decimal, close_bar: Optional[datetime] = None):
        """
        Закрыть позицию полностью по текущей рыночной цене.
        Устанавливает статус CANCELLED для всех активных ордеров.
        """
        pos = self.positions.get(position_id)
        if not pos:
            logger.warning(f"Позиция {position_id} не найдена")
            return
        
        remaining_vol = pos.remaining_volume()
        if remaining_vol > 0:
            # Создаем закрывающий маркет ордер для закрытия всей позиции
            market_order = Order(
                id=uuid4().hex,
                order_type=OrderType.CLOSE,
                price=current_price,
                volume=remaining_vol,
                direction=pos.direction,
                status=OrderStatus.ACTIVE
            )
            pos.add_order(market_order)
            logger.info(f"Создан ордер на закрытие по текущей рыночной цене: {current_price}")
        

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
def make_order(order_type: OrderType, price: Optional[Decimal], volume: Decimal, direction: Direction, created_bar: Optional[datetime] = None, meta: Optional[Dict[str, Any]] = None) -> Order:
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
        price=price if price is not None else None,
        volume=volume,
        direction=direction,
        created_bar=created_bar,
        meta=meta or {}
    )