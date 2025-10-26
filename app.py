# Загружаем и валидируем конфигурацию
# ====================================================
from src.config.config import config

# Логирование
# ====================================================
from src.utils.logger import get_logger
logger = get_logger(__name__)
logger.info("Конфигурация успешно загружена и прошла валидацию.")


# ====================================================
# Основная функция
# ====================================================
def main():
    
    # logger.info("Запуск основного конвейера получения и сохранения исторических данных...")
    # from src.logical.data_fetcher.data_pipeline import run_data_update_pipeline
    # run_data_update_pipeline()
    # logger.info("Конвейер завершил работу.")
    
    logger.info("Запуск бэктестера с локальными данными...")
    from src.logical.backtester.backtester import run_local_backtest
    run_local_backtest()
    logger.info("Бэктестер завершил работу.")

# Точка входа
if __name__ == "__main__":
    main()    