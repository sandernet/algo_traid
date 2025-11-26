# report_generator.py

from typing import List, Dict, Any
import os
import pandas as pd

import plotly.graph_objects as go
from plotly.offline import plot
from plotly.subplots import make_subplots

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

    def __init__(self, data_ohlcv, positions: List[Any]):
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
        return [self.serialize_position(p) for p in self.positions]

    # -----------------------------
    # СТАТИСТИКА
    # -----------------------------
    def build_statistics(self, serialized: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Создаёт статистику по всем позициям.
        """
        try:
            total_pnl = 0
            wins = 0
            losses = 0

            for p in serialized:
                profit = p.get("profit") or 0
                total_pnl += profit
                if profit > 0:
                    wins += 1
                elif profit < 0:
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
        except Exception as e:
            logger.error(f"Error building statistics: {e}")
            return {"total_positions": 0, "total_pnl": 0, "wins": 0, "losses": 0, "winrate": 0}

    def create_candlestick_chart(self, df: pd.DataFrame, serialized_positions: List[Dict[str, Any]]) -> str:
        """
        Создает свечной график Plotly с точками входа/выхода.
        Возвращает HTML-строку графика.
        """
        profit = 0
        
        if df.empty:
            return "<div>Нет данных для графика.</div>"
            
        fig = go.Figure(data=[
            go.Candlestick(
                x=df.index,
                open=df['open'],
                high=df['high'],
                low=df['low'],
                close=df['close'],
                name="OHLC"
            )
        ])

        # Добавление маркеров позиций (точек входа и выхода)
        for pos in serialized_positions:
            open_bar_index = pos.get("bar_opened")
            close_bar_index = pos.get("bar_closed")
            
            # Проверка наличия индексов и их корректности
            if open_bar_index is not None and open_bar_index < df.index[-1]:
                open_dt = df.index[open_bar_index]
                entry_price = pos.get("avg_entry_price")
                direction = pos.get("direction", "LONG")
                profit = pos.get("profit", 0)

                # Маркер входа
                marker_symbol = 'triangle-up' if direction == 'LONG' else 'triangle-down'
                marker_color = 'green' if direction == 'LONG' else 'red'
                
                fig.add_trace(go.Scatter(
                    x=[open_dt],
                    y=[entry_price],
                    mode='markers',
                    marker=dict(symbol=marker_symbol, size=10, color=marker_color),
                    name=f"Вход #{pos['id']} ({direction})",
                    hovertext=f"ID: {pos['id']}<br>Направление: {direction}<br>Цена: {entry_price:.4f}<br>PnL: {profit:.2f}",
                    hoverinfo='text'
                ))

            # Маркер выхода (только для закрытых позиций)
            if close_bar_index is not None and close_bar_index < len(df) and pos.get("status") == "CLOSED":
                close_dt = df.index[close_bar_index]
                exit_price = df['close'].iloc[close_bar_index] # Используем цену закрытия бара
                
                # Используем круг для выхода, цвет зависит от PnL
                marker_color_exit = 'blue' if profit >= 0 else 'orange' 
                
                fig.add_trace(go.Scatter(
                    x=[close_dt],
                    y=[exit_price],
                    mode='markers',
                    marker=dict(symbol='circle', size=8, color=marker_color_exit),
                    name=f"Выход #{pos['id']}",
                    hovertext=f"ID: {pos['id']}<br>Выход (Закрытие)<br>Цена: {exit_price:.4f}<br>PnL: {profit:.2f}",
                    hoverinfo='text'
                ))

        fig.update_layout(
            title_text='Свечной график с позициями',
            xaxis_title='Дата/Время',
            yaxis_title='Цена',
            xaxis_rangeslider_visible=False # Скрываем ползунок Plotly для лучшего вида
        )

        # Возвращаем HTML-строку, которая может быть вставлена в Jinja2 шаблон
        # full_html=False позволяет вставить только div, а не весь HTML документ
        return plot(fig, output_type='div', include_plotlyjs=False, auto_open=False)        

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
def generate_html_report(data_ohlcv, positions, coin, period_start, period_end, target_path, template_dir):
    """
    Генерация HTML-отчёта по списку объектов TradeReport или dict.
    Использует Jinja2-шаблон.
    """

    title = f"{coin.get('SYMBOL', '')} Trade Report, timeframe {coin.get('TIMEFRAME', '')}, market_type {coin.get('MARKET_TYPE', '')}"
    period_start = pd.to_datetime(period_start).strftime("%Y-%m-%d")
    period_end = pd.to_datetime(period_end).strftime("%Y-%m-%d")

    gen = ReportGenerator(data_ohlcv,positions)
    report = gen.build_report()
    
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
def generate_report(data_ohlcv, executed_positions, coin, start_date, end_date):
    # try:
    template_dir = config.get_setting("BACKTEST_SETTINGS", "TEMPLATE_DIRECTORY")
    files_report = get_export_path(coin=coin, file_extension="html")
            
            
    path = generate_html_report(
        data_ohlcv = data_ohlcv,
        positions = executed_positions,
        coin = coin, 
        period_start =start_date,
        period_end =end_date,
        target_path = files_report, 
        template_dir = template_dir
        )
    logger.info(f"Отчет сохранен в: {path}")
    # except Exception as e:
    #     logger.error(f"Ошибка при генерации отчета для {symbol}: {e}")