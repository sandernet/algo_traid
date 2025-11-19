"""
Управление рисками.	
Определение размера позиции (Position Sizing). 
Реализация глобальных Stop Loss и Take Profit.
"""

# Логирование
# ====================================================
from src.utils.logger import get_logger
logger = get_logger(__name__)

from src.config.config import config

def get_position_size(price: float, volume: float) -> float:
    if volume <= 0:
        raise ValueError("Volume must be greater than 0")
    if price <= 0:
        raise ValueError("Entry price must be greater than 0")
    
    return volume / price # размер позиции        
    


class RiskManager():
    def __init__(self, symbol: str):
        self.symbol = symbol
        self.leverage=config.get_setting("STRATEGY_SETTINGS", "LEVERAGE")
        self.position_size=config.get_setting("STRATEGY_SETTINGS", "POSITION_SIZE") 
        
        

    def fibo_trade_plan(self, levels, entry_price):
        """
        Расчёт торгового плана по уровням Фибоначчи на основе последнего движения зигзага.

        :param fib_targets: dict — целевые уровни Фибоначчи для тейков (например, {38.2: price1, 50.0: price2, 61.8: price3})
        :param prise_stoploss: float — уровень Фибоначчи для стоп-лосса 
        
        :param entry_price: float — цена входа (например, close текущей свечи)
        :param leverage: int — плечо
        :param position_size: float — общий размер позиции (в контрактах или лотах)
        :return: dict — информация по ордерам (тейки и стоп)
        """
        fib_targets = list(levels.values())[:5]
        stop_level = list(levels.values())[6]  # уровень стоп-лосса на 161.8%
        
        logger.info(f"Формирование торгового плана по уровням Фибоначчи:")
        logger.info(f"  - Цена входа: {entry_price}")
        logger.info(f"  - Плечо: {self.leverage}")    
        logger.info(f"  - Общий размер позиции: {self.position_size}")
        logger.info(f"  - Уровни тейков: {fib_targets}")
        logger.info(f"  - Уровень стоп-лосса: {stop_level}")
        
        # Разбиваем позицию на 5 равных частей
        part_size = self.position_size / len(fib_targets)

        # Формируем торговый план
        take_profits = []
        for lvl, price in levels.items():
            take_profits.append({
                "fib_level": lvl,
                "price": price,
                "size": part_size,
            })

        trade_plan = {
            "entry_price": entry_price,
            "leverage": self.leverage,
            "total_position": self.position_size,
            "take_profits": take_profits,
            "stop_loss": {
                "fib_level": 161.8,
                "price": stop_level,
                "size": self.position_size  # стоп на всю позицию
            }
        }

        return trade_plan
    
    def apply_stop_loss_take_profit(self):
        """
        Применение глобальных Stop Loss и Take Profit.
        """
        pass