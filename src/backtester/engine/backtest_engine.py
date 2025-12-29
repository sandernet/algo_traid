# цикл по барам

# src/backtester/engine/backtest_engine.py
from decimal import Decimal
from src.data_fetcher.utils import select_range, shift_timestamp
from src.logical.hedging.als.als_engine import ALSEngine

# Engine выполнения бэктеста по барам.
# Отвечает за обход баров, вызов стратегии, обработку сигналов,
# запуск исполняющего цикла по минутным барам и учет PnL в портфеле.
class BacktestEngine:
    def __init__(self, strategy, manager, execution_loop, signal_handler, portfolio, logger):
        # strategy: объект стратегии с методом find_entry_point и параметром allowed_min_bars
        # manager: менеджер позиций, содержит словарь positions
        # execution_loop: объект, который симулирует исполнение ордеров по 1m барам
        # signal_handler: обработчик сигналов, возвращает/обновляет позицию
        # portfolio: учетная логика портфеля (расчёт floating, on_bar и т.д.)
        # logger: объект логирования
        self.strategy = strategy
        self.manager = manager
        self.execution_loop = execution_loop
        self.signal_handler = signal_handler
        self.portfolio = portfolio
        self.logger = logger

    # ===================================================
    # ? Запуск бэктеста
    # ===================================================
    def run(self, ohlcv, ohlcv_1m, timeframe):
        positions = {}

        arr = ohlcv[['open','high','low','close']].copy()
        arr['dt'] = ohlcv.index.to_numpy()
        arr = arr.to_numpy()

        # ! Итерация по барам торгового таймфрейма
        for i in range(self.strategy.allowed_min_bars, len(arr)):
            bar = arr[i]
            bar_time = bar[4]

            # ! запуск стратегии, генерирует сигнал
            # передаем нужное число баров на заданном таймфрейме.
            
            signal = self.strategy.find_entry_point(arr[i-self.strategy.allowed_min_bars:i])

            # ! Обработка сигнала и Создание / обновление позиции ордеров через SignalHandler
            # Сюда можно подовать сигналы из других стратегий и она будет работать
            positions = self.signal_handler.handle(signal, positions, bar)

            # ! Запуск исполнения по минутным барам, если есть открытые позиции
            # Позиций может быть несколько, основная и хеджирующие
            if len(positions) > 0:
                start = bar_time
                end = shift_timestamp(bar_time, 1, timeframe, +1)
                bars_1m = select_range(ohlcv_1m, start, end)
                arr_1m = bars_1m[['open', 'high', 'low', 'close']].assign(
                    dt=bars_1m.index.to_numpy()
                ).to_numpy()

                self.execution_loop.run(arr_1m)

            # ! Учет PnL в портфеле по окончании бара
            realized = Decimal("0")
            for p in self.manager.positions.values():
                for e in p.executions:
                    if e.bar_index == bar_time:
                        realized += e.realized_pnl
            
            # ! расчет floating  
            floating = self.portfolio.calculate_floating(
                self.manager,
                Decimal(str(bar[1])),
                Decimal(str(bar[2]))
            )
            self.logger.debug(f"Осуществленный PnL на баре {bar_time}: {realized}, Плавающий PnL: {floating}")
            # ! обновление портфеля по бару
            self.portfolio.on_bar(bar_time, realized, floating)
