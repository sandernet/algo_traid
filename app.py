# Загружаем и валидируем конфигурацию
# ====================================================
from src.config.config import config

# Логирование
# ====================================================
from src.utils.logger import get_logger
logger = get_logger(__name__)
logger.info("Конфигурация успешно загружена и прошла валидацию.")



# Основной код приложения
# ====================================================
def main():
    logger.info("Запуск приложения...")
    # Получение настроек Биржи
    exchange_id = config.get_setting("EXCHANGE_SETTINGS", "EXCHANGE_ID")
    limit = config.get_setting("EXCHANGE_SETTINGS", "LIMIT")
    
    
    # 1. Получение массива монет
    try:
        coins_list = config.get_section("COINS")
        print(f"Загружено {len(coins_list)} монет из конфигурации.")
    except KeyError as e:
        # Хотя валидация должна была поймать это, это хорошая защита
        print(f"Критическая ошибка: {e}")
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
            
            data_df.to_excel(f"data_{symbol.replace('/', '_')}_{timeframe}.xlsx")
            logger.info(f"Данные сохранены в файл data_{symbol.replace('/', '_')}_{timeframe}.xlsx")

            


    

# Точка входа
if __name__ == "__main__":
    main()    