# src/backtester/reports/collector.py
class SummaryCollector:
    def __init__(self):
        self.data = {}

    def add(
        self,
        *,
        coin: str,
        timeframe: str,
        metrics: dict,
        report_path: str
    ):
        self.data.setdefault(coin, [])
        self.data[coin].append({
            "timeframe": timeframe,
            "metrics": metrics,
            "report_path": report_path,
        })
