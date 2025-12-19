# src/backtester/runner.py
from src.backtester.v3.engine.backtest_engine import BacktestEngine
from src.backtester.v3.engine.execution_loop import ExecutionLoop
from src.backtester.v3.trading.position_builder import PositionBuilder
from src.backtester.v3.trading.signal_handler import SignalHandler
from src.backtester.v3.portfolio.portfolio import Portfolio
from src.backtester.v3.portfolio.metrics import MetricsCalculator


# Запуск бэктеста
def run_backtest(data, data_1m, coin, strategy, manager, engine, logger):
    portfolio = Portfolio(coin["START_DEPOSIT_USDT"])
    builder = PositionBuilder(manager, coin)
    signal_handler = SignalHandler(manager, builder, logger)
    exec_loop = ExecutionLoop(engine)

    bt = BacktestEngine(
        strategy,
        manager,
        exec_loop,
        signal_handler,
        portfolio,
        logger
    )

    bt.run(data, data_1m, coin["TIMEFRAME"])

    return {
        "test_id": manager.id,
        "positions": manager.positions,
        "portfolio": portfolio,
        "metrics": MetricsCalculator.from_positions(manager.positions)
    }
