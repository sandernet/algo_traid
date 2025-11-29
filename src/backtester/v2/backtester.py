# backtest	Тестирование стратегии на исторических данных.	
# Симуляция выполнения сделок. 
# Расчет метрик производительности (прибыльность, просадка, Sharpe Ratio).


# Логирование
# ====================================================
from src.utils.logger import get_logger, LoggingTimer
logger = get_logger(__name__)

from src.config.config import config
from src.backtester.v2.backtester_coin import backtest_coin
from src.backtester.v2.utils import select_range_becktest

from src.backtester.v2.report_generator import generate_report

ALLOWED_Z2_OFFSET = 1  # сколько баров назад допускается последняя точка zigzag
# ====================================================
# точка входа для бэктеста
# ====================================================
def run_local_backtest():
    """Основной конвейер для получения и сохранения исторических данных по монетам из конфигурации."""

    # Получение настроек Биржи
    exchange = config.get_section("EXCHANGE_SETTINGS")
    # exchange = config.get_setting("EXCHANGE_SETTINGS", "EXCHANGE_ID")
    # limit = config.get_setting("EXCHANGE_SETTINGS", "LIMIT")
    
    # директории данных
    data_dir = config.get_setting("BACKTEST_SETTINGS", "DATA_DIR")

    
    # Параметры бэктеста
    full_datafile = config.get_setting("BACKTEST_SETTINGS", "FULL_DATAFILE")
    start_date = config.get_setting("BACKTEST_SETTINGS", "START_DATE")
    end_date = config.get_setting("BACKTEST_SETTINGS", "END_DATE")
    # Получение минимальное количество баров из настроек
    MIN_BARS = config.get_setting("STRATEGY_SETTINGS", "MINIMAL_BARS")
    
    # 1. Получение массива монет из конфигурации
    try:
        coins_list = config.get_section("COINS")
        timeframe_list = config.get_setting("BACKTEST_SETTINGS", "TIMEFRAME_LIST")
        logger.info(f"Загружено {len(coins_list)} монет из конфигурации.")
    except KeyError as e:
        # Хотя валидация должна была поймать это, это хорошая защита
        logger.error(f"Критическая ошибка: {e}")
        coins_list = [] # Устанавливаем пустой список для безопасной работы
        timeframe_list = [] # Устанавливаем пустой список для безопасной работы
        
    # Подключение модуля с загрузчиком данных
    from src.data_fetcher.data_fetcher import DataFetcher
    # 2. Обработка каждой монеты   
    for coin in coins_list:
        # try:
        logger.info("============================================================================")
        logger.info(f"[bold yellow] [{coin.get('SYMBOL')}/USDT][/bold yellow] 🚀 Запуск бэктеста ...")
        logger.info("============================================================================")

        symbol = coin.get("SYMBOL")+"/USDT"
        tick_size = coin.get("MINIMAL_TICK_SIZE")
        # 1. Загрузка из файла
        # Инициализируем DataFetcher
        fetcher = DataFetcher( coin,
            exchange=exchange, 
            directory=data_dir,
            )
        with LoggingTimer("[symbol] Загрузка минутных данных для точного исполнения стопов и тейков"):
            data_df_1m = fetcher.load_from_csv(file_type="csv") # загружаем минутные данные для точного исполнения стопов и тейков
    
        for timeframe in timeframe_list:
            # coin["TIMEFRAME"] = tf
            logger.info(f"[{symbol}] 🪙, 🕒 Таймфрейм: [bold yellow]{timeframe}[/bold yellow], Минимальный шаг цены {tick_size}")
            coin["TIMEFRAME"] = timeframe
            # timeframe = coin.get("TIMEFRAME")


            # Загружаем данные из CSV файла
            with LoggingTimer("[symbol] Загрузка данных торгового таймфрейма для бэктеста"):
                data_df = fetcher.load_from_csv(file_type="csv", timeframe=timeframe) # загружаем данные нужного таймфрейма
            
            
            if data_df is not None:
                logger.info(f"🚀 Запуск стратегии для {symbol} с локальными данными.")
                
                # 2. Выбор периода для бэктеста
                with LoggingTimer("[symbol] Формируем данные для бэктеста"):
                    select_data = select_range_becktest(data_df, timeframe, full_datafile, MIN_BARS, start_date, end_date)
                    if not full_datafile:
                        logger.info(f"[symbol] Данные для бэктеста отобраны с {select_data.index[0]} по {select_data.index[-1]}. Всего баров: {len(select_data)}")
                        start_date = select_data.index[0]
                        end_date = select_data.index[-1]

                # 3. Выполнение бэктеста
                #  Здесь вы передаете data_df в ваш модуль стратегии или бэктеста
                with LoggingTimer("[symbol] Выполнение бэктеста"):
                    executed_positions = backtest_coin(select_data,data_df_1m, coin, MIN_BARS)
                
                # 4. Генерация отчета по результатам бэктеста
                with LoggingTimer("[symbol] Генерация отчета"):
                    generate_report(select_data, executed_positions, coin, start_date, end_date)
                
                logger.info(f"[symbol] Закончена обработка бэктеста. Всего позиций: {len(executed_positions)}")
                
            else:
                logger.error(f"Невозможно запустить бектест для {symbol}: данные не загружены.")
            # except Exception as e:
            #     logger.error(f"Ошибка при бэктесте для монеты {coin.get('SYMBOL')}/USDT: {e}")
            



