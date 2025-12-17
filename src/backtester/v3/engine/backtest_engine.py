# цикл по барам

# src/backtester/engine/backtest_engine.py
from decimal import Decimal
from src.data_fetcher.utils import select_range, shift_timestamp

class BacktestEngine:
    def __init__(self, strategy, manager, execution_loop, signal_handler, portfolio, logger):
        self.strategy = strategy
        self.manager = manager
        self.execution_loop = execution_loop
        self.signal_handler = signal_handler
        self.portfolio = portfolio
        self.logger = logger

    def run(self, ohlcv, ohlcv_1m, timeframe):
        position = None

        arr = ohlcv[['open','high','low','close']].copy()
        arr['dt'] = ohlcv.index.to_numpy()
        arr = arr.to_numpy()

        for i in range(self.strategy.allowed_min_bars, len(arr)):
            bar = arr[i]
            bar_time = bar[4]

            signal = self.strategy.find_entry_point(arr[i-self.strategy.allowed_min_bars:i])

            position = self.signal_handler.handle(signal, position, bar_time)

            if position:
                start = bar_time
                end = shift_timestamp(bar_time, 1, timeframe, +1)
                bars_1m = select_range(ohlcv_1m, start, end)
                arr_1m = bars_1m[['open','high','low','close']].assign(
                    dt=bars_1m.index.to_numpy()
                ).to_numpy()

                self.execution_loop.run(arr_1m)

            realized = sum(
                e.realized_pnl
                for p in self.manager.positions.values()
                for e in p.executions
                if e.bar_index == bar_time
            )

            floating = self.portfolio.calculate_floating(
                self.manager,
                Decimal(str(bar[1])),
                Decimal(str(bar[2]))
            )

            self.portfolio.on_bar(bar_time, realized, floating)
