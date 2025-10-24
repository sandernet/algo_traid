from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand, BotCommandScopeDefault

import src.config.config as config

cfg = config.get_config()

# инициируем объект бота, передавая ему parse_mode=ParseMode.HTML по умолчанию
tg_bot = Bot(token=cfg["telegram"]["token"], default=DefaultBotProperties(parse_mode=ParseMode.HTML))

# инициируем объект бота
dp = Dispatcher()

# Функция, которая настроит командное меню (дефолтное для всех пользователей)
async def set_commands(tg_bot):
    commands = [BotCommand(command='start', description='Старт'),
                BotCommand(command='profile', description='Мой профиль')]
    await tg_bot.set_my_commands(commands, BotCommandScopeDefault())


# Функция, которая выполнится когда бот запустится
async def start_bot():
    # получаем список администраторов из .env
    admin = cfg["telegram"]["admin"]
    # channal = cfg["telegram"]["channel"]
    
    await set_commands(tg_bot)

    try:
        await tg_bot.send_message(admin, f'Я запущен🥳.')
        # await tg_bot.send_message(channal, f'Я запущен🥳.')
    except:
        pass


 