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




# Класс Test (окно тестирования) монета и таймфрейм период
class Test():
    # окно тестирования
    def __init__(self, data, symbol, timeframe, data_dir):
        # параметры теста
        self.id = uuid4().hex
        self.symbol = symbol
        self.timeframe = timeframe
        self.data_dir = data_dir
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
        
        # Данные для графиков
        self.equity_curve: pd.Series = pd.Series(dtype=float)
        self.daily_profit: pd.Series = pd.Series(dtype=float)

    # расчеты для каждого теста
    # сумма депозита на каждый бар
    # def build_equity_curve(self):
    #     equity = 0
    #     curve: pd.Series = pd.Series(dtype=float)
    #     for pos in sorted(self.positions.values(), key=lambda p: p.bar_closed):
    #         equity += pos.profit
    #         timestamp = self.ohlcv.index[pos.bar_closed]
    #         curve.append({"timestamp": timestamp, "equity": float(equity)})
    #     self.equity_curve = curve
    def build_equity_curve(self):
        """
        Рассчитывает кривую эквити, используя datetime (pos.bar_closed) 
        напрямую в качестве индекса.
        """
        # Используем список для сбора данных, что гораздо быстрее, чем pd.Series.append()
        equity_data = [] 
        current_equity = Decimal("0")
        
        # Фильтрация и сортировка
        # Убедимся, что мы берем только закрытые позиции с меткой времени
        closed_positions = [
            pos for pos in self.positions.values() 
            if getattr(pos, 'bar_closed', None) is not None
        ]

        # Сортировка позиций по времени закрытия (datetime)
        sorted_positions = sorted(closed_positions, key=lambda p: p.bar_closed)

        for pos in sorted_positions:
            # 1. Накопление прибыли
            # Предполагаем, что pos.profit имеет тип Decimal
            current_equity += pos.profit
            
            # 2. Сохранение точки (Timestamp, Накопленный PnL)
            # pos.bar_closed (datetime) используется напрямую как метка времени
            timestamp = pos.bar_closed
            
            # Добавляем точку в список: (timestamp, PnL)
            equity_data.append((timestamp, float(current_equity))) 

        # 3. Создание Series за один раз для эффективности
        if equity_data:
            timestamps, equities = zip(*equity_data)
            # Используем pd.to_datetime для гарантии правильного типа индекса
            self.equity_curve = pd.Series(data=equities, 
                                        index=pd.to_datetime(timestamps), 
                                        name="Equity Curve", 
                                        dtype=float)
        else:
            self.equity_curve = pd.Series(dtype=float)
            
            
    # # профит на каждый день
    def build_daily_profit(self):
        """
        Рассчитывает ежедневный PnL (Daily Profit).
        Использует pos.bar_closed (datetime) напрямую.
        """
        daily_pnl_map = {}
        
        for pos in self.positions.values():
            # Проверка 1: Игнорируем активные позиции (у них нет времени закрытия)
            if pos.bar_closed is None:
                continue
            
            # 2. Получаем дату напрямую из datetime объекта, без обращения к self.ohlcv.index
            # Это устраняет ошибку индексации.
            date = pos.bar_closed.date() 
            
            # 3. Суммирование PnL. Преобразуем pos.profit (Decimal) в float.
            profit_amount = float(pos.profit)
            
            # Инициализация словаря с 0.0 и суммирование
            daily_pnl_map.setdefault(date, 0.0)
            daily_pnl_map[date] += profit_amount
            
        # 4. Создание финальной Series
        # Индекс Series будет состоять из объектов date (датированных ключей словаря)
        self.daily_profit = pd.Series(daily_pnl_map, dtype=float)
        
    # Максимальная просадка
    def calc_max_drawdown(self):
        highs = []
        dd = 0
        max_eq = float("-inf")
        for x in self.equity_curve:
            eq = x
            max_eq = max(max_eq, eq)
            dd = min(dd, eq - max_eq)
        self.max_drawdown = dd


    # добавить расчеты и статистику для каждого теста
        
    # TODO: Добавить расчеты статистики прибыльности
    def calculate_statistics(self):
        
        # TODO: Добавить расчеты статистики
        self.total_pnl = sum(pos.profit for pos in self.positions.values())
        self.total_win = sum(pos.profit for pos in self.positions.values() if pos.profit > 0)
        self.total_loss = sum(pos.profit for pos in self.positions.values() if pos.profit < 0)
        self.wins = sum(1 for pos in self.positions.values() if pos.profit > 0)
        self.losses = sum(1 for pos in self.positions.values() if pos.profit < 0)
        self.count_positions = len(self.positions)
        self.winrate = (self.wins / self.count_positions * 100) if self.count_positions > 0 else 0
        
        # ==================================
        # Добавить вызовы расчетов:
        # ==================================
        # self.build_equity_curve() 
        # self.build_daily_profit()
        # self.calc_max_drawdown()

    
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
            # директории данных
            self.data_dir = config.get_setting("BACKTEST_SETTINGS", "DATA_DIR")
            # Параметры бэктеста
            self.full_datafile = config.get_setting("BACKTEST_SETTINGS", "FULL_DATAFILE")
            self.start_date = config.get_setting("BACKTEST_SETTINGS", "START_DATE")
            self.end_date = config.get_setting("BACKTEST_SETTINGS", "END_DATE")
            # минимальное количество баров для расчета стратегии
            self.minimal_count_bars = config.get_setting("STRATEGY_SETTINGS", "MINIMUM_BARS_FOR_STRATEGY_CALCULATION")
            # 1. Получение массива монет из конфигурации
            self.coins_list = config.get_section("COINS")
            self.timeframe_list = config.get_setting("BACKTEST_SETTINGS", "TIMEFRAME_LIST")
            # ReportGenerator требует путь к шаблонам, берем его из конфига
            self.template_dir = config.get_setting("BACKTEST_SETTINGS", "TEMPLATE_DIRECTORY")
            
            
            logger.info(f"Загружено {len(self.coins_list)} монет из конфигурации.")
        except Exception as e:
            logger.error(f"Ошибка при получении настроек биржи: {e}")
        
        self.tests: Dict[str, Test] = {}
        self.data_ohlc: DataFrame
        

            
    # ====================================================
    # 1. Выполнение одного бэктеста
    # ====================================================
    def _execute_single_backtest(self, coin, timeframe) -> Test: # Dict[str, Any]:
        """
        Выполняет один бэктест для конкретной монеты и таймфрейма.
        Возвращает все позиции которые были за указанный период
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
            raise ValueError("Невозможно запустить бэктест: данные не загружены.")

        # 2. Выбор периода для бэктеста (используем self.start_date/end_date)
        select_data = select_range_backtest(
            data_df,  self.full_datafile,  self.start_date, self.end_date
        )
        
        if select_data is None or len(select_data) == 0:
            logger.error(f"[{symbol}, {timeframe}] Нет достаточного объема данных для выбранного периода.")
            raise ValueError("Нет достаточного объема данных для выбранного периода.")

        # 3. Выполнение бэктеста
        test = Test(select_data,  symbol, timeframe, self.data_dir)
        
        # расчет позиций по тесту 
        positions = backtest_coin(select_data, data_df_1m, coin, self.minimal_count_bars)
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
            for timeframe in self.timeframe_list:
                # Создаем список задач (кортежей: coin, timeframe)
                coin["TIMEFRAME"] = timeframe
                tasks.append((coin.copy(), timeframe)) # .copy() чтобы избежать изменения одного объекта coin в разных потоках
                
        logger.info(f"📊 Всего задач бэктеста: {len(tasks)}")
        
        # Словарь для структурирования результатов: {"BTC": {"1h": Test_obj, "4h": Test_obj}, ...}


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
                    test_result = future.result()
                    if test_result:
                        self.tests[test_result.id] = test_result # Сохраняем все тесты
                        
                        logger.info(f"[{symbol}, {tf_task}] ✅ Результаты получены и агрегированы.")
                        
                except Exception as exc:
                    logger.error(f"[{symbol}, {tf_task}] ❌ Задача вызвала исключение: {exc}")
        
        

        reports_structure = {}
        # Формируем отчет
        if len(self.tests) > 0:
            logger.info(f"📊 Генерация отчета... всего тестов {len(self.tests)}")
            try:
                
                for test in self.tests.values():
                    if test.symbol not in reports_structure:
                        reports_structure[test.symbol] = {}
                    reports_structure[test.symbol][test.timeframe] = test
                
                # Импортируем MultiReportGenerator из нужного файла (зависит от вашей структуры, 
                # но я предполагаю, что это класс, который мы модифицируем далее)
                # NOTE: Убедитесь, что у вас правильный импорт для MultiReportGenerator, который умеет генерировать HTML
                from src.backtester.v2.multi_report_generator import MultiReportGenerator 
                
                # Создаем экземпляр и генерируем отчет
                report_gen = MultiReportGenerator(reports_structure, template_dir=self.template_dir)
                
                # Передаем период тестирования из конфига
                report_path = report_gen.generate_html_report(
                    template_name="multi_backtest_report.html", 
                )
                logger.info(f"💾 Мульти-отчет сохранен в: {report_path}")
            except Exception as e:
                logger.error(f"Ошибка при генерации мульти-отчета: {e}")
                
                
        logger.info("============================================================================")
        logger.info("📈 Все бэктесты завершены!")
        logger.info("============================================================================")

        # Формируем отчет
        # TODO: 1. Агрегировать результаты, 2. Печатать отчет
        
        
    # # ====================================================
    # # точка входа для бэктеста
    # # ====================================================
    # def run_local_backtest(self):
    #     """Основной конвейер для получения и сохранения исторических данных по монетам из конфигурации."""

            

    #     # 2. Обработка каждой монеты   
    #     for coin in self.coins_list:
    #         # try:
    #         logger.info("============================================================================")
    #         logger.info(f"[bold yellow] [{coin.get('SYMBOL')}/USDT][/bold yellow] 🚀 Запуск бэктеста ...")
    #         logger.info("============================================================================")

    #         symbol = coin.get("SYMBOL")+"/USDT"
    #         tick_size = coin.get("MINIMAL_TICK_SIZE")
    #         # 1. Загрузка из файла
    #         # Инициализируем DataFetcher
    #         fetcher = DataFetcher( coin,
    #             exchange=self.exchange, 
    #             directory=self.data_dir,
    #             )
    #         with LoggingTimer("[symbol] Загрузка минутных данных для точного исполнения стопов и тейков"):
    #             data_df_1m = fetcher.load_from_csv(file_type="csv") # загружаем минутные данные для точного исполнения стопов и тейков
        
    #         for timeframe in self.timeframe_list:
    #             # coin["TIMEFRAME"] = tf
    #             logger.info(f"[{symbol}] 🪙, 🕒 Таймфрейм: [bold yellow]{timeframe}[/bold yellow], Минимальный шаг цены {tick_size}")
    #             coin["TIMEFRAME"] = timeframe
    #             # timeframe = coin.get("TIMEFRAME")


    #             # Загружаем данные из CSV файла
    #             with LoggingTimer("[symbol] Загрузка данных торгового таймфрейма для бэктеста"):
    #                 data_df = fetcher.load_from_csv(file_type="csv", timeframe=timeframe) # загружаем данные нужного таймфрейма
                
    #             if data_df is None:
    #                 continue
                
    #             # 2. Выбор периода для бэктеста
    #             with LoggingTimer("[symbol] Формируем данные для бэктеста"):
    #                 select_data = select_range_backtest(data_df,  self.full_datafile,  self.start_date, self.end_date)
    #                 if select_data is not None:
    #                     logger.info(f"[symbol] Данные для бэктеста отобраны с {select_data.index[0]} по {select_data.index[-1]}. Всего баров: {len(select_data)}")
    #                     start_date = select_data.index[0]
    #                     end_date = select_data.index[-1]

    #             # 3. Выполнение бэктеста
    #             #  Здесь вы передаете data_df в ваш модуль стратегии или бэктеста
    #             with LoggingTimer("[symbol] Выполнение бэктеста"):
    #                 executed_positions = backtest_coin(select_data,data_df_1m, coin, self.minimal_count_bars)
                
    #             if data_df is not None:
    #                 logger.info(f"🚀 Запуск стратегии для {symbol} с локальными данными.")
                    
    #                 # 2. Выбор периода для бэктеста
    #                 with LoggingTimer("[symbol] Формируем данные для бэктеста"):
    #                     select_data = select_range_backtest(data_df, self.full_datafile,  self.start_date, self.end_date)
    #                     if not self.full_datafile:
    #                         logger.info(f"[symbol] Данные для бэктеста отобраны с {select_data.index[0]} по {select_data.index[-1]}. Всего баров: {len(select_data)}")
    #                         start_date = select_data.index[0]
    #                         end_date = select_data.index[-1]

    #                 # 3. Выполнение бэктеста
    #                 #  Здесь вы передаете data_df в ваш модуль стратегии или бэктеста
    #                 with LoggingTimer("[symbol] Выполнение бэктеста"):
    #                     executed_positions = backtest_coin(select_data,data_df_1m, coin, self.minimal_count_bars)
                    
    #                 # 4. Генерация отчета по результатам бэктеста
    #                 with LoggingTimer("[symbol] Генерация отчета"):
    #                     generate_report(select_data, executed_positions, coin, self.start_date, self.end_date)
                    
    #                 logger.info(f"[symbol] Закончена обработка бэктеста. Всего позиций: {len(executed_positions)}")
                    
    #             else:
    #                 logger.error(f"Невозможно запустить бектест для {symbol}: данные не загружены.")
    #             # except Exception as e:
    #             #     logger.error(f"Ошибка при бэктесте для монеты {coin.get('SYMBOL')}/USDT: {e}")
                



