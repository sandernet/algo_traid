from enum import Enum
from decimal import Decimal, ROUND_HALF_UP

from typing import List, Optional

# Статусы позиции
class Position_Status(Enum):
    ACTIVE = "active" # активная позиция
    TAKEN_PART = "part_taken" # позиция закрыта частично
    TAKEN_FULL = "taken_full" # позиция закрыта в прибыль
    STOPPED = "stopped" # позиция закрыта в убыток
    CANCELLED = "cancelled" # позиция отменена
    NONE = "none" # позиция не инициализирована
    CREATED = "created" # позиция создана
    
# Статусы Take Profit
class TakeProfit_Status(Enum):
    ACTIVE = "active"
    EXECUTED = "executed"
    CANCELED = "canceled"

# Статусы stop_loss
class StopLoss_Status(Enum):
    ACTIVE = "active"
    EXECUTED = "executed"
    CANCELED = "canceled"
    NO_LOSS = "no_loss" # Без убытка, при закрытии первого take_profit
    
class Direction(Enum):
    LONG = "long"
    SHORT = "short"


# Take Profit 
class TakeProfit:
    def __init__(self, price: float, volume: float):
        self.price: Decimal = float_to_decimal(price)   # цена Take Profit
        self.volume: Decimal = float_to_decimal(volume)  # доля от общей позиции (например, 0.2 = 20%)
        self.Status = TakeProfit_Status.ACTIVE  # статус
        self.bar_executed = None  # индекс бара, в котором был выполнен Take Profit
        self.profit = Decimal('0.0')
        
    def __repr__(self):
        return f"TakeProfitLevel(price={self.price}, volume={self.volume}, status={self.Status.value}) \n"
        
class StopLoss:
    def __init__(self, price: float, volume: float):
        self.price = float_to_decimal(price)  # цена cтоп-лосс
        self.volume = float_to_decimal(volume)  # объем (например, 0.2 = 20%) 
        self.closed_volume = Decimal('0.0')
        self.status = StopLoss_Status.ACTIVE  # статус
        self.bar_executed = None  # индекс бара, в котором срабатывает стоп-лосс
        self.profit = Decimal('0.0')
        
    def __repr__(self):
        return f"StopLoss(price={self.price}, volume={self.volume}, status={self.status.value}, bar_executed={self.bar_executed}, profit={self.profit})"


class Position:
    def __init__(self, tick_size: float):
        self.status = Position_Status.NONE  # позиция не создана
        self.bar_opened = None  # индекс бара, в котором была открыта позиция
        self.bar_closed = None  # индекс бара, в котором была закрыта позиция
        self.take_profits = []
        self.stop_loss = None   
        self.tick_size = float_to_decimal(tick_size)  # размер tick_size
        
        
    def setPosition(self, symbol, direction, entry_price: float, bar_index):
        self.symbol: str = symbol # название монеты
        self.direction = direction # направление позиции long, short
        self.entry_price: Decimal = float_to_decimal(entry_price) # entry_price  # цена входа
        
        self.status = Position_Status.CREATED  # статус позиции
        
        self.take_profits: List[TakeProfit] = []  # список Take Profit
        self.stop_loss: Optional[StopLoss] = None  # один стоп-лосс

        self.bar_opened = bar_index  # индекс бара, в котором была открыта позиция
        self.bar_closed = None  # индекс бара, в котором была закрыта позиция
        self.profit: Decimal = Decimal('0.0')

    


    # устанавливает размер позиции
    def setVolume_size(self, volume: float):
        if volume <= 0:
            raise ValueError("Volume must be greater than 0")
        self.volume_size = float_to_decimal(volume) # размер позиции        
    
    
    def is_empty(self) -> bool:
        """Проверяет, является ли позиция пустой (не инициализированной)"""
        return not hasattr(self, 'symbol') or self.symbol is None
    
    def set_take_profits(self, take_profits: List[TakeProfit]):
        """Устанавливает все Take Profit уровни разом."""
        self.take_profits = take_profits

    def set_stop_loss(self, stop_loss: StopLoss):
        """Устанавливает один Stop Loss."""
        self.stop_loss = stop_loss

    def add_stop_loss(self, sl: StopLoss):
        """Добавляет стоп-лосс (заменяет предыдущий)."""
        self.stop_loss = sl
        
    # Переводим стоп-лосс в без убыток     
    def stop_loss_not_loss(self):
        """
        функция по переводу стоп-лосс в без убыток
        """
        if self.stop_loss:
            self.stop_loss.status = StopLoss_Status.NO_LOSS
            

    def round_to_step(self, value: float) -> Decimal:
        """
        Округляет значение до ближайшего кратного tick_size с использованием точной арифметики Decimal.
        Возвращает Decimal.
        """
        if self.tick_size <= 0:
            raise ValueError("tick_size must be > 0")
        if value < 0:
            raise ValueError("value must be non-negative")  # опционально, если поддерживаете только >=0
        value_decimal = float_to_decimal(value)
        tick_size = self.tick_size
        # Округляем (value / tick_size) до целого числа с явным указанием режима округления
        multiplier = (value_decimal / tick_size).quantize(Decimal('1'), rounding=ROUND_HALF_UP)
        return multiplier * tick_size
    
    def __repr__(self) -> str:
        return f"Position(symbol={self.symbol}, \n" + \
            f"direction={self.direction}, \n" + \
                f"volume volume={self.volume_size}, entry_price={self.entry_price}, take_profits={self.take_profits}, stop_loss={self.stop_loss})"
    
def float_to_decimal(f: float) -> Decimal:
    return Decimal(str(f))