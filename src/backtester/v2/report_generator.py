# report_generator.py

from typing import List, Dict, Any
import os
import pandas as pd



from jinja2 import Environment, FileSystemLoader
from pathlib import Path

from src.utils.logger import get_logger
logger = get_logger(__name__)
from src.config.config import config

class MultiReportGenerator:
    """
    Мультирепорт: Монеты → Тесты → Позиции → Ордера
    """

    def __init__(self, data: dict):
        """
        data = {
            "BTC": {
                "1h": {
                    "ohlcv": ...,
                    "positions": {...}
                },
                "4h": {
                    ...
                }
            },
            "ETH": { ... }
        }
        """
        self.data = data

    def build_report(self):
        coins_report = {}

        for coin, tests in self.data.items():
            coin_entry = {}

            for timeframe, test_data in tests.items():

                gen = ReportGenerator(
                    data_ohlcv=test_data["ohlcv"],
                    positions=test_data["positions"]
                )

                test_report = gen.build_report()
                coin_entry[timeframe] = test_report   # ← вложенный отчёт теста

            coins_report[coin] = coin_entry

        return coins_report

class ReportGenerator:
    """
    Генератор отчётов на основе списка объектов Position.
    Подготовленные данные предназначены для передачи в Jinja2-шаблон.
    """

    def __init__(self, data_ohlcv, positions: dict[str, Any]):
        self.positions = positions
        self.data_ohlcv = data_ohlcv

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
        # x = []
        # for p in self.positions:
        #     x.append(self.serialize_position(p))
        
        return [self.serialize_position(p) for _, p in self.positions.items()]
        # return x

    # -----------------------------
    # СТАТИСТИКА
    # -----------------------------
    def build_statistics(self, serialized: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Создаёт статистику по всем позициям.
        """
        try:
            total_pnl = 0 # общий PnL
            total_loss = 0 # общий убыток
            total_win = 0 # общий прибыль
            wins = 0 # общее количество побед
            losses = 0 # общее количество проигрышей
            count = 0 # общее количество позиций
            winrate = 0 # процент побед

            for p in serialized:
                profit = p.get("profit") or 0
                total_pnl += profit
                if profit > 0:
                    wins += 1
                    total_win += profit
                elif profit < 0:
                    losses += 1
                    total_loss += profit

            count = len(serialized)
            winrate = (wins / count * 100) if count else 0

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
        
        # 1. Подготовка данных OHLCV
        # ohlcv_df = self.data_ohlcv

        # 2. Создание графика
        # chart_html = self.create_candlestick_chart(self.data_ohlcv, serialized_positions)

        return {
            "positions": serialized_positions,
            "stats": stats,
            # "chart_html": chart_html # Добавляем HTML-код графика
        }

# -------------------------------------------------------------
# Формирование пути для экспорта и импорта файлов
# -------------------------------------------------------------
def get_export_path(coin, file_extension: str = "html") -> str:
    """
    Формирует полный путь для сохранения файла и гарантирует существование директории.
    """
    symbol = coin.get('SYMBOL')
    timeframe = coin.get('TIMEFRAME', '-')
    # report_date = datetime.date.today().isoformat()
    file_prefix = f"{symbol}_UDDT__timeframe {timeframe}"
    path = config.get_setting("BACKTEST_SETTINGS", "REPORT_DIRECTORY")

    if not os.path.exists(path):
        os.makedirs(path)
        logger.info(f"Создана директория для экспорта: {path}")

    file_name = f"{file_prefix}.{file_extension}"
    return os.path.join(path, file_name)

# -----------------------
# Генерация HTML отчёта
# -----------------------
def generate_html_report(data, coin, period_start, period_end, target_path, template_dir):
    """
    Генерация HTML-отчёта по списку объектов TradeReport или dict.
    Использует Jinja2-шаблон.
    """

    title = f"{coin.get('SYMBOL', '')} Trade Report, timeframe {coin.get('TIMEFRAME', '')}, market_type {coin.get('MARKET_TYPE', '')}"
    period_start = pd.to_datetime(period_start).strftime("%Y-%m-%d")
    period_end = pd.to_datetime(period_end).strftime("%Y-%m-%d")

    multi = MultiReportGenerator(data)
    report = multi.build_report()
    # gen = ReportGenerator(data_ohlcv,positions)
    # report = gen.build_report()
    
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
    )

    Path(target_path).write_text(html_content, encoding="utf-8")
    return target_path

# -----------------------
# Основная функция генерации отчёта
# -----------------------
def generate_report(data, coin, start_date, end_date):
    # try:
    template_dir = config.get_setting("BACKTEST_SETTINGS", "TEMPLATE_DIRECTORY")
    files_report = get_export_path(coin=coin, file_extension="html")
            
    
            
    path = generate_html_report(
        data = data,
        coin = coin, 
        period_start =start_date,
        period_end =end_date,
        target_path = files_report, 
        template_dir = template_dir
        )
    logger.info(f"Отчет сохранен в: {path}")
    # except Exception as e:
    #     logger.error(f"Ошибка при генерации отчета для {symbol}: {e}")