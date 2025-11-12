from enum import Enum
from decimal import Decimal, ROUND_HALF_UP

from typing import List, Optional

# Статусы позиции
class PositionStatus(Enum):
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
    
class Direction(Enum):
    LONG = "long"
    SHORT = "short"


class TakeProfitLevel:
    def __init__(self, price: Decimal, volume: Decimal, tick_size: float):
        self.price = round_to_step(price, Decimal(tick_size)) # цена Take Profit
        self.volume = volume  # доля от общей позиции (например, 0.2 = 20%)
        self.TakeProfit_Status = TakeProfit_Status.ACTIVE  # статус
        self.bar_executed = None  # индекс бара, в котором был выполнен Take Profit
        self.profit = Decimal(0.0)
        
    def __repr__(self):
        return f"TakeProfitLevel(price={self.price}, volume={self.volume}, status={self.TakeProfit_Status.value}) \n"
        
class StopLoss:
    def __init__(self, price: float, volume: float, tick_size: float ):
        self.price = round_to_step(Decimal(price), Decimal(tick_size))  # цена cтоп-лосс
        self.volume = volume  # объем (например, 0.2 = 20%) 
        self.status = TakeProfit_Status.ACTIVE  # статус
        self.bar_executed = None  # индекс бара, в котором срабатывает стоп-лосс
        self.profit = Decimal(0.0)
        
    def __repr__(self):
        return f"StopLoss(price={self.price}, volume={self.volume}, status={self.status.value}, bar_executed={self.bar_executed}, profit={self.profit})"


