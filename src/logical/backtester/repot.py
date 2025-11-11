from decimal import Decimal
from typing import List, Optional

class TradeReport:
    def __init__(self, position: 'Position'):
        if position.status in (PositionStatus.NONE, PositionStatus.CREATED, PositionStatus.ACTIVE):
            raise ValueError("TradeReport can only be generated for closed positions.")
        
        self.symbol = position.symbol
        self.direction = position.direction
        self.entry_price = position.entry_price
        self.exit_price = self._calculate_exit_price(position)
        self.volume = position.volume_size
        self.status = position.status
        self.bar_opened = position.bar_opened
        self.bar_closed = position.bar_closed
        self.profit = position.profit  # предполагается, что уже рассчитано в Position
        self.take_profits_executed = self._extract_executed_tps(position.take_profits)
        self.stop_loss_executed = self._was_stop_loss_executed(position.stop_loss)

    def _calculate_exit_price(self, position: 'Position') -> Optional[Decimal]:
        """Вычисляет средневзвешенную цену выхода по сработавшим TP/SL."""
        total_volume = Decimal('0')
        weighted_price = Decimal('0')

        for tp in position.take_profits:
            if tp.TakeProfit_Status != TakeProfit_Status.ACTIVE and tp.bar_executed is not None:
                vol = Decimal(str(tp.volume))
                total_volume += vol
                weighted_price += Decimal(str(tp.price)) * vol

        if position.stop_loss and position.stop_loss.status != TakeProfit_Status.ACTIVE and position.stop_loss.bar_executed is not None:
            vol = Decimal(str(position.stop_loss.volume))
            total_volume += vol
            weighted_price += Decimal(str(position.stop_loss.price)) * vol

        if total_volume == 0:
            return None
        return weighted_price / total_volume

    def _extract_executed_tps(self, tps: List['TakeProfitLevel']) -> List[dict]:
        executed = []
        for tp in tps:
            if tp.bar_executed is not None:
                executed.append({
                    'price': tp.price,
                    'volume': tp.volume,
                    'bar_index': tp.bar_executed,
                    'profit': tp.profit
                })
        return executed

    def _was_stop_loss_executed(self, sl: Optional['StopLoss']) -> Optional[dict]:
        if sl and sl.bar_executed is not None:
            return {
                'price': sl.price,
                'volume': sl.volume,
                'bar_index': sl.bar_executed
            }
        return None

    def to_dict(self) -> dict:
        return {
            'symbol': self.symbol,
            'direction': self.direction.value,
            'entry_price': float(self.entry_price),
            'exit_price': float(self.exit_price) if self.exit_price else None,
            'volume': self.volume,
            'status': self.status.value,
            'profit': float(self.profit) if self.profit is not None else None,
            'bar_opened': self.bar_opened,
            'bar_closed': self.bar_closed,
            'take_profits_executed': self.take_profits_executed,
            'stop_loss_executed': self.stop_loss_executed
        }

    def __repr__(self):
        return (f"TradeReport(symbol={self.symbol}, direction={self.direction.value}, "
                f"entry={self.entry_price}, exit={self.exit_price}, profit={self.profit}, "
                f"status={self.status.value})")