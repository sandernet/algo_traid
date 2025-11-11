from enum import Enum
from decimal import Decimal

from typing import List, Optional

# Статусы позиции
class PositionStatus(Enum):
    ACTIVE = "active" # активная позиция
    TAKEN = "taken" # позиция закрыта в прибыль
    STOPPED = "stopped" # позиция закрыта в убыток
    CANCELLED = "cancelled" # позиция отменена
    NONE = "none" # позиция не инициализирована
    CREATED = "created" # позиция создана
    
# Статусы Take Profit
class TakeProfit_Status(Enum):
    ACTIVE = "active"
    PENDING = "pending"
    CANCELED = "canceled"
    
class Direction(Enum):
    LONG = "long"
    SHORT = "short"


class TakeProfitLevel:
    def __init__(self, price: Decimal, volume: float, tick_size: float):
        self.price = round_to_step(price, tick_size) # цена Take Profit
        self.volume = volume  # доля от общей позиции (например, 0.2 = 20%)
        self.TakeProfit_Status = TakeProfit_Status.ACTIVE  # статус
        self.bar_executed = None  # индекс бара, в котором был выполнен Take Profit
        self.profit = None
        
    def __repr__(self):
        return f"TakeProfitLevel(price={self.price}, volume={self.volume}, status={self.TakeProfit_Status.value}) \n"
        
class StopLoss:
    def __init__(self, price: float, volume: float, tick_size: float ):
        self.price = round_to_step(price, tick_size)  # цена cтоп-лосс
        self.volume = volume  # объем (например, 0.2 = 20%) 
        self.status = TakeProfit_Status.ACTIVE  # статус
        self.bar_executed = None  # индекс бара, в котором срабатывает стоп-лосс
        
    def __repr__(self):
        return f"StopLoss(price={self.price}, volume={self.volume}, status={self.status.value})"


class Position:
    
    
    def __init__(self):
        self.status = PositionStatus.NONE  # позицыя не создана
        
        
    def setPosition(self, symbol, direction, entry_price: float, bar_index, tick_size):
        self.symbol = symbol # название монеты
        self.direction = direction # направление позиции long, short
        self.entry_price = round_to_step(entry_price, tick_size) # entry_price  # цена входа
        
        self.status = PositionStatus.CREATED  # статус позиции
        
        self.take_profits: List[TakeProfitLevel] = []  # список Take Profit
        self.stop_loss: Optional[StopLoss] = None  # один стоп-лосс

        self.bar_opened = bar_index  # индекс бара, в котором была открыта позиция
        self.bar_closed = None  # индекс бара, в котором была закрыта позиция
        self.profit = None

    
    # устанавливает размер позиции
    def setVolume_size(self, volume: float):
        if volume <= 0:
            raise ValueError("Volume must be greater than 0")
        self.volume_size = volume # размер позиции        
    
    
    def is_empty(self) -> bool:
        """Проверяет, является ли позиция пустой (не инициализированной)"""
        return not hasattr(self, 'symbol') or self.symbol is None
    
    def set_take_profits(self, take_profits: List[TakeProfitLevel]):
        """Устанавливает все Take Profit уровни разом."""
        self.take_profits = take_profits

    def set_stop_loss(self, stop_loss: StopLoss):
        """Устанавливает один Stop Loss."""
        self.stop_loss = stop_loss

    def add_stop_loss(self, sl: StopLoss):
        """Добавляет стоп-лосс (заменяет предыдущий)."""
        self.stop_loss = sl
        
    def __repr__(self):
        return (f"Position(symbol={self.symbol}, entry_price={self.entry_price}, direction={self.direction.value}, \n"
                f"status={self.status.value} \n"
                f"volume_size={self.volume_size} \n"
                f"{self.take_profits}\n" 
                f"{self.stop_loss})")


@staticmethod
def round_to_step(value: float, step: float) -> float:
    return round(value / step) * step