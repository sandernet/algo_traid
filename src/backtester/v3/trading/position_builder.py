# создание позиции + ордера

# src/backtester/trading/position_builder.py
from decimal import Decimal
from src.trading_engine.orders.order_factory import make_order
from src.trading_engine.core.enums import OrderType
from src.risk_manager.risk_manager import RiskManager

class PositionBuilder:
    def __init__(self, manager, coin):
        self.manager = manager
        self.coin = coin

    def build(self, signal, bar):
        direction = signal["direction"]
        symbol = self.coin["SYMBOL"] + "/USDT"
        tick_size = Decimal(str(self.coin["MINIMAL_TICK_SIZE"]))

        position = self.manager.open_position(
            symbol=symbol,
            direction=direction,
            tick_size=tick_size,
            open_bar=bar
        )

        entry_price = position.round_to_tick(Decimal(signal["price"]))
        rm = RiskManager(self.coin)
        volume = rm.calculate_position_size(entry_price)

        position.add_order(
            make_order(OrderType.ENTRY, entry_price, volume, direction, bar)
        )

        for tp in signal.get("take_profits", []):
            position.add_order(
                make_order(
                    OrderType.TAKE_PROFIT,
                    position.round_to_tick(Decimal(tp["price"])),
                    position.round_to_tick(volume * Decimal(tp["volume"])),
                    direction,
                    bar
                )
            )

        for sl in signal.get("sl", []):
            position.add_order(
                make_order(
                    OrderType.STOP_LOSS,
                    position.round_to_tick(Decimal(sl["price"])),
                    position.round_to_tick(volume * Decimal(sl["volume"])),
                    direction,
                    bar
                )
            )

        return position
