# Загружаем и валидируем конфигурацию
# ====================================================
from src.config.config import config

# Логирование
# ====================================================
from src.utils.logger import get_logger
logger = get_logger(__name__)
logger.info("Конфигурация успешно загружена и прошла валидацию.")



# Основной код приложения

def main():
    from src.logical.data_fetcher.data_pipeline import run_data_update_pipeline

    logger.info("Запуск основного конвейера получения и сохранения исторических данных...")
    run_data_update_pipeline()
    logger.info("Конвейер завершил работу.")

# Точка входа
if __name__ == "__main__":
    main()    