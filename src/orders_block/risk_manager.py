"""
Управление рисками.	
Определение размера позиции (Position Sizing). 
Реализация глобальных Stop Loss и Take Profit.
"""
from decimal import Decimal, ROUND_HALF_DOWN
# Логирование
# ====================================================
from src.utils.logger import get_logger
logger = get_logger(__name__)


class RiskManager():
    def __init__(self, coin):
        self.symbol             = coin.get("SYMBOL")+"/USDT"
        self.leverage           = Decimal(coin.get("LEVERAGE"))
        self.start_deposit_usdt = Decimal(coin.get("START_DEPOSIT_USDT"))
        self.minimal_qty        = Decimal(str(coin.get("MINIMAL_TICK_SIZE")))  # минимальный объём монеты (minQty)
        self.position_size_usdt = Decimal(coin.get("VOLUME_SIZE"))  # фикс. объём в USDT (условный риск)
        
        
    # расчет размера позиции
    def calculate_position_size(self, entry_price: Decimal) -> Decimal:
            """
            Расчет количества монет с учетом:
            - фиксированного размера позиции в USDT
            - плеча
            - минимального шага количества (minQty)
            """
            # 1. Объём позиции в монете до округления
            raw_qty = (self.position_size_usdt * self.leverage) / entry_price

            # 2. Приведение к минимальному шагу (minQty)
            qty = self._round_to_min_qty(raw_qty)

            return qty
        
    # округление количества монет до минимального шага (minQty)
    def _round_to_min_qty(self, qty: Decimal) -> Decimal:
        """
        Округление количества монет до минимального шага (minQty)
        всегда вниз, чтобы не превысить лимиты биржи.
        """
        if not self.minimal_qty:
            return qty
        if self.minimal_qty <= 0:
            return qty
        q = (qty / self.minimal_qty).quantize(Decimal('1'), rounding=ROUND_HALF_DOWN)
        return q * self.minimal_qty
    
    # # округление количества монет до минимального шага (minQty)
    # def _round_to_min_qty(self, qty: Decimal) -> Decimal:
    #     """
    #     Округление количества монет до минимального шага (minQty)
    #     всегда вниз, чтобы не превысить лимиты биржи.
    #     """
    #     return (qty // self.minimal_qty) * self.minimal_qty
    