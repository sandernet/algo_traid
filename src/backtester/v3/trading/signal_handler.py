# реакция на сигналы
# src/backtester/trading/signal_handler.py
from src.trading_engine.core.enums import Position_Status

# Обработчик сигналов стратегии.
# Отвечает за открытие, закрытие и изменение позиций
# в зависимости от полученных сигналов. Работает совместно
# с PositionBuilder для создания новых позиций.
class SignalHandler:
    def __init__(self, manager, builder, logger):
        self.manager = manager
        self.builder = builder
        self.logger = logger

    def handle(self, signal, position, bar):
        if not signal:
            return position

        if position and position.direction != signal["direction"]:
            self.logger.debug("Противоположный сигнал — закрытие позиции")
            self.manager.cansel_active_orders(position.id, bar)
            self.manager.close_position_at_market(position.id, signal["price"], bar)
            return None

        if position is None:
            self.logger.debug("Открытие новой позиции")
            return self.builder.build(signal, bar)

        return position
