import src.config.config as config
from pybit.unified_trading import HTTP

# Создаем коннектор с Bybit-API
def Connector_Bybit():

    cfg = config.load_config("config.json")

    session = HTTP(
        api_key=cfg["exchange"]["api_key"],
        api_secret=cfg["exchange"]["api_secret"],
        testnet=cfg["exchange"]["testnet"],
        demo=cfg["exchange"].get("demo", False)
        )
    return session