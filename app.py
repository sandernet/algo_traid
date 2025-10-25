# Загружаем и валидируем конфигурацию
# ====================================================
from src.config.config import config

# Логирование
# ====================================================
from src.utils.logger import get_logger
logger = get_logger(__name__)
logger.info("Конфигурация успешно загружена и прошла валидацию.")


from src.logical.data_fetcher.data_fetcher import DataFetcher


# Основной код приложения
# ====================================================
def main():
    logger.info("Приложение запущено")
    # Получение настроек Биржи
    exchange_id = config.get_setting("EXCHANGE_SETTINGS", "EXCHANGE_ID")
    
    
    # 1. Получение массива монет
    try:
        coins_list = config.get_section("COINS")
        print(f"Загружено {len(coins_list)} монет из конфигурации.")
    except KeyError as e:
        # Хотя валидация должна была поймать это, это хорошая защита
        print(f"Критическая ошибка: {e}")
        coins_list = [] # Устанавливаем пустой список для безопасной работы
        
    
    for coin in coins_list:
        symbol = coin.get("SYMBOL")
        timeframe = coin.get("TIMEFRAME")
        print(f"Монета: {symbol}, Таймфрейм: {timeframe}")
        
        
        fetcher = DataFetcher()
        data_df = fetcher.fetch_all_historical_data()
        
        if data_df is not None:
            print("\n--- Фрагмент загруженных данных (DataFrame) ---")
            print(data_df.head())
            print(data_df.tail())
    
    # Здесь можно добавить основной код приложения
    # Например, запуск бота или других сервисов
    

# Точка входа
if __name__ == "__main__":
    main()    