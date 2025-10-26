# Логирование
# ====================================================
from src.utils.logger import get_logger
logger = get_logger(__name__)

from src.config.config import config


# ====================================================
# Основной конвейер для получения и сохранения исторических данных
# ====================================================
def run_data_update_pipeline():
    """Основной конвейер для получения и сохранения исторических данных по монетам из конфигурации."""

    # Получение настроек Биржи
    exchange_id = config.get_setting("EXCHANGE_SETTINGS", "EXCHANGE_ID")
    limit = config.get_setting("EXCHANGE_SETTINGS", "LIMIT")
    data_dir = config.get_setting("MODE_SETTINGS", "DATA_DIR")
    
    
    # 1. Получение массива монет
    try:
        coins_list = config.get_section("COINS")
        logger.info(f"Загружено {len(coins_list)} монет из конфигурации.")
    except KeyError as e:
        # Хотя валидация должна была поймать это, это хорошая защита
        logger.error(f"Критическая ошибка: {e}")
        coins_list = [] # Устанавливаем пустой список для безопасной работы
        
    # Подключение к Бирже
    from src.logical.data_fetcher.data_fetcher import DataFetcher
    # 2. Обработка каждой монеты   
    for coin in coins_list:
        logger.info("============================================================================")
        symbol = coin.get("SYMBOL")+"/USDT"
        timeframe = coin.get("TIMEFRAME")
        logger.info(f"Монета: {symbol}, Таймфрейм: {timeframe}")
       
        fetcher = DataFetcher( symbol, timeframe, exchange_id, limit)
        logger.info("Загрузка данных за всю историю...")
        data_df = fetcher.fetch_entire_history()
        
        # Сохранение данных
        if data_df is not None:
            logger.info(f"Загружено {len(data_df)} свечей {symbol}, {timeframe} за всю историю.")
         
            # Сохранить в подпапку 'csv_files'
            fetcher.export_to_csv(data_df, directory=data_dir+"csv_files") 
                
                # Сохранить в подпапку 'excel_files'
            fetcher.export_to_excel(data_df, directory=data_dir+"excel_files")