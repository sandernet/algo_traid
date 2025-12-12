
import os

from jinja2 import Environment, FileSystemLoader
from pathlib import Path

from src.utils.logger import get_logger
logger = get_logger(__name__)
from src.config.config import config

from src.backtester.v2.backtester import Test
from src.backtester.v2.reportg_generator import ReportGenerator



# -----------------------
# Основная функция генерации отчёта по монете
# -----------------------
def generate_html_report(test: Test):
    """
    Генерация HTML-отчёта по списку объектов TradeReport или dict.
    Использует Jinja2-шаблон.
    """
    symbol, timeframe = test.coin.get("SYMBOL"), test.coin.get("TIMEFRAME")
    market_type = test.coin.get("MARKET_TYPE")
    period_start = test.settings_test.get("START_DATE", test.ohlcv.index.min())
    period_end = test.settings_test.get("END_DATE", test.ohlcv.index.max())
    template_dir = test.settings_test.get("TEMPLATE_DIRECTORY", "")
    
    title = f"{symbol} Trade Report, timeframe {timeframe}, market_type {market_type}"


    gen = ReportGenerator(test=test)
    report = gen.build_report()
    
    env = Environment(
        loader=FileSystemLoader(template_dir),
        autoescape=True,
        trim_blocks=True,
        lstrip_blocks=True
    )

    template = env.get_template("v2/report_coin.html")
    try:
        html_content = template.render(
            title=title,
            coin_name=symbol,
            period_start=period_start,
            period_end=period_end,
            **report,
        )
    except Exception as e:
        logger.error(f"Ошибка при генерации HTML-отчета:  {e}")
        return

    files_report = get_export_path(coin=test.coin, file_extension="html")

    Path(files_report).write_text(html_content, encoding="utf-8")
    logger.info(f"Отчет сохранен в: {files_report}")
        
# -------------------------------------------------------------
# Формирование пути для экспорта и импорта файлов
# -------------------------------------------------------------
def get_export_path(coin = None, file_extension: str = "html") -> str:
    """
    Формирует полный путь для сохранения файла и гарантирует существование директории.
    """
    if not coin:
        symbol = "all"
        timeframe = "all"
    else:
        symbol = coin.get('SYMBOL')
        timeframe = coin.get('TIMEFRAME', '-')
    
    # report_date = datetime.date.today().isoformat()
    file_prefix = f"{symbol}-USDT_TF-{timeframe}"
    path = config.get_setting("BACKTEST_SETTINGS", "REPORT_DIRECTORY")

    if not os.path.exists(path):
        os.makedirs(path)
        logger.info(f"Создана директория для экспорта: {path}")

    file_name = f"{file_prefix}.{file_extension}"
    return os.path.join(path, file_name)
