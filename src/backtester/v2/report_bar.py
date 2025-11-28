from typing import List, Dict, Any

import plotly.graph_objects as go
from plotly.offline import plot


import pandas as pd



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