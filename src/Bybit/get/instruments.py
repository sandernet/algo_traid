def get_instruments_info(session, category, symbol, logger):
    """
    Получение информации с биржи по заданному инструменту
    """
    try:
        data = session.get_instruments_info(
            category    = category,
            symbol      = symbol,
    )
        tickSize = data['result']['list'][0]
        return tickSize
    except Exception as e:
        logger.error(f"Ошибка при получении данных: {e}")
        return {}
    
