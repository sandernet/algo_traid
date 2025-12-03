from pathlib import Path
from jinja2 import Environment, FileSystemLoader
import pandas as pd
from datetime import datetime
import json
from decimal import Decimal

import plotly.graph_objects as go
from plotly.subplots import make_subplots
from typing import Any, Dict, Tuple, List

from src.backtester.v2.backtester import Test
from src.orders_block.order import OrderStatus, OrderType
from src.backtester.v2.report_generator import ReportGenerator, get_export_path

class MultiReportGenerator:
    def __init__(self, data: Dict[str, Any], template_dir: str = "TEMPLATES"):
        """
        data = {
            "BTC/USDT": {
                "1h": {
                    "ohlcv": ... (pd.DataFrame),
                    "positions": {...} (dict of Position objects OR serialized)
                },
                ...
            },
            ...
        }
        """
        self.data = data
        self.template_dir = template_dir


    def _plot_to_json(self, fig: go.Figure) -> str:
        """Преобразует Plotly Figure в JSON для встраивания в HTML."""
        # Используем fig.to_json() для передачи Plotly данных, чтобы HTML-шаблон мог их отобразить.
        return json.dumps(fig.to_dict())
    
    # Helper: унифицировать positions (словарь -> список)
    def _normalize_positions(self, positions_obj):
        if isinstance(positions_obj, dict):
            return list(positions_obj.values())
        if isinstance(positions_obj, list):
            return positions_obj
        return list(positions_obj)
    
    
    # ---------------------------------------------------------
    # Основной генератор отчета
    # ---------------------------------------------------------

    def build_coin_summary(self, tests: Dict[str, Test]) -> Dict[str, Any]:
        """Собирает общую статистику по всем тестам (таймфреймам) для одной монеты."""
        total_pnl = Decimal("0")
        total_wins = 0
        total_losses = 0
        
        if not tests:
            return {}

        # Агрегация данных
        for test in tests.values():
            total_pnl += test.total_pnl
            total_wins += test.wins
            total_losses += test.losses
            
        count_positions = total_wins + total_losses
        winrate = (total_wins / count_positions) * 100 if count_positions > 0 else 0.0

        # Определение периода тестирования (по всем тестам)
        start_dates = [t.ohlcv.index.min() for t in tests.values() if not t.ohlcv.empty]
        end_dates = [t.ohlcv.index.max() for t in tests.values() if not t.ohlcv.empty]
        period_start = min(start_dates) if start_dates else None
        period_end = max(end_dates) if end_dates else None
        
        # Получаем название монеты/рынка из первого теста
        symbol = next(iter(tests.values())).symbol 
        
        return {
            "symbol": symbol,
            "period_start": str(period_start.strftime("%Y-%m-%d")) if period_start else "N/A",
            "period_end": str(period_end.strftime("%Y-%m-%d")) if period_end else "N/A",
            "total_pnl": float(total_pnl),
            "count_positions": count_positions,
            "wins": total_wins,
            "losses": total_losses,
            "winrate": f"{winrate:.2f}%",
        }
        
        
    def build_profit_drawdown_chart(self, test: Test) -> str:
        """
        График 1: Кривая Эквити (Прибыль) и Просадка.
        """
        if test.equity_curve.empty:
            return ""

        # Расчет просадки (Drawdown)
        equity = test.equity_curve
        peak = equity.expanding(min_periods=1).max()
        drawdown = peak - equity
        
        fig = make_subplots(specs=[[{"secondary_y": False}]])
        
        # Кривая Эквити
        fig.add_trace(
            go.Scatter(x=equity.index, y=equity.values, 
                    mode='lines', name='Кривая Эквити (Накопленный PnL)', 
                    line=dict(color='green')),
            secondary_y=False,
        )
        
        # Кривая Просадки (Отображаем как отрицательное значение для наглядности)
        fig.add_trace(
            go.Scatter(x=drawdown.index, y=drawdown.values, 
                    mode='lines', name='Просадка (Drawdown)', 
                    hmtline=dict(color='red', dash='dot'), opacity=0.5),
            secondary_y=False,
        )

        fig.update_layout(
            title_text=f"Кривая Эквити и Просадка ({test.timeframe})",
            xaxis_title="Дата/Время",
            yaxis_title="Накопленный PnL (USD)",
            hovermode="x unified",
            height=500
        )
        return self._plot_to_json(fig)


    def build_daily_profit_chart(self, test: Test) -> str:
        """
        График: Профит на каждый день (гистограмма).
        """
        if test.daily_profit.empty:
            return ""

        # Установка цвета для баров (зеленый для >0, красный для <0)
        colors = ['green' if p >= 0 else 'red' for p in test.daily_profit.values]

        fig = go.Figure()
        fig.add_trace(
            go.Bar(x=test.daily_profit.index, y=test.daily_profit.values, 
                   name='Дневной PnL', marker_color=colors)
        )

        fig.update_layout(
            title_text=f"Дневной PnL ({test.timeframe})",
            xaxis_title="Дата",
            yaxis_title="PnL за день (USD)",
            hovermode="x unified",
            height=300
        )
        return self._plot_to_json(fig)

    def build_order_execution_chart(self, test: Test) -> str:
        """
        График 2: OHLCV бары с метками исполнения ордеров (close_bar).
        """
        ohlcv = test.ohlcv
        if ohlcv.empty:
            return ""

        # 1. Основной график OHLCV (Свечи)
        fig = go.Figure(data=[go.Candlestick(
            x=ohlcv.index,
            open=ohlcv['open'],
            high=ohlcv['high'],
            low=ohlcv['low'],
            close=ohlcv['close'],
            name=f"{test.symbol} {test.timeframe}"
        )])

        # 2. Сбор данных об исполненных ордерах
        filled_orders = []
        for pos in test.positions.values():
            for order in pos.orders:
                if order.status == OrderStatus.FILLED and order.close_bar:
                    filled_orders.append({
                        'time': order.close_bar,
                        'price': float(order.price),
                        'type': order.order_type.value,
                        'pnl_abs': float(pos.pnl_abs) if order.order_type != OrderType.ENTRY else 0
                    })
        
        if filled_orders:
            orders_df = pd.DataFrame(filled_orders)
            
            # 3. Добавление маркеров ордеров на график
            fig.add_trace(go.Scatter(
                x=orders_df['time'],
                y=orders_df['price'],
                mode='markers',
                name='Исполненные Ордера',
                marker=dict(
                    size=10,
                    symbol='circle',
                    color=[
                        'blue' if t == 'entry' else
                        'green' if t == 'take_profit' else
                        'red' if t == 'stop_loss' or t == 'market_close' else 'black'
                        for t in orders_df['type']
                    ],
                    line=dict(width=1, color='DarkSlateGrey')
                ),
                text=[
                    f"Тип: {t.upper()}<br>Цена: {p:.2f}<br>PnL: {pnl:.2f}"
                    for t, p, pnl in zip(orders_df['type'], orders_df['price'], orders_df['pnl_abs'])
                ],
                hoverinfo='text'
            ))

        fig.update_layout(
            title_text=f"Исполнение Ордеров на графике Баров ({test.timeframe})",
            xaxis_title="Дата/Время",
            yaxis_title="Цена",
            xaxis_rangeslider_visible=True, # Интерактивный слайдер для выбора периода
            height=600
        )
        return self._plot_to_json(fig)

    # ---------------------------------------------------------
    # Генерация HTML-отчета (ОБНОВЛЕНО)
    # --------------------------------------------------------
    # Добавляем report_period для отображения в отчете
    def generate_html_report(self, template_name: str):
        """
        Основная функция генерации отчета.
        
        :param tests_map: Словарь {coin_name: {timeframe: Test_object}}
        """
        
        env = Environment(
            loader=FileSystemLoader(self.template_dir),
            autoescape=True,
            trim_blocks=True,
            lstrip_blocks=True
        )
        template = env.get_template(template_name)
        
        coins_output:   Dict[str, Any] = {}

        coin_summary:   Dict[str, Any] = {}
        tests_reports:  Dict[str, Any] = {}
            
        # Проходим по каждой монете
        for coin_name, tests_by_timeframe in self.data.items():
            
            # 1. Общая сводка по монете
            coin_summary = self.build_coin_summary(tests_by_timeframe)
            tests_reports: Dict[str, Any] = {}
            
            # 2. Отчеты по каждому таймфрейму (для кнопок/вкладок)
            for timeframe, test in tests_by_timeframe.items():
                
                # Обновляем все необходимые метрики
                test.calculate_statistics()
                test.build_equity_curve()
                test.calc_max_drawdown()
                test.build_daily_profit()

                # Генератор для сериализации позиций
                reporter = ReportGenerator(test.ohlcv, test.positions)
                
                test_report = {}
                test_report["timeframe"] = timeframe
                
                # Графики Plotly (конвертируются в JSON для встраивания)
                test_report["equity_drawdown_chart"] = self.build_profit_drawdown_chart(test)
                test_report["daily_profit_chart"]    = self.build_daily_profit_chart(test)
                test_report["order_execution_chart"] = self.build_order_execution_chart(test)
                
                # Все закрытые позиции (сериализованный список)
                test_report["closed_positions"] = reporter.build_report_data()

                # Статистика конкретного теста
                test_report["test_stats"] = {
                    "total_pnl": float(test.total_pnl),
                    "winrate": f"{test.winrate:.2f}%",
                    "max_drawdown": float(test.max_drawdown),
                    "count_positions": test.count_positions,
                    "ohlcv_start": str(test.ohlcv.index.min()),
                    "ohlcv_end": str(test.ohlcv.index.max()),
                }

                tests_reports[timeframe] = test_report

            coins_output[coin_name] = {
                "summary": coin_summary,
                "tests": tests_reports
            }
        
        # Общая информация для отчета
        global_report_data = {
            "coins": coins_output,
            "report_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "testing_period": f"{coin_summary.get('period_start', 'N/A')} - {coin_summary.get('period_end', 'N/A')}",
        }

        html = template.render(**global_report_data)
        files_report = get_export_path(coin=None, file_extension="html")
        Path(files_report).write_text(html, encoding="utf-8")
        print(f"✅ Отчет успешно сохранен: {files_report}")