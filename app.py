import os
from src.logical.loading_data import get_kline_data_timeframe

# Логирование 
import logging
from src.utils.logger import setup_logging


# Загружаем настройки приложения 
# ====================================================
from config import TestingConfig, ProductionConfig
# Определяем окружение по переменной окружения APP_ENV
env = os.getenv("APP_ENV")

# Выбор класса конфигурации в зависимости от окружения
if env == "production":
    config = ProductionConfig
else:
    config = TestingConfig
# ====================================================


# Настройка логирования
setup_logging()
# Создание логгера
logger = logging.getLogger(__name__)



# # Функция получения данных и запуска вычислений по стратегии
# def run_strategy_and_graphics():
#     try:
#         # Расчет стратегии 
#         from strategy.strategy import run_strategy
#         minor_kline_data, work_kline_data, senior_kline_data, vpvr_data = run_strategy(config)
        
#         # ========================================
#         # Вовд графика в браузер
#         # Если в конфигураторе указано показывать график
#         if config.GRAFIC_SEE:
#             from graphics import chart_plotly
#             logger.info("Запуск построения графика")
#             chart_plotly(minor_kline_data, work_kline_data, senior_kline_data, vpvr_data, config)
#     except Exception as e:
#         print(f"Ошибка проверки данных: {e}")

 

# Асинхронная функция для основного процесса
def main():
    logger.info("Запуск основного процесса")

    data = get_kline_data_timeframe()
    logger.info(data)
    logger.info("Завершение основного процесса")


if __name__ == "__main__":
    main()
    
    
    # while True:
    #     print("Выберите действие:")
    #     print("1. Запустить загрузку данных с ByBit")
    #     print("2. Запуск стратегии Mozart")
    #     print("3. Запуск программы с ТГ ботом")
    #     print("4. Запуск обучения AI")
    #     print("0. Выйти")
        
    #     # Получаем выбор от пользователя
    #     choice = input("Введите номер действия: ")

    #     if choice == "1":
    #         # Загрузка и сохранение данных с биржи в файл
    #         print("Запуск Загрузки данных.....")
    #         from get_dataBybit.get.index import save_files_in_csv
    #         save_files_in_csv()
    #         break
            
    #     elif choice == "2":
    #         print("Запуск стратегии Mozart")
    #         run_strategy_and_graphics()
    #         break
        
    #     elif choice == "3":
    #         print("Запуск программы с ТГ ботом")
    #         asyncio.run(main()) 
    #     elif choice == "4":
    #         print("Запуск обучения AI....")
    #         from nn_ai.nn_training import training 
    #         training()
    #     elif choice == "0":
    #         print("Выход из программы.")
    #         break  # Завершение цикла
    #     else:
    #         print("Некорректный выбор. Попробуйте снова.")
        
    #     print()  # Пустая строка для разделения вывода