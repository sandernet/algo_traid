# multi_report_generator.py
from dataclasses import dataclass
from typing import Dict, Any
from jinja2 import Environment, FileSystemLoader
from pathlib import Path
import pandas as pd
import plotly.graph_objects as go
import os

from report_generator import ReportGenerator
from src.utils.logger import get_logger
logger = get_logger(__name__)


@dataclass
class TestInfo:
    ohlcv: pd.DataFrame
    positions: dict
    timeframe: str
    period_start: str
    period_end: str
    exec_time: float  # время выполнения теста
    test_name: str    # можно поставить timeframe или ID теста


class MultiReportGenerator:
    """
    Формирует ОДИН ОБЩИЙ отчет:
    Монеты → Тесты → Позиции → Ордера + Графики
    """

    def __init__(self, data: Dict[str, Dict[str, TestInfo]], template_dir: str):
        """
        data =
        {
            "BTC": {
                "1h": TestInfo(...),
                "4h": TestInfo(...)
            },
            "ETH": {
                "1h": TestInfo(...)
            }
        }
        """
        self.data = data
        self.template_dir = template_dir

    # ---------------------------------------------------------
    # График: OHLCV + ордера + открытие/закрытие позиций
    # ---------------------------------------------------------
    def build_chart(self, ohlcv: pd.DataFrame, positions_serialized):
        fig = go.Figure()

        # Свечи
        fig.add_trace(go.Candlestick(
            x=ohlcv.index,
            open=ohlcv['open'],
            high=ohlcv['high'],
            low=ohlcv['low'],
            close=ohlcv['close'],
            name="Price"
        ))

        # Отмечаем ордера
        buy_x = []
        buy_y = []
        sell_x = []
        sell_y = []

        for p in positions_serialized:
            for o in p["orders"]:
                if o["direction"] == "BUY":
                    buy_x.append(ohlcv.index[o["created_bar"]])
                    buy_y.append(o["price"])
                else:
                    sell_x.append(ohlcv.index[o["created_bar"]])
                    sell_y.append(o["price"])

        fig.add_trace(go.Scatter(
            x=buy_x, y=buy_y, mode="markers",
            marker=dict(size=8), name="BUY"
        ))

        fig.add_trace(go.Scatter(
            x=sell_x, y=sell_y, mode="markers",
            marker=dict(size=8), name="SELL"
        ))

        fig.update_layout(
            height=600,
            template="plotly_white",
            xaxis_rangeslider_visible=True
        )

        return fig.to_html(include_plotlyjs='cdn')

    # ---------------------------------------------------------
    # Формируем отчет по монете
    # ---------------------------------------------------------
    def build_coin_summary(self, coin_tests):
        """
        Статистика по монете: сколько тестов, какие таймфреймы,
        средний профит, суммарное время.
        """
        summaries = {
            "tests_count": len(coin_tests),
            "timeframes": list(coin_tests.keys()),
            "avg_profit": 0,
            "avg_winrate": 0,
            "total_exec_time": 0
        }

        total_profit = 0
        total_winrate = 0

        for tf, test in coin_tests.items():
            gen = ReportGenerator(test.ohlcv, test.positions)
            report = gen.build_report()

            total_profit += report["stats"]["total_pnl"]
            total_winrate += report["stats"]["winrate"]
            summaries["total_exec_time"] += test.exec_time

        summaries["avg_profit"] = total_profit / len(coin_tests)
        summaries["avg_winrate"] = total_winrate / len(coin_tests)

        return summaries

    # ---------------------------------------------------------
    # Генерация общего HTML
    # ---------------------------------------------------------
    def generate_html(self, output_path: str):
        env = Environment(
            loader=FileSystemLoader(self.template_dir),
            autoescape=True,
            trim_blocks=True,
            lstrip_blocks=True
        )

        template = env.get_template("global_report.html")

        coins_output = {}

        for coin, tests in self.data.items():
            coin_entry = {
                "summary": self.build_coin_summary(tests),
                "tests": {}
            }

            for timeframe, test in tests.items():
                gen = ReportGenerator(test.ohlcv, test.positions)
                test_report = gen.build_report()

                # добавляем график
                chart_html = self.build_chart(test.ohlcv, test_report["positions"])
                test_report["chart_html"] = chart_html
                test_report["period_start"] = test.period_start
                test_report["period_end"] = test.period_end
                test_report["exec_time"] = test.exec_time
                test_report["timeframe"] = timeframe

                coin_entry["tests"][timeframe] = test_report

            coins_output[coin] = coin_entry

        html = template.render(coins=coins_output)

        Path(output_path).write_text(html, encoding="utf-8")
        return output_path
