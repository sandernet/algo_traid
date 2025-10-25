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
    logger.info("Приложение запущено")
    # Получение настроек Биржи
    exchange_id = config.get_setting("EXCHANGE_SETTINGS", "EXCHANGE_ID")
    timeframe = config.get_setting("EXCHANGE_SETTINGS", "TIMEFRAME")
    
    logger.info(f"Биржа: {exchange_id}, Пара: {timeframe}")
    
    # Здесь можно добавить основной код приложения
    # Например, запуск бота или других сервисов
    

# Точка входа
if __name__ == "__main__":
    main()    