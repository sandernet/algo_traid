from pybit.unified_trading import HTTP

# Создаем сессию с API
def connect_bybit(config):
    session = HTTP(
        api_key=config.API_KEY,
        api_secret=config.API_SECRET,
        testnet=config.TESTNET,
        )
    return session

    
