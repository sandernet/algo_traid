from decimal import Decimal, ROUND_HALF_DOWN
# Логирование
# ====================================================
from src.utils.logger import get_logger
logger = get_logger(__name__)

RISK_PROFILES = {
    "conservative": {
        "risk_per_trade": Decimal("0.01"),  # Риск 1% от депозита
        "take_profit_multiplier": Decimal("1.5"),
        "stop_loss_multiplier": Decimal("0.5"),
    },
    "moderate": {
        "risk_per_trade": Decimal("0.02"),  # Риск 2% от депозита
        "take_profit_multiplier": Decimal("2.0"),
        "stop_loss_multiplier": Decimal("1.0"),
    },
    "aggressive": {
        "risk_per_trade": Decimal("0.05"),  # Риск 5% от депозита
        "take_profit_multiplier": Decimal("3.0"),
        "stop_loss_multiplier": Decimal("1.5"),
    },
}

class RiskManager():
    def __init__(self, coin, profile="moderate"):
        self.symbol = coin.get("SYMBOL") + "/USDT"
        self.leverage = Decimal(coin.get("LEVERAGE"))
        self.start_deposit_usdt = Decimal(coin.get("START_DEPOSIT_USDT"))
        self.minimal_qty = Decimal(str(coin.get("MINIMAL_TICK_SIZE")))  # минимальный объём монеты (minQty)
        self.position_size_usdt = Decimal(coin.get("VOLUME_SIZE"))  # фикс. объём в USDT (условный риск)

        if profile not in RISK_PROFILES:
            raise ValueError(f"Invalid risk profile: {profile}")
        self.profile = RISK_PROFILES[profile]

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
        logger.debug(f"[{self.symbol}]🔶 Размер позиции рассчитан RiskManager: {qty}")
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

    def calculate_stop_loss(self, entry_price: Decimal) -> Decimal:
        """
        Расчет стоп-лосса на основе уровня риска и текущей цены входа.
        """
        stop_loss = entry_price * (1 - self.profile["stop_loss_multiplier"] / 100)
        logger.debug(f"[{self.symbol}]🔶 Stop Loss: {stop_loss}")
        return stop_loss

    def calculate_take_profit(self, entry_price: Decimal) -> Decimal:
        """
        Расчет тейк-профита на основе уровня риска и текущей цены входа.
        """
        take_profit = entry_price * (1 + self.profile["take_profit_multiplier"] / 100)
        logger.debug(f"[{self.symbol}]🔶 Take Profit: {take_profit}")
        return take_profit

    def calculate_risk_per_trade(self) -> Decimal:
        """
        Расчет объема риска на сделку в зависимости от депозита.
        """
        risk = self.start_deposit_usdt * self.profile["risk_per_trade"]
        logger.debug(f"[{self.symbol}]🔶 Риск на сделку: {risk}")
        return risk