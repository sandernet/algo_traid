import json
from typing import List, Any
from decimal import Decimal
from enum import Enum
import pandas as pd
import datetime
import html

# ====================================================
from src.utils.logger import get_logger
logger = get_logger(__name__)

from src.orders_block.trade_position import Position, PositionStatus, TakeProfitLevel, Direction, TakeProfit_Status 

class TradeReport:
    def __init__(self, position: 'Position'):
        if position.status in (PositionStatus.NONE, PositionStatus.CREATED, PositionStatus.ACTIVE):
            logger.error("Статус позиции не в завершенном состоянии")
            raise ValueError("TradeReport can only be generated for closed positions.")
        
        self.symbol = position.symbol
        # self.direction = position.direction
        # 🔹 Безопасно преобразуем Enum в строку
        self.direction = (
            position.direction.value if isinstance(position.direction, Direction) else str(position.direction)
        )
        self.entry_price = position.entry_price
        self.volume = position.volume_size
        # self.status = position.status
        self.status = (
            position.status.value if isinstance(position.status, PositionStatus) else str(position.status)
        )
        self.bar_opened = position.bar_opened
        self.bar_closed = position.bar_closed
        self.profit = float(position.profit) if isinstance(position.profit, (Decimal, float, int)) else 0.0  # предполагается, что уже рассчитано в Position
        self.take_profits = self._take_profits_report(position.take_profits)
        
        # Добавим стоп-лосс если есть
        stop_loss = position.stop_loss
        self.stop_loss = {
            # безопасно извлекаем значение цены из возможного pandas/numpy объекта или просто берем как есть
            "price": (lambda p: (None if p is None else (  # p — возможный scalar / Series / ndarray / Decimal
                (lambda v: (v if v is None else (float(v) if isinstance(v, (int, float, Decimal)) else v)))
                ( (p.item() if hasattr(p, "item") else (p.values[0] if getattr(p, "values", None) is not None else p)) )
            )))(getattr(stop_loss, "price", None)),
            "volume": (lambda v: float(v) if v is not None else None)(getattr(position.stop_loss, "volume", None)),
            "status": (
                stop_loss.status.value 
                if stop_loss is not None and isinstance(stop_loss.status, TakeProfit_Status) 
                else str(stop_loss.status) if stop_loss is not None else None
            ),
            "bar_executed": getattr(position.stop_loss, "bar_executed", None)
             }
         
        
    def _take_profits_report(self, take_profits: List[TakeProfitLevel]) -> list[dict]:
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
                "volume": take.volume,
                "status": take.TakeProfit_Status.value if isinstance(take.TakeProfit_Status, TakeProfit_Status) else str(take.TakeProfit_Status),
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
            "volume": self.volume,
            "status": self.status,
            "bar_opened": self.bar_opened.isoformat() if self.bar_opened is not None else None,
            "bar_closed": self.bar_closed.isoformat() if self.bar_closed is not None else None,
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
# функция рендера take_profits в HTML строку
# -----------------------
def _render_take_profits_html(take_profits: List[dict]) -> str:
    if not take_profits:
        return "<i>— нет</i>"
    rows = []
    rows.append("<table class='tp-table'><thead><tr>"
                "<th>ID</th><th>Price</th><th>Volume</th><th>Status</th><th>Bar Executed</th><th>Profit</th>"
                "</tr></thead><tbody>")
    for tp in take_profits:
        rows.append(
            "<tr>"
            f"<td>{html.escape(str(tp.get('id','')))}</td>"
            f"<td>{html.escape(str(tp.get('price','')))}</td>"
            f"<td>{html.escape(str(tp.get('volume','')))}</td>"
            f"<td>{html.escape(str(tp.get('status','')))}</td>"
            f"<td>{html.escape(str(tp.get('bar_executed','')))}</td>"
            f"<td>{html.escape(str(tp.get('profit','')))}</td>"
            "</tr>"
        )
    rows.append("</tbody></table>")
    return "\n".join(rows)

