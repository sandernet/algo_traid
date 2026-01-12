from src.backtester.trading.signal_handler import SignalHandler
from src.trading_engine.core.signal import Signal
from src.trading_engine.core.enums import Direction, SignalType
from decimal import Decimal

from hypothesis import given, strategies as st  # ← Добавьте это

try:
    from src.tests.mocks.mock_position import MockPosition
except ImportError:
    from tests.mocks.mock_position import MockPosition

# Определите стратегии перед использованием
positions_strategy = st.builds(MockPosition)  # или ваша кастомная стратегия
exit_signal_strategy = st.builds(Signal)  # или ваша кастомная стратегия

def test_exit_closes_positions(positions, signal, mock_builder, mock_manager, mock_logger):
    # positions и signal должны быть в параметрах
    handler = SignalHandler(mock_manager, mock_builder, mock_logger)

    # Создаем тестовую позицию
    pos = MockPosition(
        direction=Direction.LONG,
        source="STRATEGY",
        is_hedge=False,
        price=Decimal("100")  # или Decimal("100")
    )
    
    # Создаем словарь позиций
    positions = {pos.id: pos}

    # Создаем EXIT сигнал
    signal = Signal(
        signal_type=SignalType.EXIT,
        source="STRATEGY"
    )

    bar = [0, 0, 0, 100]

    result = handler.handle(signal, positions, bar)

    assert len(result) == 0  # В словаре не должно остаться позиций
    assert pos.id not in result