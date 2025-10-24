"""
Модуль logging поддерживает несколько уровней логирования:

DEBUG: Подробная информация, обычно интересная только для разработки.
INFO: Подтверждение того, что все работает как ожидается.
WARNING: Указание на то, что что-то может пойти не так.
ERROR: Сообщение об ошибке, которая произошла.
CRITICAL: Очень серьезная ошибка, которая может привести к остановке программы.

"""
import logging
import sys

def setup_logging(log_file='app.log', cfg_level="INFO"):
    
 # Преобразуем строковый уровень в константу logging
    level_map = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
    }
    level = level_map.get(cfg_level.upper(), logging.INFO)
    
    
    # Создаём обработчики с явной кодировкой UTF-8
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    console_handler = logging.StreamHandler(sys.stdout)  # Явно stdout для предсказуемости

    # Формат сообщений
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # Настройка логирования
    logging.basicConfig(
        level=level,  # Уровень логирования
        handlers=[file_handler, console_handler],
        force=True  # Перезаписывает предыдущую конфигурацию (Python 3.8+)
    )


"""
# Пример логирования
logging.debug("Это отладочное сообщение")
logging.info("Это информационное сообщение")
logging.warning("Это предупреждающее сообщение")
logging.error("Это сообщение об ошибке")
logging.critical("Это критическое сообщение")
"""