# -----------------------
# главная функция: генерируем HTML отчет
# -----------------------
def generate_html_report(executed_reports: List[Any], target_path: str = "trade_report.html") -> str:
    """
    executed_reports: список объектов TradeReport или словарей.
    target_path: куда сохранить HTML-файл.
    Вернёт путь к сохранённому файлу.
    """
    plain = [to_plain_dict(r) for r in executed_reports]

    # summary stats
    profits = []
    for r in plain:
        p = r.get("profit", 0.0)
        try:
            p = float(p)
        except Exception:
            p = 0.0
        profits.append(p)
    total_profit = sum(profits)
    trades_count = len(profits)
    wins = sum(1 for x in profits if x > 0)
    losses = sum(1 for x in profits if x < 0)
    flat = trades_count - wins - losses
    win_rate = (wins / trades_count * 100) if trades_count else 0.0

    # build HTML
    html_parts = []
    html_parts.append("""
<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8"/>
<title>Trade Report</title>
<style>
body{{font-family: Arial, Helvetica, sans-serif; margin:20px; color:#111}}
h1{{margin-bottom:0.2em}}
.summary{{display:flex;gap:20px;flex-wrap:wrap;margin-bottom:20px}}
.card{{background:#f7f7f9;border:1px solid #e1e1e6;padding:12px;border-radius:8px;min-width:160px}}
.table{{width:100%;border-collapse:collapse;margin-top:10px}}
.table th,.table td{{border:1px solid #ddd;padding:8px;text-align:left}}
.table th{{background:#f0f0f3}}
.details{{margin-top:10px}}
.tp-table{{width:100%;border-collapse:collapse}}
.tp-table th,.tp-table td{{border:1px solid #ddd;padding:6px}}
.toggle{{cursor:pointer;color:#0056b3;text-decoration:underline}}
.meta{{font-size:0.9em;color:#555}}
</style>
</head>
<body>
<h1>Trade Report</h1>
<div class="summary">
<div class="card"><strong>Total PnL</strong><div style="font-size:1.4em">{total_profit:.2f}</div></div>
<div class="card"><strong>Trades</strong><div style="font-size:1.4em">{trades_count}</div></div>
<div class="card"><strong>Win rate</strong><div style="font-size:1.4em">{win_rate:.2f}%</div></div>
<div class="card"><strong>Wins / Losses / Flat</strong><div style="font-size:1.1em">{wins} / {losses} / {flat}</div></div>
</div>
<table class="table">
<thead><tr>
<th>#</th><th>Symbol</th><th>Direction</th><th>Entry</th><th>Volume</th><th>Status</th><th>Opened</th><th>Closed</th><th>Profit</th><th>Details</th>
</tr></thead><tbody>
""".format(total_profit=total_profit, trades_count=trades_count, win_rate=win_rate, wins=wins, losses=losses, flat=flat))

    # rows
    for idx, r in enumerate(plain, start=1):
        symbol = html.escape(str(r.get("symbol","")))
        direction = html.escape(str(r.get("direction","")))
        entry = html.escape(str(r.get("entry_price","")))
        vol = html.escape(str(r.get("volume","")))
        status = html.escape(str(r.get("status","")))
        opened = html.escape(str(r.get("bar_opened","")))
        closed = html.escape(str(r.get("bar_closed","")))
        profit = r.get("profit", 0.0)
        try:
            profit = float(profit)
        except Exception:
            profit = 0.0

        # take_profits HTML
        tps_html = _render_take_profits_html(r.get("take_profits", []))

        # stop_loss
        sl = r.get("stop_loss")
        if sl:
            sl_html = ("<table class='tp-table'><tr><th>Price</th><th>Volume</th><th>Status</th><th>Bar Executed</th></tr>"
                       f"<tr><td>{html.escape(str(sl.get('price','')))}</td>"
                       f"<td>{html.escape(str(sl.get('volume','')))}</td>"
                       f"<td>{html.escape(str(sl.get('status','')))}</td>"
                       f"<td>{html.escape(str(sl.get('bar_executed','')))}</td></tr></table>")
        else:
            sl_html = "<i>— нет</i>"

        # details block (hidden by JS)
        details_id = f"det-{idx}"
        details_block = f"""
        <div id="{details_id}" class="details" style="display:none">
            <div class="meta"><strong>Take Profits:</strong></div>
            {tps_html}
            <div class="meta" style="margin-top:8px"><strong>Stop Loss:</strong></div>
            {sl_html}
          
        </div>
        """

        html_parts.append(
            "<tr>"
            f"<td>{idx}</td>"
            f"<td>{symbol}</td>"
            f"<td>{direction}</td>"
            f"<td>{entry}</td>"
            f"<td>{vol}</td>"
            f"<td>{status}</td>"
            f"<td>{opened}</td>"
            f"<td>{closed}</td>"
            f"<td>{profit:.2f}</td>"
            f"<td><span class='toggle' onclick=\"(function(e){{var el=document.getElementById('{details_id}');el.style.display=el.style.display==='none'?'block':'none';}})();\">toggle</span>{details_block}</td>"
            "</tr>"
        )

    # footer / scripts
    html_parts.append("""
        </tbody></table>

        <script>
        // (no external dependencies) - simple toggles already embedded inline
        </script>

        </body></html>
        """)

    html_content = "\n".join(html_parts)

    with open(target_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    return target_path

        