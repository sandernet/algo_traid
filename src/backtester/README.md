[backtester]
<!-- Формирование данных для теста Запуск параллельного тестирования -->
   V
[Runner]
   v
[BacktestEngine.run]
   |
   v
[Итерация по барам OHLCV]
   |
   v
[Strategy.find_entry_point]
   |
   v
[SignalHandler]
   |
   +--> [PositionBuilder] (если нет позиции)
   |
   +--> [PositionManager] (закрытие / отмена)
   |
   v
[ExecutionLoop (1m)]
   |
   v
[ExecutionEngine]
   |
   v
[Portfolio.on_bar]
   |
   v
[Equity / Drawdown Curves]
   |
   v
[MetricsCalculator]
