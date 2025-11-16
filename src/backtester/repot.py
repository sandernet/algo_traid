import os
import json
from typing import List, Any
from decimal import Decimal
from enum import Enum
import pandas as pd
import datetime

from jinja2 import Environment, FileSystemLoader
from pathlib import Path

# ====================================================
from src.utils.logger import get_logger
logger = get_logger(__name__)
from src.config.config import config

from src.orders_block.trade_position import Position, Position_Status, TakeProfit, Direction, TakeProfit_Status 

class TradeReport:
    def __init__(self, position: 'Position'):
        if position.status in (Position_Status.NONE, Position_Status.CREATED, Position_Status.ACTIVE):
            logger.error("Статус позиции не в завершенном состоянии")
            raise ValueError("TradeReport can only be generated for closed positions.")

        self.symbol         = position.symbol
        # self.direction = position.direction
        # 🔹 Безопасно преобразуем Enum в строку
        self.direction = (
            position.direction.value if isinstance(position.direction, Direction) else str(position.direction)
        )
        self.entry_price = position.entry_price
        self.volume = position.volume_size
        # self.status = position.status
        self.status = (
            position.status.value if isinstance(position.status, Position_Status) else str(position.status)
        )
        self.bar_opened = position.bar_opened
        self.bar_closed = position.bar_closed
        self.profit = float(position.profit) if isinstance(position.profit, (Decimal, float, int)) else 0.0  # предполагается, что уже рассчитано в Position
        self.take_profits = self._take_profits_report(position.take_profits)
        
        # Добавим стоп-лосс если есть
        stop_loss = position.stop_loss

        if stop_loss is not None:
            # Извлекаем price
            price_val = self._to_float(getattr(stop_loss, 'price', None))
            # Извлекаем volume
            volume_val = self._to_float(getattr(stop_loss, 'volume', None))
            # Извлекаем статус
            status_val = getattr(stop_loss, 'status', None)
            
            # status_val = (
            #     status_attr.value if hasattr(status_attr, 'value') else str(status_attr)
            # ) if status_attr is not None else None
            # Извлекаем bar_executed (предполагаем, что это int или None)
            bar_executed_val = getattr(stop_loss, 'bar_executed', None)
            if bar_executed_val is not None:
                bar_executed_val = (
                    bar_executed_val.isoformat()
                    if hasattr(bar_executed_val, 'isoformat')
                    else str(bar_executed_val)
                )
                
            profit_sl = self._to_float(getattr(stop_loss, 'profit', Decimal('0.0')))
        else:
            price_val = volume_val = status_val = bar_executed_val  = None
            profit_sl = Decimal('0.0')

        self.stop_loss = {
            "price": price_val,
            "volume": volume_val,
            "status": status_val,
            "bar_executed": bar_executed_val,
            "profit": profit_sl
        }
        
    @staticmethod
    def _to_float(value):
        """Безопасно преобразует Decimal, numpy, pandas scalar -> float или None."""
        if value is None:
            return None
        # Обработка numpy/pandas
        if hasattr(value, 'item'):
            value = value.item()
        elif hasattr(value, 'values') and len(getattr(value, 'values', [])) > 0:
            value = value.values[0]
        # Преобразование числовых типов
        if isinstance(value, (int, float, Decimal)):
            return float(value)
        return None  # или raise ValueError, если строго
         
        
    def _take_profits_report(self, take_profits: List[TakeProfit]) -> list[dict]:
        """
        Формирует структуру отчёта по уровням Take Profit.
        """
        if not take_profits:
            return []
        
        take_profits_report = []

        for i, take in enumerate(take_profits, start=1):
            report_item = {
                "id": i,
                "price": float(take.price),
                "volume": float(take.volume),
                "status": take.Status.value if isinstance(take.Status, TakeProfit_Status) else str(take.Status),
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
            "entry_price": float(self.entry_price),
            "volume": float(self.volume),
            "status": self.status,
            "bar_opened": self.bar_opened.isoformat() if self.bar_opened is not None else None,
            "bar_closed": self.bar_closed.isoformat() if self.bar_closed is not None else None,
            "profit": float(self.profit),
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
                return obj.isoformat()  # '2025-11-11T12:30:00'
            elif obj is None:
                return None
            else:
                return str(obj)
        
        data = self.to_dict()
        
        return json.dumps(
           data,
            ensure_ascii=False,
            indent=indent,
            default=default_serializer
        )
    
# -------------------------------------------------------------
# Формирование пути для экспорта и импорта файлов
# -------------------------------------------------------------
def get_export_path(symbol, file_extension: str ="html" ) -> str:
    """
    Формирует полный путь для сохранения файла и гарантирует существование директории.
    """
    # добавляем дату формирования отчёта в имя файла (формат YYYY-MM-DD)
    report_date = datetime.date.today().isoformat()
    file_prefix = f"{symbol.replace('/', '_')} report {report_date}"
    path = config.get_setting("BACKTEST_SETTINGS", "REPORT_DIRECTORY") 
    
    # 1. Создание директории, если она не существует
    if not os.path.exists(path):
        os.makedirs(path)
        logger.info(f"Создана директория для экспорта: {path}")

    # 2. Формирование имени файла с датой
    # Пример: BTC_USDT report 2025-11-16.html
    file_name = f"{file_prefix}.{file_extension}"
    
    return os.path.join(path, file_name)


# -----------------------
# helper: привести объект к "чистому" словарю
# -----------------------
def to_plain_dict(report_obj: Any) -> dict:
    """
    Принимает TradeReport или dict и возвращает словарь, пригодный для рендеринга.
    Преобразует Enum, Decimal, pandas.Timestamp в строки/float.
    """
    # если объект имеет to_dict(), вызываем его
    if hasattr(report_obj, "to_dict"):
        data = report_obj.to_dict()
    elif isinstance(report_obj, dict):
        data = dict(report_obj)
    else:
        # попытка взять __dict__
        data = getattr(report_obj, "__dict__", {})
        if not isinstance(data, dict):
            raise TypeError("Unsupported report object type")

    # нормализуем поля
    def norm(x):
        # pandas.Timestamp, datetime -> iso string
        try:
            import pandas as pd
            if isinstance(x, pd.Timestamp):
                return x.isoformat()
        except Exception:
            pass
        if isinstance(x, (datetime.datetime, datetime.date)):
            return x.isoformat()
        if isinstance(x, Decimal):
            return float(x)
        # Enum -> value
        from enum import Enum
        if isinstance(x, Enum):
            return x.value
        return x

    out = {}
    for k, v in data.items():
        if v is None:
            out[k] = None
        elif k == "take_profits" and isinstance(v, (list, tuple)):
            # нормализуем каждый TP
            tps = []
            for tp in v:
                tp_norm = {}
                for kk, vv in dict(tp).items():
                    tp_norm[kk] = norm(vv)
                tps.append(tp_norm)
            out[k] = tps
        elif k == "stop_loss" and isinstance(v, dict):
            sl = {kk: norm(vv) for kk, vv in v.items()}
            out[k] = sl
        else:
            out[k] = norm(v)
    return out


# -----------------------
# главная функция: генерируем HTML отчет
# -----------------------
def generate_html_report(executed_reports, symbol, period_start, period_end, target_path, template_dir):
    """
    Генерация HTML-отчёта по списку объектов TradeReport или dict.
    Использует Jinja2-шаблон.
    """
    plain = [to_plain_dict(r) for r in executed_reports]


    title = symbol+" Trade Report"
    # period_start, period_end = period_start.strftime("%Y-%m-%d"), period_end.strftime("%Y-%m-%d")
    period_start = pd.to_datetime(period_start).strftime("%Y-%m-%d")
    period_end = pd.to_datetime(period_end).strftime("%Y-%m-%d")

    # статистика
    profits = [float(r.get("profit", 0.0)) for r in plain]
    total_profit = sum(profits)
    trades_count = len(profits)
    wins = sum(1 for p in profits if p > 0)
    losses = sum(1 for p in profits if p < 0)
    flat = trades_count - wins - losses
    win_rate = (wins / trades_count * 100) if trades_count else 0.0

    # создаём окружение Jinja2
    env = Environment(
        loader=FileSystemLoader(template_dir),
        autoescape=True,
        trim_blocks=True,
        lstrip_blocks=True
    )

    # загружаем шаблон
    template = env.get_template("trade_report.html")

    # рендерим HTML
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

    # сохраняем
    Path(target_path).write_text(html_content, encoding="utf-8")
    return target_path