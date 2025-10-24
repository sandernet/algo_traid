import logging
from src.utils.logger import setup_logging
setup_logging()
logger = logging.getLogger(__name__)


def openOrder(session, category, symbol, side, qty, orderType, orderLinkId):
    # Запрос данных по свечам
    try:
        order_info = session.place_order(
            category=category,
            symbol=symbol,
            side=side,
            orderType=orderType,
            qty=qty,
            marketUnit = "quoteCoin",
            # timeInForce="PostOnly",
            orderLinkId=orderLinkId,
            # isLeverage=0,
            # orderFilter="Order",
        )
        return order_info
    except Exception as e:
        print(f"Ошибка при получении данных: {e}")
        return None
    
# --- . Функция: получения истории ордеров с биржи ---
def get_order_history(session, category, symbol, orderLinkId, limit=50):
    lst = []
    try:
        response = session.get_order_history(
            category=category, 
            symbol=symbol, 
            limit=limit, 
            orderLinkId=orderLinkId
            )
        
        # Проверяем, что response — словарь
        if not isinstance(response, dict):
            logger.error(f"   ❌ Неожиданный формат ответа: {type(response)}")
            return lst
         # Достаём "result"
        result = response.get("result")
        if not isinstance(result, dict):
            logger.error(f"   ❌ В ответе нет корректного 'result': {response}")
            return lst

        # Достаём список ордеров
        lst = result.get("list", [])
        if not isinstance(lst, list) or not lst:
            logger.info(f"   ❌ В 'result' списк 'list' пустой:")
            return lst
        
        return lst
    except Exception as e:
        logger.error(f"Ошибка при получении истории ордеров: {e}")
        return lst
    