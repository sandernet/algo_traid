
# Логирование
# ====================================================
from src.utils.logger import get_logger
logger = get_logger(__name__)

from src.config.config import config

# точка входа для бектеста
# ====================================================
def debugger_strategy():
    """Отладка стратегии"""

    # Получение настроек Биржи
    exchange_id = config.get_setting("EXCHANGE_SETTINGS", "EXCHANGE_ID")
    limit = config.get_setting("EXCHANGE_SETTINGS", "LIMIT")
    data_dir = config.get_setting("BACKTEST_SETTINGS", "DATA_DIR")
    
    
    # 1. Получение массива монет из конфигурации
    try:
        coins_list = config.get_section("COINS")
        logger.info(f"Загружено {len(coins_list)} монет из конфигурации.")
    except KeyError as e:
        # Хотя валидация должна была поймать это, это хорошая защита
        logger.error(f"Критическая ошибка: {e}")
        coins_list = [] # Устанавливаем пустой список для безопасной работы
        
    # Подключение модуля с загрузчиком данных
    from src.data_fetcher.data_fetcher import DataFetcher
    # 2. Обработка каждой монеты   
    for coin in coins_list:
        logger.info("============================================================================")
        symbol = coin.get("SYMBOL")+"/USDT"
        timeframe = coin.get("TIMEFRAME")
        logger.info(f"🪙 Монета: {symbol}, ↔️ Таймфрейм: {timeframe}")
        # 1. Инициализируем DataFetcher
        fetcher = DataFetcher( coin,
            exchange_id=exchange_id, 
            limit=limit,
            directory=data_dir,
            )
        # 2. Загрузка из файла
        data_full = fetcher.load_from_csv(file_type="csv")
    
        if data_full is not None:
            logger.info(f"🚀 Запуск стратегии 〽️ ZigZag и уровней Фибоначчи. {symbol} с локальными данными.")
            #  Здесь вы передаете data_full в ваш модуль стратегии или бектеста

            from src.logical.strategy.zigzag_fibo.zigzag_and_fibo import ZigZagAndFibo
            strategy = ZigZagAndFibo(symbol)
            
            zigzag, fiboLev = strategy.find_entry_point(data_full)
            
            if zigzag is None or fiboLev is None:
                logger.error(f"Стратегия не вернула корректные результаты для {symbol}.")
                continue
            
        else:
            logger.error(f"Невозможно запустить бектест для {symbol}: данные не загружены.")