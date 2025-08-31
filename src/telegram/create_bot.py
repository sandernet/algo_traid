from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand, BotCommandScopeDefault

from config import Config
cfg = Config()

# получаем список администраторов из .env
admins = [int(admin_id) for admin_id in cfg.TG_ADMINS.split(',')]

# инициируем объект бота, передавая ему parse_mode=ParseMode.HTML по умолчанию
tg_bot = Bot(token=cfg.TG_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

# инициируем объект бота
dp = Dispatcher()

# Функция, которая настроит командное меню (дефолтное для всех пользователей)
async def set_commands(tg_bot):
    commands = [BotCommand(command='start', description='Старт'),
                BotCommand(command='profile', description='Мой профиль')]
    await tg_bot.set_my_commands(commands, BotCommandScopeDefault())


# Функция, которая выполнится когда бот запустится
async def start_bot():
   
    await set_commands(tg_bot)
    count_users = 0 #await get_all_users(count=True)
    try:
        for admin_id in admins:
            await tg_bot.send_message(admin_id, f'Я запущен🥳.')
    except:
        pass


# # Функция, которая выполнится когда бот завершит свою работу
# async def stop_bot(cfg):
#     try:
#         for admin_id in cfg.admins:
#             await tg_bot.send_message(admin_id, 'Бот остановлен. За что?😔')
#     except:
#         pass
    
