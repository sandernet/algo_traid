# Логирование
# ====================================================
from src.utils.logger import get_logger
logger = get_logger(__name__)

from src.config.config import config


# ====================================================
# Основной конвейер для получения и сохранения исторических данных
# ====================================================
def run_data_update_pipeline(load_min_timeframe = False):
    """Основной конвейер для получения и сохранения исторических данных по монетам из конфигурации."""

    # Получение настроек Биржи
    exchange = config.get_section("EXCHANGE_SETTINGS")
    limit = config.get_setting("EXCHANGE_SETTINGS", "LIMIT")
    data_dir = config.get_setting("BACKTEST_SETTINGS", "DATA_DIR")
    
    
    # 1. Получение массива монет
    try:
        coins_list = config.get_section("COINS")
        logger.info(f"Загружено {len(coins_list)} монет из конфигурации.")
    except KeyError as e:
        # Хотя валидация должна была поймать это, это хорошая защита
        logger.error(f"Критическая ошибка: {e}")
        coins_list = [] # Устанавливаем пустой список для безопасной работы
        
    # Подключение к Бирже
    from src.data_fetcher.data_fetcher import DataFetcher
    # 2. Обработка каждой монеты   
    for coin in coins_list:
        logger.info("============================================================================")
        symbol = coin.get("SYMBOL")+"/USDT"
        timeframe = coin.get("TIMEFRAME")
        min_timeframe = coin.get("MIN_TIMEFRAME")
        logger.info(f"Монета: {symbol}, Таймфрейм: {timeframe}, Минимальный таймфрейм: {min_timeframe}")
       
        fetcher = DataFetcher( coin,
            exchange=exchange, 
            directory=data_dir,
            )
        logger.info("Загрузка данных за всю историю...") 
        data_df = fetcher.fetch_entire_history(timeframe)
        
        # Сохранение данных
        if data_df is not None:
            logger.info(f"[{symbol}] Загружено {len(data_df)} свечей, таймфрейм {timeframe} - вся история.")
         
            # Сохранить в под папку 'csv_files'
            fetcher.export_to_csv(data_df, timeframe) 
                
                # Сохранить в под папку 'excel_files'
            fetcher.export_to_excel(data_df, timeframe)
            
            
        if load_min_timeframe:
            data_df_min = fetcher.fetch_entire_history(min_timeframe)
            # Сохранение данных
            if data_df_min is not None:
                logger.info(f"[{symbol}] Загружено {len(data_df_min)} свечей, таймфрейм {min_timeframe} - вся история.")
            
                # Сохранить в под папку 'csv_files'
                fetcher.export_to_csv(data_df_min, timeframe=min_timeframe) 
                    