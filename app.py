import argparse




# ====================================================
# Основная функция
# ====================================================
def main():
    parser = argparse.ArgumentParser(description='Программа алготрейдинга с бэктестером и загрузкой данных.')
    
    # Добавляем параметр --loaddata
    parser.add_argument(
        '--loaddata',
        action='store_true',  # Флаг (без значения)
        help='Загрузить или обновить исторические данные перед запуском бэктеста'
    )
    
    
    
    args = parser.parse_args()
    
    # Загружаем и валидируем конфигурацию
    # ====================================================
    from src.config.config import config

    # Логирование
    # ====================================================
    from src.utils.logger import get_logger
    logger = get_logger(__name__)
    logger.info("Конфигурация успешно загружена и прошла валидацию.")
    # Проверяем параметры
    if args.loaddata:
        logger.info("Загрузка и обновление исторических данных...")
        from src.logical.data_fetcher.data_pipeline import run_data_update_pipeline
        run_data_update_pipeline()
        logger.info("Загрузка и обновление исторических данных завершены.")
    
    logger.info("Запуск бэктестера с локальными данными...")
    from src.logical.backtester.backtester import run_local_backtest
    run_local_backtest()
    logger.info("Бэктестер завершил работу.")
    


# Точка входа
if __name__ == "__main__":
    main()    