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
    status: str = 'open' # 'open', 'closed', "None"


class OrderBlock(TradePosition):
    def __init__(self):
        pass
                 