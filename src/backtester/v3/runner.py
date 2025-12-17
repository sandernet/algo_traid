# src/backtester/runner.py
from src.backtester.engine.backtest_engine import BacktestEngine
from src.backtester.engine.execution_loop import ExecutionLoop
from src.backtester.trading.position_builder import PositionBuilder
from src.backtester.trading.signal_handler import SignalHandler
from src.backtester.portfolio.portfolio import Portfolio
from src.backtester.portfolio.metrics import MetricsCalculator

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
        "positions": manager.positions,
        "portfolio": portfolio,
        "metrics": MetricsCalculator.from_positions(manager.positions)
    }