class Position:
    def __init__(self):
        self.status = PositionStatus.NONE  # позиция не создана
        
        
    def setPosition(self, symbol, direction, entry_price: float, bar_index, tick_size):
        self.symbol = symbol # название монеты
        self.direction = direction # направление позиции long, short
        self.entry_price = round_to_step(Decimal(entry_price), tick_size) # entry_price  # цена входа
        
        self.status = PositionStatus.CREATED  # статус позиции
        
        self.take_profits: List[TakeProfitLevel] = []  # список Take Profit
        self.stop_loss: Optional[StopLoss]  # один стоп-лосс

        self.bar_opened = bar_index  # индекс бара, в котором была открыта позиция
        self.bar_closed = None  # индекс бара, в котором была закрыта позиция
        self.profit = 0.0

    # Расчет прибыли позиции по всем тейк-профитам или стоп-лосс
    def Calculate_profit(self):
        """
        Рассчитывает общую прибыль/убыток по позиции
        исходя из сработавших Take Profit и Stop Loss.
        """
        total_profit = Decimal('0.0')
        total_closed_volume = Decimal('0.0')

        for tp in self.take_profits:
            if tp.TakeProfit_Status == TakeProfit_Status.CANCELED:
                continue
            if tp.bar_executed is not None:
                closed_volume = Decimal(str(tp.volume)) * Decimal(self.volume_size)
                if self.direction == Direction.LONG:
                    profit = Decimal(tp.price - self.entry_price) * closed_volume
                else:  # SHORT
                    profit = Decimal(self.entry_price - tp.price) * closed_volume
                tp.profit = profit
                total_profit += profit
                total_closed_volume += closed_volume
          
                
                # Если сработал стоп-лосс — учитываем его
        if self.stop_loss and self.stop_loss.bar_executed is not None:
            closed_volume = Decimal(self.volume_size) - total_closed_volume
            if closed_volume > 0:
                if self.direction == Direction.LONG:
                    loss = Decimal(self.stop_loss.price - self.entry_price) * closed_volume
                else:
                    loss = Decimal(self.entry_price - self.stop_loss.price) * closed_volume
                total_profit += loss

        self.profit = total_profit
        return total_profit
    
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
        
    # Переводим стоп-лосс в без убыток     
    def stop_loss_not_loss(self):
        if self.stop_loss and self.stop_loss.bar_executed is None and self.stop_loss.status == TakeProfit_Status.ACTIVE:
            self.stop_loss.price = self.entry_price
            
            
    # Проверяет, сработал ли Take Profit если закрыты все Take Profit возвращает True
    def check_take_profit(self, current_bar) -> bool:
        high_price = Decimal(current_bar["high"])
        low_price = Decimal(current_bar["low"])
        full_closed = False
        # Проверяем каждый Take Profit
        for tp in self.take_profits:
            # Если Take Profit ещё не сработал
            if tp.bar_executed is None and tp.TakeProfit_Status == TakeProfit_Status.ACTIVE:
                # Если позиция в long и текущая цена выше Take Profit               
                if (self.direction == Direction.LONG and high_price >= tp.price) or (self.direction == Direction.SHORT and low_price <= tp.price):
                    # меняем статус
                    tp.TakeProfit_Status = TakeProfit_Status.EXECUTED
                    # устанавливаем индекс бара в котором был сработан Take Profit
                    tp.bar_executed = current_bar.name
        
        # Проверяем первый  Take Profit 
        if self.take_profits and self.take_profits[0].TakeProfit_Status == TakeProfit_Status.EXECUTED:
            # меняем статус
            self.status = PositionStatus.TAKEN_PART
            self.stop_loss_not_loss()
            
                        
        # Проверяем последний Take Profit 
        if self.take_profits and self.take_profits[-1].TakeProfit_Status == TakeProfit_Status.EXECUTED:
            # меняем статус
            self.status = PositionStatus.TAKEN_FULL
            # устанавливаем индекс бара в котором был сработан stop_loss
            self.bar_closed = current_bar.name
            full_closed = True  
                # elif self.direction == Direction.SHORT and low_price <= tp.price:
                #     # меняем статус
                #     tp.TakeProfit_Status = TakeProfit_Status.EXECUTED
                #     # устанавливаем индекс бара в котором был сработан Take Profit
                #     tp.bar_executed = current_bar.name
        return full_closed
    
    def check_stop_loss(self, current_bar):
        if self.stop_loss and self.stop_loss.bar_executed is None and self.stop_loss.status == TakeProfit_Status.ACTIVE:
            if (self.direction == Direction.LONG and current_bar["low"] <= self.stop_loss.price) or (self.direction == Direction.SHORT and current_bar["high"] >= self.stop_loss.price):
                # меняем статус
                self.stop_loss.status = TakeProfit_Status.EXECUTED
                self.status = PositionStatus.STOPPED
                # устанавливаем индекс бара в котором был сработан stop_loss
                self.stop_loss.bar_executed = current_bar.name
                self.bar_closed = current_bar.name
                
    
    # Останавливает позицию
    def cancel_orders(self):
        
        status = PositionStatus.CANCELLED
        
        if self.status == PositionStatus.TAKEN_PART:
            status = PositionStatus.TAKEN_PART
            for tp in self.take_profits:
                if tp.TakeProfit_Status == TakeProfit_Status.ACTIVE:
                    tp.TakeProfit_Status = TakeProfit_Status.CANCELED
        if self.stop_loss and self.stop_loss.status == TakeProfit_Status.ACTIVE:
            self.stop_loss.status = TakeProfit_Status.CANCELED
        elif self.stop_loss and self.stop_loss.status == TakeProfit_Status.EXECUTED:
            status = PositionStatus.STOPPED
                
        self.status = status
        
    def __repr__(self):
        return (f"Position(symbol={self.symbol}, entry_price={self.entry_price}, direction={self.direction.value}, \n"
                f"status={self.status.value} \n"
                f"volume_size={self.volume_size} \n"
                f"{self.take_profits}\n" 
                f"{self.stop_loss})")


def round_to_step(value: Decimal, step: Decimal) -> Decimal:
    """
    Округление значения по шагу tick_size с использованием Decimal для точности.
    Возвращает float (как раньше) для совместимости.
    """
    if step <= 0:
        raise ValueError("tick_size must be > 0")
    v = Decimal(str(value))
    s = Decimal(str(step))
    factor = (v / s).to_integral_value(rounding=ROUND_HALF_UP)
    return Decimal(factor * s)