import argparse
import os

# ====================================================
# Основная функция
# ====================================================
def main():
    from src.config.config import config
    # ------------------------------------------
    # аргументы командной строки
    parser = argparse.ArgumentParser(description='Программа алготрейдинга с бэктестером и загрузкой данных.')
    
    # Добавляем параметр --loaddata
    parser.add_argument(
        '--ldata',
        action='store_true',  # Флаг (без значения)
        help='Загрузить или обновить исторические данные c биржи'
    )

    # Добавляем параметр --backtester
    data_dir = config.get_setting("MODE_SETTINGS", "DATA_DIR")
    parser.add_argument(
        '--btest',
        action='store_true',  # Флаг (без значения)
        help=f'Запустить бэктестер с локальными данными из директории {data_dir}'
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
    if args.ldata:
        logger.info("Загрузка и обновление исторических данных...")
        from src.logical.data_fetcher.data_pipeline import run_data_update_pipeline
        run_data_update_pipeline()
        logger.info("Загрузка и обновление исторических данных завершены.")
    
    # Проверяем параметры
    if args.btest:
        # 1. Проверяем есть ли данные для бэктеста
        if not os.path.exists(data_dir+"csv_files"):
            logger.info(f"Нет данных для бэктеста.")
            logger.info("Загружаем данные с биржи...")
            from src.logical.data_fetcher.data_pipeline import run_data_update_pipeline
            run_data_update_pipeline()
            logger.info("Загрузка данных с биржи завершена.")
            
        # 2. Запуск бэктестера
        logger.info(f"Запуск бэктестера с локальными данными из {data_dir}...")
        from src.logical.backtester.backtester import run_local_backtest
        run_local_backtest()
        logger.info("Бэктестер завершил работу.")
    

# Точка входа
if __name__ == "__main__":
    main()    