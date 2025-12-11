# report_generator.py
from typing import List, Dict, Any
from src.position_manager.order import Position_Status
from src.backtester.v2.backtester import Test

from src.utils.logger import get_logger
logger = get_logger(__name__)

class ReportGenerator:
    """
    Генератор отчётов на основе списка объектов Position.
    Подготовленные данные предназначены для передачи в Jinja2-шаблон.
    """

    def __init__(self, test: Test):
        self.test = test

    def serialize_meta(self,meta):
        if not isinstance(meta, dict) or not meta:
            return ""
        return " ".join(f"{k}={v}" for k, v in meta.items())
        
    # -----------------------------
    # ПРЕОБРАЗОВАНИЕ ОБЪЕКТОВ
    # -----------------------------
    def serialize_order(self, order: Any) -> Dict[str, Any]:
        """
        Превращает Order в понятный Jinja2 словарь.
        
        """
        return {
            "id": getattr(order, "id", None),
            "order_type": getattr(order.order_type, "name", order.order_type),
            "status": getattr(order.status, "name", order.status),
            "price": getattr(order, "price", None),
            "volume": getattr(order, "volume", None),
            "profit": getattr(order, "profit", None),
            "filled": getattr(order, "filled", None),
            "direction": getattr(order.direction, "name", order.direction),
            "created_bar": getattr(order, "created_bar", None),
            "close_bar": getattr(order, "close_bar", None),
            "meta":  self.serialize_meta(getattr(order, "meta", {})),  # на случай использования оригинального объекта
        }

    def serialize_position(self, pos: Any) -> Dict[str, Any]:
        """
        Превращает Position в словарь.
        """
        # сериализация ордеров (если есть)
        orders = []
        if hasattr(pos, "orders") and pos.orders:
            for o in pos.orders:
                orders.append(self.serialize_order(o))

        return {
            "id": getattr(pos, "id", None),
            "symbol": getattr(pos, "symbol", None),
            "direction": getattr(pos.direction, "name", pos.direction),
            "status": getattr(pos.status, "name", pos.status),
            "opened_volume": getattr(pos, "opened_volume", None),
            "closed_volume": getattr(pos, "closed_volume", None),
            "bar_opened": getattr(pos, "bar_opened", None),
            "bar_closed": getattr(pos, "bar_closed", None),
            "avg_entry_price": getattr(pos, "avg_entry_price", None),
            "profit": getattr(pos, "profit", None),
            "meta": getattr(pos, "meta", None),
            "orders": orders,
        }

    def serialize_all_positions(self) -> List[Dict[str, Any]]:
        """
        Сериализует все позиции.
        """
        return [self.serialize_position(p) for _, p in self.test.positions.items()]


    # -----------------------------
    def serialize_statistics(self, serialized: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Создаёт статистику по всем позициям.
        """
        self.test
        
        try:        
            total_pnl = self.test.total_pnl # общий PnL
            total_loss = self.test.total_loss # общий убыток
            total_win = self.test.total_win # общий прибыль
            wins = self.test.wins # общее количество побед
            losses = self.test.losses # общее количество проигрышей
            count = self.test.count_positions # общее количество позиций
            winrate = self.test.winrate # процент побед

            return {
                "total_positions": count,
                "total_pnl": total_pnl,
                "total_win": total_win,
                "total_loss": total_loss,
                "wins": wins,
                "losses": losses,
                "winrate": winrate,
            }
        except Exception as e:
            logger.error(f"Error building statistics: {e}")
            return {"total_positions": 0, "total_pnl": 0, "wins": 0, "losses": 0, "winrate": 0, "total_win": 0, "total_loss": 0}

    def build_report_data(self) -> List[Dict[str, Any]]:
        """Главный метод, собирающий список сериализованных позиций."""
        # Фильтруем и сериализуем только закрытые позиции для отчета
        closed_positions = [p for p in self.test.positions.values() if p.status != Position_Status.ACTIVE]
        return [self.serialize_position(pos) for pos in closed_positions]
    
    # -----------------------------
    # ОСНОВНАЯ ФОРМА ОТЧЁТА
    # -----------------------------
    def build_report(self) -> Dict[str, Any]:
        """
        Собирает весь отчёт.
        Это итоговый объект для шаблона Jinja2.
        """
        serialized_positions = self.serialize_all_positions()
        stats = self.serialize_statistics(serialized_positions)
        settings = self.test.settings_test
        
        # 1. Подготовка данных OHLCV
        # ohlcv_df = self.data_ohlcv

        # 2. Создание графика
        # chart_html = self.create_candlestick_chart(self.data_ohlcv, serialized_positions)

        return {
            "positions": serialized_positions,
            "stats": stats,
            "settings": settings
        }
