# реакция на сигналы
# src/backtester/trading/signal_handler.py
# from src.trading_engine.core.enums import Position_Status
from src.trading_engine.core.signal import Signal
from src.trading_engine.core.enums import SignalType
from src.trading_engine.core.position import Position
from typing import Dict

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
    # TODO: добавить передачу всех позиции в обработчик сигнала
    
    def handle(self, signal: Signal, positions: Dict[str, Position], bar) -> Dict[str, Position]:
        # !--- 1. NO SIGNAL ---
        if signal.is_no_signal():
            self.logger.debug(f"Обработка сигнала: {signal.signal_type}, Позиции: {list(positions.keys())}")
            return positions
        
        # self.logger.debug(f"Обработка сигнала: {signal.signal_type}, Позиции: {list(positions.keys())}")
        # !--- 2. ENTRY ---
        if signal.signal_type == SignalType.ENTRY:
            return self._handle_entry(signal, positions, bar)

        # !--- 3. EXIT ---
        if signal.signal_type == SignalType.EXIT:
            return self._handle_exit(signal, positions, bar)

        # !--- 4. HEDGE OPEN ---
        if signal.signal_type == SignalType.HEDGE_OPEN:
            return self._handle_hedge_open(signal, positions, bar)

        # !--- 5. HEDGE CLOSE ---
        if signal.signal_type == SignalType.HEDGE_CLOSE:
            return self._handle_hedge_close(signal, positions, bar)

        self.logger.warning(f"Неизвестный тип сигнала: {signal.signal_type}")
        return positions

    # ============================
    # ? ENTRY — открытие основной позиции
    # ==================================================
    def _handle_entry(self, signal: Signal, positions: Dict[str, Position], bar):

        self.logger.info("ENTRY: открытие новой позиции")

        position = self.builder.build(signal, bar)

        if position:
            positions[position.id] = position

        return positions

    # ==================================================
    # ? EXIT — закрытие всех позиций источника
    # ==================================================
    def _handle_exit(self, signal: Signal, positions: Dict[str, Position], bar):
        self.logger.info("EXIT: закрытие позиций")
        for pos_id, pos in list[tuple[str, Position]](positions.items()):
            if signal.source and pos.source != signal.source:
                continue
            # ! Отмена активных ордеров и закрытие позиции по рынку
            self.manager.cancel_active_orders(pos.id, bar)
            self.manager.close_position_at_market(
                pos.id,
                pos.last_price,
                bar,
            )
            del positions[pos_id]
        return positions
    
    # ==================================================
    # ?HEDGE OPEN — открытие хедж позиции
    # ==================================================
    def _handle_hedge_open(self, signal: Signal, positions: Dict[str, Position], bar):

        self.logger.info("HEDGE_OPEN: открытие хедж позиции")

        if signal.direction is None or signal.price is None:
            self.logger.error("HEDGE_OPEN пропущен — отсутствует направление или цена")
            return positions
        
        hedge_signal = Signal.entry(
            
            direction=signal.direction,
            entry_price=signal.price,
            take_profits=[],
            stop_losses=[],
            source=signal.source,
            metadata={**signal.metadata, "is_hedge": True},
        )

        position = self.builder.build(hedge_signal, bar)

        if position:
            position.is_hedge = True
            positions[position.id] = position

        return positions
    
    # ==================================================
    # ? HEDGE CLOSE — закрытие всех хедж позиций
    # ==================================================
    def _handle_hedge_close(self, signal: Signal, positions: Dict[str, Position], bar):

        self.logger.info("HEDGE_CLOSE " + signal.source + " закрытие всех хедж позиций")

        for pos_id, pos in list[tuple[str, Position]](positions.items()):
            if signal.source and pos.source != signal.source:
                continue
            if pos.is_hedge:
                self.manager.cancel_active_orders(pos.id, bar)
                self.manager.close_position_at_market(
                    pos.id,
                    pos.last_price,
                    bar,
                )   
                del positions[pos_id]

        return positions
