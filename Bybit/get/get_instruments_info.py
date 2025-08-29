"""Получение информации с биржи по заданному инструменту"""
# print(data['result']['list'][0]['priceFilter']['tickSize']) получение размера тикета для расчета VPVR

def instruments_info(session, config):
    try:
        data = session.get_instruments_info(
            category    = config.CATEGORY,
            symbol      = config.SYMBOL,
    )
        tickSize = data['result']['list'][0]['priceFilter']['tickSize']
        return tickSize
    except Exception as e:
        print(f"Ошибка при получении данных: {e}")
        return None
    
