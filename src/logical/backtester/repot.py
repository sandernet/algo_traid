import json
from typing import List
from decimal import Decimal
from enum import Enum
import pandas as pd

# ====================================================
from src.utils.logger import get_logger
logger = get_logger(__name__)

from src.risk_manager.trade_position import Position, PositionStatus, TakeProfitLevel, Direction

class TradeReport:
    def __init__(self, position: 'Position'):
        if position.status in (PositionStatus.NONE, PositionStatus.CREATED, PositionStatus.ACTIVE):
            logger.error("Статус позиции не в завершенном состоянии")
            raise ValueError("TradeReport can only be generated for closed positions.")
        
        self.symbol = position.symbol
        # self.direction = position.direction
        # 🔹 Безопасно преобразуем Enum в строку
        self.direction = (
            position.direction.value if isinstance(position.direction, Direction) else str(position.direction)
        )
        self.entry_price = position.entry_price
        self.volume = position.volume_size
        # self.status = position.status
        self.status = (
            position.status.value if isinstance(position.status, PositionStatus) else str(position.status)
        )
        self.bar_opened = position.bar_opened
        self.bar_closed = position.bar_closed
        self.profit = float(position.profit) if isinstance(position.profit, (Decimal, float, int)) else 0.0  # предполагается, что уже рассчитано в Position
        self.take_profits = self._take_profits_report(position.take_profits)
        
        # # Добавим стоп-лосс если есть
        # self.stop_loss = (
        #     {
        #         "price": Decimal(position.stop_loss.price),
        #         "volume": float(position.stop_loss.volume),
        #         "status": position.stop_loss.status.value,
        #         "bar_executed": position.stop_loss.bar_executed
        #     }
        #     if getattr(position, "stop_loss", None)
        #     else None
        # )
        
    def _take_profits_report(self, take_profits: List[TakeProfitLevel]) -> list[dict]:
        """
        Формирует структуру отчёта по уровням Take Profit.
        """
        take_profits_report = []

        for i, take in enumerate(take_profits, start=1):
            report_item = {
                "id": i,
                "price": take.price,
                "volume": take.volume,
                "status": take.TakeProfit_Status.value,
                "bar_executed": take.bar_executed,
                "profit": float(take.profit) if take.profit is not None else 0.0
            }
            take_profits_report.append(report_item)

        return take_profits_report
    
    def to_dict(self) -> dict:
        """Преобразует отчёт в словарь (удобно для сериализации)."""
        return {
            "symbol": self.symbol,
            "direction": self.direction,
            "entry_price": self.entry_price,
            "volume": self.volume,
            "status": self.status,
            "bar_opened": self.bar_opened,
            "bar_closed": self.bar_closed,
            "profit": self.profit,
            "take_profits": self.take_profits
        }

    def to_json(self, indent: int = 4) -> str:
        """Возвращает JSON-представление отчёта, обрабатывая все нестандартные типы."""
        
        def default_serializer(obj):
            if isinstance(obj, (Decimal, float, int, str)):
                return obj
            elif isinstance(obj, Enum):
                return obj.value
            elif isinstance(obj, pd.Timestamp):
                return obj.isoformat()  # '2025-11-11T12:30:00'
            elif obj is None:
                return None
            else:
                return str(obj)
        
        return json.dumps(
            self.to_dict(),
            ensure_ascii=False,
            indent=indent,
            default=default_serializer
        )

        