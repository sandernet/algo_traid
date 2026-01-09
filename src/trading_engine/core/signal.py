from datetime import datetime, UTC
from typing import List, Optional, Dict, Any
from decimal import Decimal
from src.trading_engine.core.enums import SignalType, SignalSource, Direction



class Signal:
    """
    Универсальный торговый сигнал.
    Используется стратегиями, ALS и другими модулями.
    """

    def __init__(
        self,
        *,
        signal_type: SignalType,
        direction: Optional[Direction] = None,
        price: Optional[Decimal] = None,
        volume: Optional[Decimal] = None,
        take_profits: Optional[List[Dict[str, Any]]] = None,
        stop_losses: Optional[List[Dict[str, Any]]] = None,
        bar_index=None,
        source: str,
        metadata: Optional[Dict[str, Any]] = None,
        timestamp: Optional[datetime] = None,
    ):
        self.signal_type = signal_type
        self.direction = direction
        self.price = price
        self.volume = volume

        self.take_profits = take_profits or []
        self.stop_losses = stop_losses or []
        self.bar_index = bar_index
        self.source = source
        self.metadata = metadata or {}
        self.timestamp = timestamp or datetime.now(UTC)

    # ==========================
    # Factory methods (очень важно!)
    # ==========================

    # Возврат объекта сигнала без сигнала
    @classmethod
    def no_signal(cls, source: str, bar_index=None ):
        """
        Пустой сигнал — стратегия ничего не делает
        """
        return cls(
            signal_type=SignalType.NO_SIGNAL,
            source=source,
            bar_index=bar_index,
        )

    # Создание объекта сигнала на вход в позицию
    @classmethod
    def entry(
        cls,
        *,
        
        direction: Direction,
        entry_price: Decimal,
        take_profits: list,
        stop_losses: list,
        source: str,
        metadata: dict = {},
    ):
        return cls(
            signal_type=SignalType.ENTRY,
            direction=direction,
            price=entry_price,
            take_profits=take_profits,
            stop_losses=stop_losses,
            source=source,
            metadata=metadata,
        )

    @classmethod
    def hedge_open(
        cls,
        *,
        direction: Direction,
        volume: Decimal,
        source: str,
        metadata: dict = {},
    ):
        return cls(
            signal_type=SignalType.HEDGE_OPEN,
            direction=direction,
            volume=volume,
            source=source,
            metadata=metadata,
        )

    @classmethod
    def exit(
        cls,
        *,
        source: str,
        metadata: dict = {},
    ):
        return cls(
            signal_type=SignalType.EXIT,
            source=source,
            metadata=metadata,
        )

    # ==========================
    # Utility
    # ==========================
    def is_no_signal(self) -> bool:
        return self.signal_type == SignalType.NO_SIGNAL

    def is_entry(self) -> bool:
        return self.signal_type == SignalType.ENTRY

    def is_hedge(self) -> bool:
        return self.signal_type in {
            SignalType.HEDGE_OPEN,
            SignalType.HEDGE_CLOSE,
        }

    def to_dict(self) -> dict:
        return {
            "type": self.signal_type.value,
            "direction": self.direction,
            "price": str(self.price) if self.price else None,
            "volume": str(self.volume) if self.volume else None,
            "take_profits": self.take_profits,
            "stop_losses": self.stop_losses,
            "source": self.source,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat(),
        }

    def __repr__(self):
        return f"<Signal {self.signal_type.value} {self.direction} src={self.source.value}>"
