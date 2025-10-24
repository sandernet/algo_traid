# import asyncio
# Загружаем настройки приложения 
# ====================================================
from src.config.config import ConfigManager, ConfigValidationError
import yaml

# Создание синглтона для доступа к конфигурации
try:
    config = ConfigManager()
except (FileNotFoundError, yaml.YAMLError, ConfigValidationError) as e:
    # Важно: При ошибке валидации или загрузки, программа должна быть остановлена
    print(f"\nFATAL ERROR: {e}")
    # Вы можете добавить здесь os._exit(1) для принудительной остановки, 
    # если это главный скрипт
    raise SystemExit(1)


# from src.telegram.create_bot import tg_bot
    
# # ====================================================
# # Логирование 
# import logging
# from src.utils.logger import setup_logging
# # Настройка логирования
# setup_logging(cfg.get("logger", {}).get("log_file", "app.log"), cfg.get("logger", {}).get("log_level", "INFO"))
# # Создание логгера
# logger = logging.getLogger(__name__)
# # ====================================================



# from src.schedulers.schedulers import start_scheduler
# from src.logical.trading import launch_of_trading

# _main_loop = None

# def make_trading_job(loop, cfg):
#     def job():
#         # Эта функция будет вызвана из другого потока!
#         async def _run():
#             await launch_of_trading(cfg, tg_bot)
#         # Безопасно отправляем корутину в event loop из другого потока
#         loop.call_soon_threadsafe(asyncio.create_task, _run())
#     return job

# # Асинхронная функция для основного процесса
# async def main():
#     logger.warning("def main - "+"Запуск приложения")
    
#     # Запуск планировщика-------------------------
#     logger.info("Запуск планировщика")
#     global _main_loop
#     _main_loop = asyncio.get_running_loop()
#     start_scheduler(make_trading_job(_main_loop, cfg))

    
#     cfg_telegram = cfg.get("telegram", {})
#     if not cfg_telegram.get("token", "").strip():
#         logger.warning("Токен Telegram не указан — бот не запущен")
#         # Если бот не нужен, тогда держим программу в работе вручную
#         await asyncio.Event().wait()
#         return
        
#     # Запуск Telegram-бота-------------------------
#     logger.info("Запуск Telegram-бота") 
#     # Подключение модулей бота
#     from src.telegram.create_bot import tg_bot, dp, start_bot
#     from src.telegram.handlers import user_router 
#     # Регистрируем маршруты (обработчики)
#     dp.include_routers(user_router.router)
#     # регистрация функций
#     dp.startup.register(start_bot)
#     # запуск бота в режиме long polling при запуске бот очищает все обновления, которые были за его моменты бездействия
#     try:
#         await tg_bot.delete_webhook(drop_pending_updates=True)
#         await dp.start_polling(tg_bot, allowed_updates=dp.resolve_used_update_types())
#     finally:
#         await tg_bot.session.close()


# Точка входа
# if __name__ == "__main__":
#     asyncio.run(main())

def main():
    print("Приложение запущено")
    # Получение настроек Биржи
    exchange_id = config.get_setting("EXCHANGE_SETTINGS", "EXCHANGE_ID")
    symbol = config.get_setting("EXCHANGE_SETTINGS", "SYMBOL")
    
    print(f"Биржа: {exchange_id}, Пара: {symbol}")
    
    # Здесь можно добавить основной код приложения
    # Например, запуск бота или других сервисов
    

# Точка входа
if __name__ == "__main__":
    main()    