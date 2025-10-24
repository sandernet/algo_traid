from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.types import Message, ChatMemberUpdated

from src.telegram.keyboards.kbs_users import kbs_main_menu
from src.telegram.create_bot import tg_bot
import src.config.config as config

# подключаем логику 
from src.logical.hendler_info import get_balance_info


router = Router()  # [1]
cfg = config.get_config()


# стартовое приветствие 
@router.message(Command("start"))  # [2]
async def cmd_start(message: Message):
    await message.answer(
        f"Привет мой новый друг.",
        reply_markup=kbs_main_menu()


    )

@router.message(F.text == "Текущие показатели индикатора")
async def answer_yes(update: ChatMemberUpdated, message: Message):
    chat_id_group = update.chat.id
    chat_title = update.chat.title
    await message.answer(
        "Данная функция в разработке:\n\n",
        reply_markup=kbs_main_menu()
    )

       
@router.message(F.text == "Баланс на бирже")
async def balance_info(message: Message):
    text = get_balance_info()
    await message.answer(
        text,
        reply_markup=kbs_main_menu()
    )
        
@router.message(F.text == "Посмотреть настрйки торговли")
async def answer_no(message: Message):
    
    coins = cfg.get("coins", [])
    text = ""
    if coins:  # проверяет и на None, и на пустоту
        # Перебираем список монет
        for coin in coins:
            symbol = coin.get("symbol", "N/A")
            timeframe = coin.get("timeframe", "N/A")
            auto_trading = coin.get("auto_trading", False)
            start_deposit_usdt = coin.get("start_deposit_usdt", 0)
            orderType = coin.get("orderType", "Market")
            
            text += (f'👉 Текущая пара: <code><b>{symbol}</b></code>\n'
                    f'👥 Установленный рабочий таймфрейм: <b>{timeframe}</b>\n'
                    f'🚀 Вид торговли: {"Автоматическая" if auto_trading else "Ручная"}\n'
                    f'💰 Стартовый депозит USDT: <b>{start_deposit_usdt}</b>\n'
                    f'⚙️ Тип ордера: <b>{orderType}</b>\n\n')
            
    
    await message.answer(
        text,
        reply_markup=kbs_main_menu()
    )
    

# Обработчик события добавления бота в группу
@router.my_chat_member()
async def on_bot_added_to_group(update: ChatMemberUpdated):
    admin = cfg["telegram"]["admin"]
    if update.new_chat_member.status == "member":
        chat_id_group = update.chat.id
        chat_title = update.chat.title
        
        # Отправляем ID группы в ЛС создателю
        await tg_bot.send_message(chat_id=admin, text=f"Бота добавили в группу:\nID: {chat_id_group}\nНазвание: {chat_title}")
        
        
      
# Обработчик всех сообщений в группах
@router.message()
async def handle_group_messages(message: types.Message):
    if message.chat.type in ["group", "supergroup"]:
        chat_id = message.chat.id
        chat_title = message.chat.title
        # Отправляем ID группы в ЛС создателю
        await tg_bot.send_message(
            chat_id=chat_id,  # ID администратора
            text=f"__",
            reply_markup=kbs_main_menu()
        )