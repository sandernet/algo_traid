from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardRemove

from src.telegram.keyboards.kbs_users import kbs_main_menu
from config import Config

router = Router()  # [1]
config = Config()



@router.message(Command("start"))  # [2]
async def cmd_start(message: Message):
    await message.answer(
        f"Привет криптаны.",
        reply_markup=kbs_main_menu()
    )

@router.message(F.text == "Кнопка 1")
async def answer_yes(message: Message):
    await message.answer(
        "Кнопка 1...",
        reply_markup=kbs_main_menu()
    )
        
@router.message(F.text == "Посмотреть настрйки торговли")
async def answer_no(message: Message):
    
    text = (f'👉 Текущая пара: <code><b>{config.SYMBOL}</b></code>\n'
            f'👥 Установленный рабочий таймфрейм: <b>{config.TIMEFRAME}</b>\n'
            f'🚀 Количество свечей для анализа {config.LIMIT}')
    await message.answer(
        text,
        reply_markup=kbs_main_menu()
    )