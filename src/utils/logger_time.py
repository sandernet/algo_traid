import time
from datetime import datetime

# Логирование
# ====================================================
from src.utils.logger import get_logger
logger = get_logger(__name__)


class LoggingTimer:
    """
    Менеджер контекста для логирования времени выполнения задачи.
    Записывает время начала, конца и общее затраченное время.
    """
    def __init__(self, task_name="Задача"):
        self.task_name = task_name

    def __enter__(self):
        # 1. Фиксация и запись времени НАЧАЛА
        self.start_time_raw = time.time()
        self.start_datetime = datetime.now()

        logger.info(f"[🟢🟢🟢] {self.task_name} / {self.start_datetime.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # 2. Фиксация и запись времени КОНЦА
        self.end_time_raw = time.time()
        self.end_datetime = datetime.now()

        # 3. Расчет и запись ЗАТРАЧЕННОГО ВРЕМЕНИ
        execution_time = self.end_time_raw - self.start_time_raw

        logger.info(f"[🔴🔴🔴] {self.task_name} / Затрачено времени: {execution_time:.4f} секунд / {self.end_datetime.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}")
        
        # Возвращает False, чтобы не подавлять возможные исключения
        return False