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

# Статусы stop_loss
class StopLoss_Status(Enum):
    ACTIVE = "active"
    EXECUTED = "executed"
    CANCELED = "canceled"
    NO_LOSS = "no_loss" # Без убытка, при закрытии первого take_profit
    
class Direction(Enum):
    LONG = "long"
    SHORT = "short"


class TakeProfitLevel:
    def __init__(self, price: float, volume: float):
        self.price: Decimal = float_to_decimal(price)   # цена Take Profit
        self.volume: Decimal = float_to_decimal(volume)  # доля от общей позиции (например, 0.2 = 20%)
        self.TakeProfit_Status = TakeProfit_Status.ACTIVE  # статус
        self.bar_executed = None  # индекс бара, в котором был выполнен Take Profit
        self.profit = Decimal('0.0')
        
    def __repr__(self):
        return f"TakeProfitLevel(price={self.price}, volume={self.volume}, status={self.TakeProfit_Status.value}) \n"
        
class StopLoss:
    def __init__(self, price: float, volume: float):
        self.price = float_to_decimal(price)  # цена cтоп-лосс
        self.volume = float_to_decimal(volume)  # объем (например, 0.2 = 20%) 
        self.status = StopLoss_Status.ACTIVE  # статус
        self.bar_executed = None  # индекс бара, в котором срабатывает стоп-лосс
        self.profit = Decimal('0.0')
        
    def __repr__(self):
        return f"StopLoss(price={self.price}, volume={self.volume}, status={self.status.value}, bar_executed={self.bar_executed}, profit={self.profit})"


