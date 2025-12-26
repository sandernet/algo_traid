# реакция на сигналы
# src/backtester/trading/signal_handler.py
# from src.trading_engine.core.enums import Position_Status
from src.trading_engine.signals.signal import Signal
from typing import Optional

# Обработчик сигналов стратегии.
# Отвечает за открытие, закрытие и изменение позиций
# в зависимости от полученных сигналов. Работает совместно
# с PositionBuilder для создания новых позиций.
class SignalHandler:
    def __init__(self, manager, builder, logger):
        self.manager = manager
        self.builder = builder
        self.logger = logger

    # ==================================================
    # ? Обработка сигнала и получение/обновление позиции
    # ==================================================
    def handle(self, signal: Optional[Signal], position, bar):
        # ! Поиск сигнала запуск стратегии
        if not signal:
            return position

        # ! Обработка сигнала и получение/обновление позиции
        # ! Если поступил сигнал на противоположное направление — закрываем позицию
        if position and position.direction != signal.direction:
            self.manager.cancel_active_orders(position.id, bar)
            self.manager.close_position_at_market(position.id, signal.price, bar)
            self.logger.debug("Противоположный сигнал — закрытие позиции")
            return None
        
        # ! Если нет открытой позиции — открываем новую
        if position is None:
            self.logger.debug("Открытие новой позиции")
            return self.builder.build(signal, bar)

        # ! Если поступил сигнал в том же направлении — обновляем позицию
        if position.direction == signal.direction:
            self.logger.debug("Обновление позиции")
            # Обновление логики позиции можно реализовать здесь
            # Например, добавление новых ордеров или изменение стопов
            # В данном примере просто возвращаем существующую позицию

        return position
