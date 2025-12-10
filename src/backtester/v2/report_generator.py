# report_generator.py

from typing import List, Dict, Any
import os
import pandas as pd



from jinja2 import Environment, FileSystemLoader
from pathlib import Path

from src.utils.logger import get_logger
logger = get_logger(__name__)
from src.config.config import config

from src.orders_block.order import Position_Status
from src.backtester.v2.backtester import Test


class ReportGenerator:
    """
    Генератор отчётов на основе списка объектов Position.
    Подготовленные данные предназначены для передачи в Jinja2-шаблон.
    """

    def __init__(self, test):
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


# -----------------------
# Генерация HTML отчёта
# -----------------------
def generate_html_report(test: Test):#data, coin, template_dir, period_start, period_end, target_path ):
    """
    Генерация HTML-отчёта по списку объектов TradeReport или dict.
    Использует Jinja2-шаблон.
    """
    symbol, timeframe = test.coin.symbol, test.coin.timeframe
    market_type = test.coin.market_type
    period_start = test.ohlcv.index.min()
    period_end = test.ohlcv.index.max()
    template_dir = test.settings_test.get("TEMPLATE_DIRECTORY", "")
    


    title = f"{symbol} Trade Report, timeframe {timeframe}, market_type {market_type}"
    

    gen = ReportGenerator(test=test)
    report = gen.build_report()
    
    env = Environment(
        loader=FileSystemLoader(template_dir),
        autoescape=True,
        trim_blocks=True,
        lstrip_blocks=True
    )

    template = env.get_template("report_one_coin.html")
    try:
        html_content = template.render(
            title=title,
            period_start=period_start,
            period_end=period_end,
            **report,
        )
    except Exception as e:
        logger.error(f"Ошибка при генерации HTML-отчета:  {e}")
        return
    files_report = get_export_path(coin=test.coin, file_extension="html")
    Path(files_report).write_text(html_content, encoding="utf-8")
    return files_report

# # -----------------------
# # Основная функция генерации отчёта по монете
# # -----------------------
# def generate_report(self, data_ohlcv, positions: dict[str, Any], template_name:str):
#     # try:
#     template_dir = config.get_setting("BACKTEST_SETTINGS", "TEMPLATE_DIRECTORY")
#     start_date = config.get_setting("BACKTEST_SETTINGS", "START_DATE")
#     end_date = config.get_setting("BACKTEST_SETTINGS", "END_DATE")
    
#     files_report = get_export_path(coin=coin, file_extension="html")
            
    
            
#     path = self.generate_html_report(
#         data = data,
#         coin = coin, 
#         period_start =start_date,
#         period_end =end_date,
#         target_path = files_report, 
#         template_dir = template_dir
#         )
#     logger.info(f"Отчет сохранен в: {path}")
#     # except Exception as e:
#     #     logger.error(f"Ошибка при генерации отчета для {symbol}: {e}")
        
# -------------------------------------------------------------
# Формирование пути для экспорта и импорта файлов
# -------------------------------------------------------------
def get_export_path(coin = None, file_extension: str = "html") -> str:
    """
    Формирует полный путь для сохранения файла и гарантирует существование директории.
    """
    if not coin:
        symbol = "all"
        timeframe = "all"
    else:
        symbol = coin.get('SYMBOL')
        timeframe = coin.get('TIMEFRAME', '-')
    
    # report_date = datetime.date.today().isoformat()
    file_prefix = f"{symbol}-USDT_TF-{timeframe}"
    path = config.get_setting("BACKTEST_SETTINGS", "REPORT_DIRECTORY")

    if not os.path.exists(path):
        os.makedirs(path)
        logger.info(f"Создана директория для экспорта: {path}")

    file_name = f"{file_prefix}.{file_extension}"
    return os.path.join(path, file_name)
