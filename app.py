import os
import asyncio

from src.schedulers.schedulers import start_scheduler
from src.logical.starting import starting

# Логирование 
import logging
from src.utils.logger import setup_logging

# Подключение Telegram-бота
from src.telegram.create_bot import tg_bot, dp, start_bot
from src.telegram.handlers import user_router  #, different_types


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


# Асинхронная функция для основного процесса
async def main():
   
#    # Запуск планировщика-------------------------
#     logger.info("Запуск планировщика")
#     start_scheduler(starting)


    #  Запускаем начальную функцию
    starting()
    
    # Запуск Telegram-бота-------------------------
    logger.info("Зпуск Telegram-бота")
    # Регистрируем маршруты (обработчики)
    dp.include_routers(user_router.router)
    # регистрация функций
    dp.startup.register(start_bot)
    # dp.shutdown.register(stop_bot)
    # запуск бота в режиме long polling при запуске бот очищает все обновления, которые были за его моменты бездействия
    try:
        await tg_bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(tg_bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await tg_bot.session.close()

    

if __name__ == "__main__":
    asyncio.run(main())
    