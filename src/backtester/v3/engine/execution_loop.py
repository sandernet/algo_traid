# исполнение по lower TF

# src/backtester/engine/execution_loop.py
class ExecutionLoop:
    def __init__(self, engine):
        self.engine = engine

    def run(self, bars_1m):
        for bar in bars_1m:
            self.engine.process_bar(bar, bar[4])
