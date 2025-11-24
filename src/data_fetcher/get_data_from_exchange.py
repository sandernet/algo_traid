# Логирование
# ====================================================
from src.utils.logger import get_logger, LoggingTimer
logger = get_logger(__name__)

from src.config.config import config


# ====================================================
# Основной конвейер для получения и сохранения исторических данных
# ====================================================
def run_data_update_pipeline(loading_min=False):
    """Основной конвейер для получения и сохранения исторических данных по монетам из конфигурации."""
    
    
    # Получение настроек Биржи
    exchange = config.get_section("EXCHANGE_SETTINGS")
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
        min_timeframe = coin.get("MIN_TIMEFRAME", "")
        logger.info(f"Монета: {symbol}, Таймфрейм: [bold yellow]{timeframe}[/bold yellow], Минимальный таймфрейм: [bold yellow]{min_timeframe}[/bold yellow]")
       
        fetcher = DataFetcher( coin,
            exchange=exchange, 
            directory=data_dir,
            )
        
       
        # Загрузка данных
        with LoggingTimer(f"[{symbol}] load timeframe.....: {timeframe}"):
            data_df = fetcher.fetch_entire_history(timeframe)
            # Сохранение данных
            if data_df is not None:
                # Сохранить в под папку 'csv_files'
                fetcher.export_to_csv(data_df, timeframe) 
                    
                    # Сохранить в под папку 'excel_files'
                fetcher.export_to_excel(data_df, timeframe)
            
            
        if loading_min:
            if min_timeframe != "":
                with LoggingTimer(f"[{symbol}] load timeframe.....: {timeframe}"):
                    data_df_min = fetcher.fetch_entire_history(min_timeframe)
                
                    # Сохранение данных
                    if data_df_min is not None:
                        # Сохранить в под папку 'csv_files'
                        fetcher.export_to_csv(data_df_min, timeframe=min_timeframe) 
                    