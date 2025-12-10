# backtest	Тестирование стратегии на исторических данных.	
# Симуляция выполнения сделок. 
# Расчет метрик производительности (прибыльность, просадка, Sharpe Ratio).
import concurrent.futures
from decimal import Decimal
from uuid import uuid4
from typing import Dict, Any, Tuple, List
from pandas import DataFrame
import pandas as pd

# Логирование
# ====================================================
from src.utils.logger import get_logger
logger = get_logger(__name__)
from src.config.config import config
# Подключение модуля с загрузчиком данных
from src.data_fetcher.data_fetcher import DataFetcher
from src.backtester.v2.backtester_coin import backtest_coin
from src.data_fetcher.utils import select_range_backtest
from src.backtester.v2.report_generator import generate_report




# Класс Test (окно тестирования) монета и таймфрейм период
class Test():
    # окно тестирования
    def __init__(self, data, coin, settings_test):
        # параметры теста
        self.id = uuid4().hex
        self.coin = coin
        self.settings_test = settings_test
        
        # Результаты теста
        self.ohlcv = data
        self.positions = {}
        
        # статистика теста
        self.total_pnl      = Decimal("0") # общий PnL
        self.total_loss     = Decimal("0") # общий убыток
        self.total_win      = Decimal("0") # общий прибыль
        self.wins           = Decimal("0") # общее количество побед
        self.losses         = Decimal("0") # общее количество проигрышей
        self.count_positions = Decimal("0") # общее количество позиций
        self.winrate        = Decimal("0") # процент побед
        

        
    def calculate_statistics(self):
        
        # TODO: Добавить расчеты статистики
        self.total_pnl = sum(pos.profit for pos in self.positions.values())
        self.total_win = sum(pos.profit for pos in self.positions.values() if pos.profit > 0)
        self.total_loss = sum(pos.profit for pos in self.positions.values() if pos.profit < 0)
        self.wins = sum(1 for pos in self.positions.values() if pos.profit > 0)
        self.losses = sum(1 for pos in self.positions.values() if pos.profit < 0)
        self.count_positions = len(self.positions)
        self.winrate = (self.wins / self.count_positions * 100) if self.count_positions > 0 else 0
        
        # Максимальная просадка
        
        # TODO: Добавить расчеты статистики прибыльности
        # ==================================
        # Добавить вызовы расчетов:
        # ==================================

    
