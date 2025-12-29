from decimal import Decimal
from src.trading_engine.signals.signal import Signal
from src.trading_engine.core.enums import Direction, SignalType, SignalSource


def test_no_signal():
    s = Signal.no_signal()
    assert s.signal_type == SignalType.NO_SIGNAL
    assert s.is_no_signal()


def test_entry_signal():
    s = Signal.entry(
        source=SignalSource.STRATEGY,
        direction=Direction.LONG,
        entry_price=Decimal("100"),
        take_profits=[],
        stop_losses=[],
    )

    assert s.signal_type == SignalType.ENTRY
    assert s.direction == Direction.LONG
    assert s.price == Decimal("100")


def test_hedge_open_signal():
    s = Signal.hedge_open(
        source=SignalSource.ALS,
        direction=Direction.SHORT,
        volume=Decimal("1"),
    )

    assert s.signal_type == SignalType.HEDGE_OPEN
    assert s.direction == Direction.SHORT
    assert s.source == SignalSource.ALS
