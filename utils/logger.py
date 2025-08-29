"""
Модуль logging поддерживает несколько уровней логирования:

DEBUG: Подробная информация, обычно интересная только для разработки.
INFO: Подтверждение того, что все работает как ожидается.
WARNING: Указание на то, что что-то может пойти не так.
ERROR: Сообщение об ошибке, которая произошла.
CRITICAL: Очень серьезная ошибка, которая может привести к остановке программы.

"""
import logging

def setup_logging(log_file='app.log', level=logging.INFO):
    # Настройка логирования
    logging.basicConfig(
        level=level,  # Уровень логирования
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',  # Формат сообщений
        handlers=[
            logging.FileHandler(log_file),  # Логи в файл
            logging.StreamHandler()  # Логи в консоль
        ]
    )


"""
# Пример логирования
logging.debug("Это отладочное сообщение")
logging.info("Это информационное сообщение")
logging.warning("Это предупреждающее сообщение")
logging.error("Это сообщение об ошибке")
logging.critical("Это критическое сообщение")
"""

