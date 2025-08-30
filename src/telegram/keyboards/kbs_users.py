# from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

# def main_menu():
#     return ReplyKeyboardMarkup(
#         keyboard=[
#             [KeyboardButton(text="Запрос баланса")],
#             [KeyboardButton(text="Текущий курс")],
#         ],
#         resize_keyboard=True
#     )


from aiogram.types import ReplyKeyboardMarkup
from aiogram.utils.keyboard import ReplyKeyboardBuilder

def kbs_main_menu() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardBuilder()
    kb.button(text="Получить баланс")
    kb.button(text="Посмотреть настройки бота")
    kb.button(text="И еще что-то...")
    kb.adjust(2)
    return kb.as_markup(resize_keyboard=True)