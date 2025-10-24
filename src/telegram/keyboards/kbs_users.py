from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Запрос баланса")],
            [KeyboardButton(text="Текущий курс")],
        ],
        resize_keyboard=True
    )


from aiogram.types import ReplyKeyboardMarkup
from aiogram.utils.keyboard import ReplyKeyboardBuilder

def kbs_main_menu() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardBuilder()
    kb.button(text="Текущие показатели индикатора")
    kb.button(text="Посмотреть настрйки торговли")
    kb.button(text="Баланс на бирже")
    kb.adjust(1)
    return kb.as_markup(resize_keyboard=True)