from src.backtester.trading.signal_handler import SignalHandler
from src.trading_engine.core.signal import Signal
from src.trading_engine.core.enums import SignalSource
try:
    from src.tests.mocks.mock_position import MockPosition
except ImportError:
    from tests.mocks.mock_position import MockPosition
from hypothesis import given

@given(
    positions=positions_strategy,
    signal=exit_signal_strategy,
)

def test_exit_closes_positions(
    mock_builder,
    mock_manager,
    mock_logger,
):
    handler = SignalHandler(mock_manager, mock_builder, mock_logger)

    pos = MockPosition(direction=1, source=SignalSource.STRATEGY)
    positions = {pos.id: pos}

    signal = Signal.exit(source=SignalSource.STRATEGY)

    bar = [0, 0, 0, 100]

    result = handler.handle(signal, positions, bar)

    assert result == {}
    assert pos.id in mock_manager.closed
