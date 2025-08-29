from pybit.unified_trading import HTTP

# Создаем коннектор с Bybit-API
def Connector_Bybit(config):
    session = HTTP(
        api_key=config.API_KEY,
        api_secret=config.API_SECRET,
        testnet=config.TESTNET,
        )
    return session

    
