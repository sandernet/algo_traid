import src.config.config as config

import logging
from src.utils.logger import setup_logging
setup_logging()
logger = logging.getLogger(__name__)

# создаем сессию подключения 
from src.bybit.client import Connector_Bybit
session = Connector_Bybit()

cfg = config.get_config()

# --- . Функция: Получение баланса ---
def get_balance(coin = None):
    
    coins_balance = {}
    
    """Получает доступный баланс для указанной монеты."""
    try:
        if coin == None:
            response = session.get_wallet_balance(accountType="UNIFIED")
        else:
            response = session.get_wallet_balance(accountType="UNIFIED", coin=coin)
        
        # Проверяем, что response — словарь
        if not isinstance(response, dict):
            print(f"   ❌ Неожиданный формат ответа: {type(response)}")
            return coins_balance

        # Достаём "result"
        result = response.get("result")
        if not isinstance(result, dict):
            print(f"   ❌ В ответе нет корректного 'result': {response}")
            return coins_balance

        # Достаём список балансов
        lst = result.get("list", [])
        if not isinstance(lst, list) or not lst:
            print(f"   ❌ В 'result' нет списка 'list': {result}")
            return coins_balance
        
        
        
        balance_list = []
        if lst:
            # Ищем монету в списке балансов
            coins_balance["Total(usd)"] = float(lst[0].get("totalEquity"))
            balance_list = lst[0].get('coin', [])

        for b in balance_list:
            coins_balance[b['coin']] = {
                'usdValue': float(b['usdValue']),
                'equity': float(b['equity'])
            }
        
        return coins_balance
        
    except Exception as e:
        print(f"   ❌ Ошибка при получении баланса {coin}: {e}")
        return coins_balance
   