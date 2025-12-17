# Логирование
# ====================================================
from src.utils.logger import get_logger
logger = get_logger(__name__)

from src.trading_engine.managers.position_manager import PositionManager


class Signal():
    def __init__(self, direction, price, volume):
        self.direction = direction
        self.price = price
        self.volume = volume
        
class TradingLogic():
    def __init__(self, symbol, coin):
        self.symbol = symbol
        self.coin = coin

    
    def trading_logic(self,pos_manager: PositionManager, signal):
        pass
    
    # ==============================================
    # ? Проверка на открытие позиции, если есть сигнал
    # ==============================================
    def checking_opening_position(self, position, signal, pos_manager, current_index):
        #-------------------------------------------------------------
        # Если нет открытой позиции, и есть сигнал на вход
        #-------------------------------------------------------------
        if position is None and signal != {}:
            # создание новой позиции по сигналу
            logger.debug(f"[{self.symbol}]🔷 Сигнал на вход получен: {signal.get('direction')} по цене {signal.get('price')}")
            position = self.create_position(signal=signal, manager=pos_manager, coin=self.coin, current_index=current_index)
            if position is None:
                logger.error(f"[{self.symbol}]🔴 Позиция не создана")
            else:    
                logger.debug(f"[{self.symbol}]--------------------------------------------------")

