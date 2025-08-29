import pandas as pd


def get_klines_strategy(session, category, symbol, interval, start_time, end_time, limit, reverse = False):

    kline_data = get_klines_bybit(session, category, symbol, interval, start_time, end_time, limit)
    kline_data = preparation_data(kline_data) 
    if reverse :
        kline_data = revers(kline_data)
    return kline_data



# Функция для получения данных из Bybit
# session - сессия подключения
# category - тип контракта (inverse, linear)
# symbol - символ, например BTCUSD
# interval - интервал в минутах (1,3,5,15,30,60,120,240,360,720,D,M,W)
# start_time - начальное время в миллисекундах
# end_time - конечное время в миллисекундах
def get_klines_bybit(session, category, symbol, interval, start_time, end_time, limit = 1000):
    # Запрос данных по свечам
    try:
        kline_data = session.get_kline(
            category=category,  # Выбор типа контракта (inverse, linear)
            symbol=symbol,       # Символ, например BTCUSD
            interval=interval,   # Интервал в минутах (1,3,5,15,30,60,120,240,360,720,D,M,W)
            start=start_time,    # Начальное время в миллисекундах
            end=end_time,         # Конечное время в миллисекундах
            limit = limit
        )
        return kline_data
    except Exception as e:
        print(f"Ошибка при получении данных: {e}")
        return None
    
    
# Функция для подготовки данных 
def preparation_data(kline_data):
    kline_data = kline_data["result"]["list"]
    kline_data = pd.DataFrame(kline_data)
    kline_data = kline_data.iloc[:,:6]
    kline_data.columns = ['DateTime', 'Open', 'High', 'Low', 'Close', 'Volume'] 
    # Проверка и приведение данных к числовому типу
    kline_data[['Open', 'High', 'Low', 'Close', 'Volume']] = kline_data[['Open', 'High', 'Low', 'Close', 'Volume']].apply(pd.to_numeric, errors='coerce').astype(float)
    # Убедимся, что колонка 'Date' является индексом, что требуется для mplfinance
    kline_data.set_index('DateTime', inplace=True)
    kline_data.index = pd.to_datetime(kline_data.index.astype(float), unit='ms')
    return kline_data


# Функция для инвертирования данных
def revers(kline_data):
    # Инвертируем данные
    return kline_data.iloc[::-1]