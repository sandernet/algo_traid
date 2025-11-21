# report_generator.py

from typing import List, Dict, Any
import datetime
import os
import pandas as pd
from jinja2 import Environment, FileSystemLoader
from pathlib import Path

from src.utils.logger import get_logger
logger = get_logger(__name__)
from src.config.config import config


class ReportGenerator:
    """
    Генератор отчётов на основе списка объектов Position.
    Подготовленные данные предназначены для передачи в Jinja2-шаблон.
    """

    def __init__(self, positions: List[Any]):
        self.positions = positions

    # -----------------------------
    # ПРЕОБРАЗОВАНИЕ ОБЪЕКТОВ
    # -----------------------------
    def serialize_order(self, order: Any) -> Dict[str, Any]:
        """
        Превращает Order в понятный Jinja2 словарь.
        """
        return {
            "id": getattr(order, "id", None),
            "type": getattr(order, "type", None),
            "side": getattr(order, "side", None),
            "price": getattr(order, "price", None),
            "amount": getattr(order, "amount", None),
            "timestamp": getattr(order, "timestamp", None),
            "raw": order  # на случай использования оригинального объекта
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
            "symbol": getattr(pos, "sym", None),
            "direction": getattr(pos, "dir", None),
            "status": getattr(pos, "status", None),
            "opened": getattr(pos, "opened", None),
            "closed": getattr(pos, "closed", None),
            "avg_entry": getattr(pos, "avg_entry", None),
            "pnl": getattr(pos, "pnl", None),
            "orders": orders,
            "raw": pos
        }

    def serialize_all_positions(self) -> List[Dict[str, Any]]:
        """
        Сериализует все позиции.
        """
        return [self.serialize_position(p) for p in self.positions]

    # -----------------------------
    # СТАТИСТИКА
    # -----------------------------
    def build_statistics(self, serialized: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Создаёт статистику по всем позициям.
        """
        total_pnl = 0
        wins = 0
        losses = 0

        for p in serialized:
            pnl = p["pnl"] or 0
            total_pnl += pnl
            if pnl > 0:
                wins += 1
            elif pnl < 0:
                losses += 1

        count = len(serialized)
        winrate = (wins / count * 100) if count else 0

        return {
            "total_positions": count,
            "total_pnl": total_pnl,
            "wins": wins,
            "losses": losses,
            "winrate": winrate,
        }

    # -----------------------------
    # ОСНОВНАЯ ФОРМА ОТЧЁТА
    # -----------------------------
    def build_report(self) -> Dict[str, Any]:
        """
        Собирает весь отчёт.
        Это итоговый объект для шаблона Jinja2.
        """
        serialized_positions = self.serialize_all_positions()
        stats = self.build_statistics(serialized_positions)

        return {
            "positions": serialized_positions,
            "stats": stats
        }

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
def generate_html_report(positions, symbol, period_start, period_end, target_path, template_dir):
    """
    Генерация HTML-отчёта по списку объектов TradeReport или dict.
    Использует Jinja2-шаблон.
    """
    # plain = [r.to_dict() if isinstance(r, TradeReport) else r for r in executed_reports]

    title = f"{symbol} Trade Report"
    period_start = pd.to_datetime(period_start).strftime("%Y-%m-%d")
    period_end = pd.to_datetime(period_end).strftime("%Y-%m-%d")

    # profits = [r.get("profit", 0.0) for r in plain]
    # total_profit = sum(profits)
    # trades_count = len(profits)
    # wins = sum(1 for p in profits if p > 0)
    # losses = sum(1 for p in profits if p < 0)
    # flat = trades_count - wins - losses
    # win_rate = (wins / trades_count * 100) if trades_count else 0.0


    gen = ReportGenerator(positions)
    report = gen.build_report()
    
    print(report.keys())


    env = Environment(
        loader=FileSystemLoader(template_dir),
        autoescape=True,
        trim_blocks=True,
        lstrip_blocks=True
    )

    template = env.get_template("trade_report2.html")
    html_content = template.render(
        title=title,
        period_start=period_start,
        period_end=period_end,
        **report,
        # total_profit=total_profit,
        # trades_count=trades_count,
        # win_rate=win_rate,
        # wins=wins,
        # losses=losses,
        # flat=flat
    )

    Path(target_path).write_text(html_content, encoding="utf-8")
    return target_path