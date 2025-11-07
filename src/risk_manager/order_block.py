from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class TakeProfitLevel:
    price: float
    volume: float          # доля от общей позиции (например, 0.2 = 20%)
    
@dataclass
class TradePosition:
    entry_price: float  # цена входа
    stop_loss: float  # стоп-лосс
    take_profits: List[TakeProfitLevel] 
    direction: str  # 'BUY' или 'SELL'

    
    def __init__(self, entry_price: float, stop_loss: float, take_profits: List[TakeProfitLevel], direction: str):
        self.entry_price = entry_price
        self.stop_loss = stop_loss
        self.take_profits = take_profits
        self.direction = direction
