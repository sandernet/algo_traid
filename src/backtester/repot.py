import os
import json
from typing import List, Any
from decimal import Decimal
from enum import Enum
import pandas as pd
import datetime

from jinja2 import Environment, FileSystemLoader
from pathlib import Path

from src.utils.logger import get_logger
logger = get_logger(__name__)
from src.config.config import config
from src.orders_block.order import Position, Position_Status, Direction, OrderType, OrderStatus


class TradeReport:
    def __init__(self, position: Position):
        if position.status not in {Position_Status.TAKEN_FULL, Position_Status.STOPPED, Position_Status.TAKEN_PART}:
            logger.error("Статус позиции не в завершенном состоянии")
            raise ValueError("TradeReport can only be generated for closed positions.")

        self.symbol = position.symbol
        self.direction = position.direction.value
        self.entry_price = float(position.avg_entry_price or 0.0)
        self.volume = float(position.opened_volume)
        self.status = position.status.value
        self.bar_opened = position.meta.get("bar_opened")
        self.bar_closed = position.meta.get("bar_closed")
        self.profit = float(position.profit)
        self.take_profits = self._take_profits_report(position)
        self.stop_loss = self._stop_loss_report(position)

    def _take_profits_report(self, position: Position) -> list[dict]:
        """
        Формирует структуру отчёта по уровням Take Profit.
        """
        take_profits = position.get_orders_by_type(OrderType.TAKE_PROFIT)
        take_profits_report = []

        for i, tp in enumerate(take_profits, start=1):
            take_profits_report.append({
                "id": i,
                "price": float(tp.price or 0.0),
                "volume": float(tp.volume),
                "status": tp.status.value,
                "profit": float(tp.meta.get("profit", 0.0)),
                "bar_executed": tp.meta.get("bar_executed")
            })

        return take_profits_report

    def _stop_loss_report(self, position: Position) -> dict:
        """
        Формирует структуру отчёта по стоп-лоссу.
        """
        stop_loss = next((o for o in position.get_orders_by_type(OrderType.STOP_LOSS) if o.status == OrderStatus.FILLED), None)
        if not stop_loss:
            return {}

        return {
            "price": float(stop_loss.price or 0.0),
            "volume": float(stop_loss.volume),
            "status": stop_loss.status.value,
            "bar_executed": stop_loss.meta.get("bar_executed"),
            "profit": float(stop_loss.meta.get("profit", 0.0))
        }

    def to_dict(self) -> dict:
        """Преобразует отчёт в словарь (удобно для сериализации)."""
        return {
            "symbol": self.symbol,
            "direction": self.direction,
            "entry_price": self.entry_price,
            "volume": self.volume,
            "status": self.status,
            "bar_opened": self.bar_opened.isoformat() if self.bar_opened else None,
            "bar_closed": self.bar_closed.isoformat() if self.bar_closed else None,
            "profit": self.profit,
            "take_profits": self.take_profits,
            "stop_loss": self.stop_loss
        }

    def to_json(self, indent: int = 4) -> str:
        """Возвращает JSON-представление отчёта, обрабатывая все нестандартные типы."""
        def default_serializer(obj):
            if isinstance(obj, (Decimal, float, int, str)):
                return obj
            elif isinstance(obj, Enum):
                return obj.value
            elif isinstance(obj, pd.Timestamp):
                return obj.isoformat()
            elif obj is None:
                return None
            else:
                return str(obj)

        data = self.to_dict()
        return json.dumps(data, ensure_ascii=False, indent=indent, default=default_serializer)


# -------------------------------------------------------------
# Формирование пути для экспорта и импорта файлов
# -------------------------------------------------------------
def get_export_path(symbol, file_extension: str = "html") -> str:
    """
    Формирует полный путь для сохранения файла и гарантирует существование директории.
    """
    report_date = datetime.date.today().isoformat()
    file_prefix = f"{symbol.replace('/', '_')} report {report_date}"
    path = config.get_setting("BACKTEST_SETTINGS", "REPORT_DIRECTORY")

    if not os.path.exists(path):
        os.makedirs(path)
        logger.info(f"Создана директория для экспорта: {path}")

    file_name = f"{file_prefix}.{file_extension}"
    return os.path.join(path, file_name)


# -----------------------
# Генерация HTML отчёта
# -----------------------
def generate_html_report(executed_reports, symbol, period_start, period_end, target_path, template_dir):
    """
    Генерация HTML-отчёта по списку объектов TradeReport или dict.
    Использует Jinja2-шаблон.
    """
    plain = [r.to_dict() if isinstance(r, TradeReport) else r for r in executed_reports]

    title = f"{symbol} Trade Report"
    period_start = pd.to_datetime(period_start).strftime("%Y-%m-%d")
    period_end = pd.to_datetime(period_end).strftime("%Y-%m-%d")

    profits = [r.get("profit", 0.0) for r in plain]
    total_profit = sum(profits)
    trades_count = len(profits)
    wins = sum(1 for p in profits if p > 0)
    losses = sum(1 for p in profits if p < 0)
    flat = trades_count - wins - losses
    win_rate = (wins / trades_count * 100) if trades_count else 0.0

    env = Environment(
        loader=FileSystemLoader(template_dir),
        autoescape=True,
        trim_blocks=True,
        lstrip_blocks=True
    )

    template = env.get_template("trade_report.html")
    html_content = template.render(
        title=title,
        period_start=period_start,
        period_end=period_end,
        reports=plain,
        total_profit=total_profit,
        trades_count=trades_count,
        win_rate=win_rate,
        wins=wins,
        losses=losses,
        flat=flat
    )

    Path(target_path).write_text(html_content, encoding="utf-8")
    return target_path