from src.backtester.trading.signal_handler import SignalHandler
from src.trading_engine.core.signal import Signal
from src.trading_engine.core.enums import Direction, SignalSource
from tests.mocks.mock_position import MockPosition
from decimal import Decimal


def test_hedge_open(
    mock_builder,
    mock_manager,
    mock_logger,
):
    handler = SignalHandler(mock_manager, mock_builder, mock_logger)

    positions = {}

    signal = Signal.hedge_open(
        source=SignalSource.ALS,
        direction=Direction.SHORT,
        volume=Decimal("1"),
    )

    bar = [0, 0, 0, 100]

    positions = handler.handle(signal, positions, bar)

    assert len(positions) == 1
    hedge = list(positions.values())[0]
    assert signal.is_hedge is True


def test_hedge_close(
    mock_builder,
    mock_manager,
    mock_logger,
):
    handler = SignalHandler(mock_manager, mock_builder, mock_logger)

    hedge = MockPosition(direction=Direction.SHORT, source=None, is_hedge=True)
    positions = {hedge.id: hedge}
    

    signal = Signal.exit(source=SignalSource.ALS)

    bar = [0, 0, 0, 100]

    positions = handler.handle(signal, positions, bar)

    assert positions == {}
    assert hedge.id in mock_manager.closed
