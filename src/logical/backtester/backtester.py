# backtester	Тестирование стратегии на исторических данных.	
# Симуляция выполнения сделок. 
# Расчет метрик производительности (прибыльность, просадка, Sharpe Ratio).

# Логирование
# ====================================================
from src.utils.logger import get_logger
logger = get_logger(__name__)

from src.config.config import config

# точка входа для бэктестера
# ====================================================
def run_local_backtest():
    """Основной конвейер для получения и сохранения исторических данных по монетам из конфигурации."""

    # Получение настроек Биржи
    exchange_id = config.get_setting("EXCHANGE_SETTINGS", "EXCHANGE_ID")
    limit = config.get_setting("EXCHANGE_SETTINGS", "LIMIT")
    data_dir = config.get_setting("MODE_SETTINGS", "DATA_DIR")
    
    
    # 1. Получение массива монет из конфигурации
    try:
        coins_list = config.get_section("COINS")
        logger.info(f"Загружено {len(coins_list)} монет из конфигурации.")
    except KeyError as e:
        # Хотя валидация должна была поймать это, это хорошая защита
        logger.error(f"Критическая ошибка: {e}")
        coins_list = [] # Устанавливаем пустой список для безопасной работы
        
    # Подключение модуля с загрузчиком данных
    from src.logical.data_fetcher.data_fetcher import DataFetcher
    # 2. Обработка каждой монеты   
    for coin in coins_list:
        logger.info("============================================================================")
        symbol = coin.get("SYMBOL")+"/USDT"
        timeframe = coin.get("TIMEFRAME")
        logger.info(f"🪙 Монета: {symbol}, ↔️ Таймфрейм: {timeframe}")
        # 1. Инициализируем DataFetcher
        fetcher = DataFetcher( 
            symbol=symbol, 
            timeframe=timeframe, 
            exchange_id=exchange_id, 
            limit=limit,
            directory=data_dir,
            )
        # 2. Загрузка из файла
        data_df = fetcher.load_from_csv(file_type="csv")
    
        if data_df is not None:
            logger.info(f"🚀 Запуск стратегии для {symbol} с локальными данными.")
            #  Здесь вы передаете data_df в ваш модуль стратегии или бэктестера
            backtest_coin(data_df)
        else:
            logger.error(f"Невозможно запустить бэктест для {symbol}: данные не загружены.")
        

# ====================================================
# Запуск бэктеста для одной монеты
# ====================================================
def backtest_coin(data_df):
    """
    Запуск бэктеста с данными, загруженными из локального файла.
    """
    
    
    logger.info("🎢 Поиск экстремумов")
    from src.logical.strategy.mozart.strategy import run_strategy
    
    run_strategy(data_df)
    logger.info("🎢 Поиск экстремумов завершен.")
    
    
    MIN_BARS = config.get_setting("STRATEGY_SETTINGS", "MINIMAL_BARS")
    for i in range(MIN_BARS, len(data_df)):
        logger.info(f"Обработка бара {data_df.index[i]} |================================================")
        current_data = data_df.iloc[i-MIN_BARS : i]
        
        logger.info(f"Обработка бара {i}/ взято {len(current_data)} баров")
    
        from src.logical.strategy.zigzag_fibo.zigzag_and_fibo import start_zz_and_fibo
        # Применяем функцию к каждой строке
        signal = start_zz_and_fibo(current_data)
        data_df.loc[i, 'signal'] = signal

    # signal = data_df['Signal'].values()
        
    # if signal is not None:
    #     logger.info("🎢 Запуск расчета данных по ордерам по стратегии.")
    #     # запускаем расчет ордеров по стратегии