class Position:
    def __init__(self, tick_size: float):
        self.status = PositionStatus.NONE  # позиция не создана
        self.tick_size = float_to_decimal(tick_size)  # размер tick_size
        
        
    def setPosition(self, symbol, direction, entry_price: float, bar_index):
        self.symbol: str = symbol # название монеты
        self.direction = direction # направление позиции long, short
        self.entry_price: Decimal = float_to_decimal(entry_price) # entry_price  # цена входа
        
        self.status = PositionStatus.CREATED  # статус позиции
        
        self.take_profits: List[TakeProfitLevel] = []  # список Take Profit
        self.stop_loss: Optional[StopLoss]  # один стоп-лосс

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
        """
        функция по переводу стоп-лосс в без убыток
        """
        if self.stop_loss:
            self.stop_loss.status = StopLoss_Status.NO_LOSS
            
            
    # Проверяет, сработал ли Take Profit если закрыты все Take Profit возвращает True
    def check_take_profit(self, current_bar) -> bool:
        high_price = float_to_decimal(current_bar["high"])
        low_price = float_to_decimal(current_bar["low"])
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
            self.stop_loss_not_loss() # переводим стоп-лосс в без убыток
            
                        
        # Проверяем последний Take Profit исполнен
        if self.take_profits and self.take_profits[-1].TakeProfit_Status == TakeProfit_Status.EXECUTED:
            # меняем статус
            self.status = PositionStatus.TAKEN_FULL
            # устанавливаем индекс бара в котором был сработан stop_loss
            self.bar_closed = current_bar.name
            if self.stop_loss:
                self.stop_loss.status = StopLoss_Status.CANCELED
            full_closed = True  
        return full_closed
    
    # Проверяет, сработал ли Stop Loss
    # если закрыт стоп-лосс возвращает True
    def check_stop_loss(self, current_bar) -> bool:
        # если статус stop_loss Активный
        if self.stop_loss and self.stop_loss.bar_executed is None and self.stop_loss.status == StopLoss_Status.ACTIVE:
            # проверяем с текущим баром
            if (self.direction == Direction.LONG and current_bar["low"] <= self.stop_loss.price) or (self.direction == Direction.SHORT and current_bar["high"] >= self.stop_loss.price):
                # меняем статус
                self.stop_loss.status = StopLoss_Status.EXECUTED
                self.status = PositionStatus.STOPPED
                # устанавливаем индекс бара в котором был сработан stop_loss
                self.stop_loss.bar_executed = current_bar.name
                self.bar_closed = current_bar.name
                return True
        # если статус stop_loss Без убыток
        if self.stop_loss and self.stop_loss.bar_executed is None and self.stop_loss.status == StopLoss_Status.NO_LOSS:
            if (self.direction == Direction.LONG and current_bar["low"] <= self.entry_price) or (self.direction == Direction.SHORT and current_bar["high"] >= self.entry_price):
                # меняем статус
               
                # устанавливаем индекс бара в котором был сработан stop_loss
                self.stop_loss.bar_executed = current_bar.name
                self.bar_closed = current_bar.name
                return True
        return False
    
    # Останавливает позицию
    # если у позиции остался обьем не закрытый закрываем его по текущей цене (в бэктесте берем открытие текущей свечи)
    def close_orders(self, current_bar):
        
        status = PositionStatus.CANCELLED
        # если стоп-лосс не исполнен
        if self.stop_loss and self.stop_loss.bar_executed is None:
            status = PositionStatus.CANCELLED
            self.stop_loss.status = StopLoss_Status.CANCELED
            self.stop_loss.bar_executed = current_bar.name
            self.stop_loss.price = current_bar["open"]

        
        if self.status == PositionStatus.TAKEN_PART:
            status = PositionStatus.TAKEN_PART
            for tp in self.take_profits:
                if tp.TakeProfit_Status == TakeProfit_Status.ACTIVE:
                    tp.TakeProfit_Status = TakeProfit_Status.CANCELED
                    tp.bar_executed = current_bar.name
        
        if self.status == PositionStatus.TAKEN_FULL:
            status = PositionStatus.TAKEN_FULL


        self.bar_closed = current_bar.name
        self.status = status
        
    # Расчет прибыли позиции по всем тейк-профитам или стоп-лосс
    def Calculate_profit(self):
        """
        Рассчитывает общую прибыль/убыток по позиции
        исходя из сработавших Take Profit и Stop Loss с использованием Decimal.
        """
        # Инициализируем переменные для расчетов в Decimal
        total_profit_decimal = Decimal('0.0')
        total_closed_volume = Decimal('0.0')
        
        # Проверяем, установлен ли размер позиции
        if not hasattr(self, 'volume_size'):
            # Возможно, нужно вернуть 0.0 или вызвать ошибку, если позиция не имеет объема
            return 0.0

        # 1. Расчет прибыли по сработавшим Take Profit
        for tp in self.take_profits:
            if tp.bar_executed is not None and tp.TakeProfit_Status == TakeProfit_Status.EXECUTED:
                # Объем закрытия для данного TP (Decimal)
                # tp.volume - это доля (float), приводим к Decimal
                closed_volume_tp = self.volume_size * tp.volume
                # closed_volume = self.volume_size * float(tp.volume)
                
                if self.direction == Direction.LONG:
                    # Разница цены (Decimal)
                    price_diff = tp.price - self.entry_price
                else:  # Direction.SHORT
                    # Разница цены (Decimal)
                    price_diff = self.entry_price - tp.price
                    
                # Прибыль/убыток по данному TP (Decimal)
                profit_decimal = price_diff * closed_volume_tp
                
                # Сохраняем результат в атрибутах класса
                tp.profit = profit_decimal
                total_profit_decimal += profit_decimal
                total_closed_volume += closed_volume_tp
         
        
        # 2. Расчет прибыли/убытка по сработавшему Stop Loss
        if self.stop_loss and self.stop_loss.bar_executed is not None:
            # Оставшийся объем, закрытый по SL (Decimal)
            total_volume = self.volume_size
            remaining_volume = total_volume - total_closed_volume
            
            stop_loss_price = self.stop_loss.price
            
            if remaining_volume > Decimal('0.0'):
                price_diff = abs(stop_loss_price - self.entry_price)
                
                if self.direction == Direction.LONG:
                    if stop_loss_price < self.entry_price:
                        price_diff = price_diff * -1 #отрицательный убыток 
                else:  # Direction.SHORT
                    # Разница цены (Decimal)
                    if stop_loss_price > self.entry_price:
                        price_diff = price_diff * -1 #отрицательный убыток 
                    
                # Прибыль/убыток по SL (Decimal)
                loss_decimal = price_diff * remaining_volume
                
                self.stop_loss.profit = loss_decimal
                self.stop_loss.volume = remaining_volume # закрываем оставшийся объем
                total_profit_decimal += loss_decimal
        
        # # 3. Обновление итоговой прибыли позиции
        # if self.volume_size == remaining_volume:
        self.profit = total_profit_decimal
        return self.profit
        
    def __repr__(self):
        return (f"Position(symbol={self.symbol}, entry_price={self.entry_price}, direction={self.direction.value}, \n"
                f"status={self.status.value} \n"
                f"volume_size={self.volume_size} \n"
                f"{self.take_profits}\n" 
                f"{self.stop_loss})")


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
    
def float_to_decimal(f: float) -> Decimal:
    return Decimal(str(f))