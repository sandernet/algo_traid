# backtest	Тестирование стратегии на исторических данных.	
# Симуляция выполнения сделок. 
# Расчет метрик производительности (прибыльность, просадка, Sharpe Ratio).
import concurrent.futures
from decimal import Decimal
from uuid import uuid4
from typing import Dict, List, Tuple, Any

# Логирование
# ====================================================
from src.utils.logger import get_logger, LoggingTimer
logger = get_logger(__name__)

from src.config.config import config
# Подключение модуля с загрузчиком данных
from src.data_fetcher.data_fetcher import DataFetcher
from src.backtester.v2.backtester_coin import backtest_coin
from src.data_fetcher.utils import select_range_backtest

from src.backtester.v2.report_generator import generate_report

ALLOWED_Z2_OFFSET = 1  # сколько баров назад допускается последняя точка zigzag


class Test():
    # окно тестирования
    def __init__(self, start_date, end_date, data_dir, exchange, symbol, timeframe, full_datafile, min_bars, max_bars):
        self.id = uuid4().hex
        self.start_date = start_date
        self.end_date = end_date
        self.data_dir = data_dir
        self.exchange = exchange
        self.symbol = symbol
        self.timeframe = timeframe
        self.full_datafile = full_datafile
        self.min_bars = min_bars
        self.max_bars = max_bars
        
        
    def set_data_results(self):
        self.profit = Decimal("0")
        self.positions = {}
        self.statistics = {}
        self.reports = {}
        # self.step_bars = step_bars #
        