# -------------------------
# Manager & Executor
# -------------------------
class TestManager:
    """
    Управление тестами: запуск, получение списка позиций, подсчет статистики.
    Проведение паралельное тестирования 
    """
    def __init__(self):
        try:
            # Параметры биржи
            self.exchange = config.get_section("EXCHANGE_SETTINGS")
            
            # Получение массива монет из конфигурации
            self.coins_list = config.get_section("COINS")
            # Параметры бэктеста
            self.settings_test = config.get_section("BACKTEST_SETTINGS")
            self.settings_strategy = config.get_section("STRATEGY_SETTINGS")
            
            # self.template_dir = config.get_setting("BACKTEST_SETTINGS", "TEMPLATE_DIRECTORY")
            # self.timeframe_list = config.get_setting("BACKTEST_SETTINGS", "TIMEFRAME_LIST")
            # self.data_dir = config.get_setting("BACKTEST_SETTINGS", "DATA_DIR")
            # self.full_datafile = config.get_setting("BACKTEST_SETTINGS", "FULL_DATAFILE")
            # self.start_date = config.get_setting("BACKTEST_SETTINGS", "START_DATE")
            # self.end_date = config.get_setting("BACKTEST_SETTINGS", "END_DATE")
            
            # минимальное количество баров для расчета стратегии
            # self.minimal_count_bars = config.get_setting("STRATEGY_SETTINGS", "MINIMUM_BARS_FOR_STRATEGY_CALCULATION")
            
            
            logger.info(f"Загружено {len(self.coins_list)} монет из конфигурации.")
        except Exception as e:
            logger.error(f"Ошибка при получении настроек биржи: {e}")
        
        self.tests: Dict[str, Test] = {}

        

            
    # ====================================================
    # 1. Выполнение одного бэктеста
    # ====================================================
    def _execute_single_backtest(self, coin, timeframe) -> Test: # Dict[str, Any]:
        """
        Выполняет один бэктест для конкретной монеты и таймфрейма.
        Возвращает все позиции которые были за указанный период
        """
        
        data_dir = self.settings_test.get("DATA_DIR", "")
        full_datafile = self.settings_test.get("FULL_DATAFILE", "")
        start_date = self.settings_test.get("START_DATE", "")
        end_date = self.settings_test.get("END_DATE", "")
        

        symbol = coin.get("SYMBOL") + "/USDT"
        logger.info(f"[{symbol}, {timeframe}] 🟢 Начало обработки...")
        
        # Обновляем таймфрейм в словаре монеты
        coin["TIMEFRAME"] = timeframe

        # 1. Загрузка данных
        fetcher = DataFetcher(coin, exchange=self.exchange, directory=data_dir)
        data_df_1m = fetcher.load_from_csv(file_type="csv")
        data_df = fetcher.load_from_csv(file_type="csv", timeframe=timeframe)
        
        if data_df is None or data_df_1m is None:
            logger.error(f"[{symbol}, {timeframe}] Невозможно запустить бэктест: данные не загружены.")
            raise ValueError("Невозможно запустить бэктест: данные не загружены.")

        # 2. Выбор периода для бэктеста (используем self.start_date/end_date)
        select_data = select_range_backtest(
            data_df=data_df,  
            full_datafile=full_datafile,  
            start_date=start_date, 
            end_date=end_date,
            offset_bars=self.settings_strategy.get("MINIMUM_BARS_FOR_STRATEGY_CALCULATION", 0)
        )
        select_data_1m = select_range_backtest(
            data_df=data_df_1m,  
            full_datafile=full_datafile,  
            start_date=start_date, 
            end_date=end_date,
            offset_bars=0
        )

        
        if select_data is None or len(select_data) == 0:
            logger.error(f"[{symbol}, {timeframe}] Нет достаточного объема данных для выбранного периода.")
            raise ValueError("Нет достаточного объема данных для выбранного периода.")

        
        # Основной расчет по свечам на выходе получаем массив позиций с ордерами
        positions = backtest_coin(select_data, select_data_1m, coin)
        
        test = Test(select_data,  coin, self.settings_test)
        
        test.positions = positions
        # расчет статистики
        test.calculate_statistics()
        
        
        # self.tests[test.id] = test
        logger.warning(f"[{symbol}, {timeframe}] ✅ Обработка завершена. Всего позиций: {len(positions)}")
        
        return test



    # ====================================================
    # Точка входа для параллельного бэктеста
    # ====================================================
    def run_parallel_backtest(self, max_workers=4):
        """Основной конвейер для параллельного бэктеста."""
        
        tasks = []
        for coin in self.coins_list:
            for timeframe in self.settings_test.get("TIMEFRAME_LIST", []):
                # Создаем список задач (кортежей: coin, timeframe)
                tasks.append((coin.copy(), timeframe)) # .copy() чтобы избежать изменения одного объекта coin в разных потоках
                
        logger.info(f"📊 Всего задач бэктеста: {len(tasks)}")
        
        # Словарь для структурирования результатов: {"BTC": {"1h": Test_obj, "4h": Test_obj}, ...}


        # Запуск параллельного выполнения
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Маппинг функции выполнения _execute_single_backtest на список аргументов
            # Важно: `executor.map` работает только с одной итерируемой переменной.
            # Используем `executor.submit` для нескольких аргументов и собираем `Future` объекты.

            future_to_task = {}
            
            # запускаем задачи строго в том порядке как идут в tasks
            for coin_task, tf_task in tasks:
                future = executor.submit(self._execute_single_backtest, coin_task, tf_task)
                future_to_task[future] = (coin_task, tf_task)
            
            # Обработка результатов по мере их завершения
            for future in concurrent.futures.as_completed(future_to_task):
                coin_task, tf_task = future_to_task[future]
                try:
                    # выполняем задачу тест
                    test_result = future.result()
                    # получили результат структура тест
                    if test_result:
                        self.tests[test_result.id] = coin_task # Сохраняем все тесты

                        # TODO Генерация отчета по одной монете
                        generate_report(test_result)
                        

                        logger.info(f"[{coin_task}, {tf_task}] ✅ Результаты получены и агрегированы.")
                        
                except Exception as exc:
                    logger.error(f"[{coin_task}, {tf_task}] ❌ Задача вызвала исключение: {exc}")
        
        

        # TODO формирование общего отчета по всем монетам
        # Перенести в модуль генерации отчета
        reports_structure = {}
        # Формируем отчет
        if len(self.tests) > 0:
            logger.info(f"📊 Генерация отчета... всего тестов {len(self.tests)}")
            # try:
                
            #     for test in self.tests.values():
            #         if test.symbol not in reports_structure:
            #             reports_structure[test.symbol] = {}
            #         reports_structure[test.symbol][test.timeframe] = test
                
            #     from src.backtester.v2.multi_report_generator import MultiReportGenerator 
                
            #     # Создаем экземпляр
            #     report_gen = MultiReportGenerator(reports_structure, template_dir=self.template_dir)
                
            #     # Передаем период тестирования из конфига
            #     report_path = report_gen.generate_html_report(
            #         template_name="report.html", 
            #     )
            #     logger.info(f"💾 Мульти-отчет сохранен в: {report_path}")
            # except Exception as e:
            #     logger.error(f"Ошибка при генерации мульти-отчета: {e}")
                
                
        logger.info("============================================================================")
        logger.info("📈 Все бэктесты завершены!")
        logger.info("============================================================================")

