# src/backtester/reports/single_test/test_report_generator.py
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from src.backtester.reports.serializers import serialize_positions
from src.utils.logger import get_logger

logger = get_logger(__name__)

class TestReportGenerator:
    def __init__(self, template_dir: str, settings_test: dict):
        self.env = Environment(
            loader=FileSystemLoader(template_dir),
            autoescape=True,
            trim_blocks=True,
            lstrip_blocks=True,
        )
        self.settings_test = settings_test

    def generate(
        self,
        *,
        result: dict,
        coin: dict,
        timeframe: str,
        output_path: Path
    ):
        template = self.env.get_template("v2/report_coin.html")

        html = template.render(
            symbol=coin["SYMBOL"],
            timeframe=timeframe,
            coin=coin,
            test_id=result["test_id"],
            metrics=result["metrics"],
            portfolio=result["portfolio"],
            settings=self.settings_test,
            positions=serialize_positions(result["positions"]),
        )

        output_path.write_text(html, encoding="utf-8")
        logger.info(f"✅ Test report saved: {output_path}")