# -------------------------
# Manager & Executor
# -------------------------
class TestManager:
    """
    Управление тестами: запуск, получение списка позиций, подсчет статистики.
    Проведение паралельное тестирования 
    """
    def __init__(self):
        self.tests: Dict[str, Test] = {}
        self.all_executed_positions = []  # Для агрегации всех позиций
        self.all_reports = []  # Для агрегации всех отчетов
        
    def compute_metrics(positions, equity_curve):
        return {
            "profit": ...,
            "max_drawdown": ...,
            "sharpe": ...,
            "winrate": ...,
            "avg_rr": ...,
            "profit_factor": ...,
            "recovery_factor": ...
        }

    def set_settings(self):
        try:
            # Параметры биржи
            self.exchange = config.get_section("EXCHANGE_SETTINGS")
            # директории данных
            self.data_dir = config.get_setting("BACKTEST_SETTINGS", "DATA_DIR")
            # Параметры бэктеста
            self.full_datafile = config.get_setting("BACKTEST_SETTINGS", "FULL_DATAFILE")
            self.start_date = config.get_setting("BACKTEST_SETTINGS", "START_DATE")
            self.end_date = config.get_setting("BACKTEST_SETTINGS", "END_DATE")
            # минимальное количество баров для расчета стратегии
            self.MIN_BARS = config.get_setting("STRATEGY_SETTINGS", "MINIMUM_BARS_FOR_STRATEGY_CALCULATION")
            # 1. Получение массива монет из конфигурации
            self.coins_list = config.get_section("COINS")
            self.timeframe_list = config.get_setting("BACKTEST_SETTINGS", "TIMEFRAME_LIST")
            
            
            logger.info(f"Загружено {len(self.coins_list)} монет из конфигурации.")
        except Exception as e:
            logger.error(f"Ошибка при получении настроек биржи: {e}")
            

    def _execute_single_backtest(self, coin, timeframe) -> Dict[str, Any]:
        """
        Выполняет один бэктест для конкретной монеты и таймфрейма.
        Возвращает выполненные позиции и сгенерированный отчет.
        """
        symbol = coin.get("SYMBOL") + "/USDT"
        logger.info(f"[{symbol}, {timeframe}] 🟢 Начало обработки...")
        
        # Обновляем таймфрейм в словаре монеты
        coin["TIMEFRAME"] = timeframe

        # 1. Загрузка данных
        fetcher = DataFetcher(coin, exchange=self.exchange, directory=self.data_dir)
        data_df_1m = fetcher.load_from_csv(file_type="csv")
        data_df = fetcher.load_from_csv(file_type="csv", timeframe=timeframe)
        
        if data_df is None or data_df_1m is None:
            logger.error(f"[{symbol}, {timeframe}] Невозможно запустить бэктест: данные не загружены.")
            return {}

        # 2. Выбор периода для бэктеста (используем self.start_date/end_date)
        select_data = select_range_backtest(
            data_df,  self.full_datafile,  self.start_date, self.end_date
        )
        
        if select_data is None or len(select_data) == 0:
            logger.error(f"[{symbol}, {timeframe}] Нет достаточного объема данных для выбранного периода.")
            return {}

        # 3. Выполнение бэктеста
        executed_positions = backtest_coin(select_data, data_df_1m, coin, self.MIN_BARS)
        
        logger.info(f"[{symbol}, {timeframe}] ✅ Обработка завершена. Всего позиций: {len(executed_positions)}")
        return executed_positions


    # ====================================================
    # Точка входа для параллельного бэктеста
    # ====================================================
    def run_parallel_backtest(self, max_workers=4):
        """Основной конвейер для параллельного бэктеста."""
        self.set_settings()
        
        tasks = []
        for coin in self.coins_list:
            for timeframe in self.timeframe_list:
                # Создаем список задач (кортежей: coin, timeframe)
                tasks.append((coin.copy(), timeframe)) # .copy() чтобы избежать изменения одного объекта coin в разных потоках
                
        logger.info(f"📊 Всего задач бэктеста: {len(tasks)}")

        # Запуск параллельного выполнения
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Маппинг функции выполнения _execute_single_backtest на список аргументов
            # Важно: `executor.map` работает только с одной итерируемой переменной.
            # Используем `executor.submit` для нескольких аргументов и собираем `Future` объекты.
            future_to_task = {
                executor.submit(self._execute_single_backtest, coin_task, tf_task): (coin_task, tf_task)
                for coin_task, tf_task in tasks
            }
            
            # Обработка результатов по мере их завершения
            for future in concurrent.futures.as_completed(future_to_task):
                coin_task, tf_task = future_to_task[future]
                symbol = coin_task.get("SYMBOL") + "/USDT"
                try:
                    executed_positions, report_data = future.result()
                    
                    if executed_positions is not None:
                        # Агрегация позиций и отчетов
                        self.all_executed_positions.extend(executed_positions)
                    
                    if report_data is not None:
                        self.all_reports.append(report_data)
                        
                    logger.info(f"[{symbol}, {tf_task}] ✅ Результаты получены и агрегированы.")
                        
                except Exception as exc:
                    logger.error(f"[{symbol}, {tf_task}] ❌ Задача вызвала исключение: {exc}")

        logger.info("============================================================================")
        logger.info("📈 Все параллельные бэктесты завершены!")
        logger.info("============================================================================")
        
        # 5. Формирование полного отчета по всем тестам
        self._generate_full_summary_report()
        
        
    # ====================================================
    # точка входа для бэктеста
    # ====================================================
    def run_local_backtest(self):
        """Основной конвейер для получения и сохранения исторических данных по монетам из конфигурации."""

            

        # 2. Обработка каждой монеты   
        for coin in self.coins_list:
            # try:
            logger.info("============================================================================")
            logger.info(f"[bold yellow] [{coin.get('SYMBOL')}/USDT][/bold yellow] 🚀 Запуск бэктеста ...")
            logger.info("============================================================================")

            symbol = coin.get("SYMBOL")+"/USDT"
            tick_size = coin.get("MINIMAL_TICK_SIZE")
            # 1. Загрузка из файла
            # Инициализируем DataFetcher
            fetcher = DataFetcher( coin,
                exchange=self.exchange, 
                directory=self.data_dir,
                )
            with LoggingTimer("[symbol] Загрузка минутных данных для точного исполнения стопов и тейков"):
                data_df_1m = fetcher.load_from_csv(file_type="csv") # загружаем минутные данные для точного исполнения стопов и тейков
        
            for timeframe in self.timeframe_list:
                # coin["TIMEFRAME"] = tf
                logger.info(f"[{symbol}] 🪙, 🕒 Таймфрейм: [bold yellow]{timeframe}[/bold yellow], Минимальный шаг цены {tick_size}")
                coin["TIMEFRAME"] = timeframe
                # timeframe = coin.get("TIMEFRAME")


                # Загружаем данные из CSV файла
                with LoggingTimer("[symbol] Загрузка данных торгового таймфрейма для бэктеста"):
                    data_df = fetcher.load_from_csv(file_type="csv", timeframe=timeframe) # загружаем данные нужного таймфрейма
                
                if data_df is None:
                    continue
                
                # 2. Выбор периода для бэктеста
                with LoggingTimer("[symbol] Формируем данные для бэктеста"):
                    select_data = select_range_backtest(data_df,  self.full_datafile,  start_date, end_date)
                    if select_data is not None:
                        logger.info(f"[symbol] Данные для бэктеста отобраны с {select_data.index[0]} по {select_data.index[-1]}. Всего баров: {len(select_data)}")
                        start_date = select_data.index[0]
                        end_date = select_data.index[-1]

                # 3. Выполнение бэктеста
                #  Здесь вы передаете data_df в ваш модуль стратегии или бэктеста
                with LoggingTimer("[symbol] Выполнение бэктеста"):
                    executed_positions = backtest_coin(select_data,data_df_1m, coin, MIN_BARS)
                
                if data_df is not None:
                    logger.info(f"🚀 Запуск стратегии для {symbol} с локальными данными.")
                    
                    # 2. Выбор периода для бэктеста
                    with LoggingTimer("[symbol] Формируем данные для бэктеста"):
                        select_data = select_range_backtest(data_df, timeframe, self.full_datafile, self.MIN_BARS, self.start_date, self.end_date)
                        if not self.full_datafile:
                            logger.info(f"[symbol] Данные для бэктеста отобраны с {select_data.index[0]} по {select_data.index[-1]}. Всего баров: {len(select_data)}")
                            start_date = select_data.index[0]
                            end_date = select_data.index[-1]

                    # 3. Выполнение бэктеста
                    #  Здесь вы передаете data_df в ваш модуль стратегии или бэктеста
                    with LoggingTimer("[symbol] Выполнение бэктеста"):
                        executed_positions = backtest_coin(select_data,data_df_1m, coin, self.MIN_BARS)
                    
                    # 4. Генерация отчета по результатам бэктеста
                    with LoggingTimer("[symbol] Генерация отчета"):
                        generate_report(select_data, executed_positions, coin, self.start_date, self.end_date)
                    
                    logger.info(f"[symbol] Закончена обработка бэктеста. Всего позиций: {len(executed_positions)}")
                    
                else:
                    logger.error(f"Невозможно запустить бектест для {symbol}: данные не загружены.")
                # except Exception as e:
                #     logger.error(f"Ошибка при бэктесте для монеты {coin.get('SYMBOL')}/USDT: {e}")
                



