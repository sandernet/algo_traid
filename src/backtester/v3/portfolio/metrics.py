
# * sharpe, drawdown, winrate
# src/backtester/portfolio/metrics.py


class MetricsCalculator:
    @staticmethod
    def from_positions(positions: dict) -> dict:
        total_pnl = sum(p.realized_pnl for p in positions.values())
        wins = [p for p in positions.values() if p.realized_pnl > 0]
        losses = [p for p in positions.values() if p.realized_pnl < 0]

        return {
            "total_pnl": total_pnl,
            "winrate": len(wins) / len(positions) * 100 if positions else 0,
            "wins": len(wins),
            "losses": len(losses),
            "count": len(positions)
        }
