from get_dataBybit.get.get_datatime import preparation_date
from get_dataBybit.run_get_data import run_get_data
from get_dataBybit.get.get_instruments_info import instruments_info

# Берем настройки из config
from config import Config
config = Config()

# создаем сессию подключения 
from get_dataBybit.config import connect_bybit
session = connect_bybit(config)



# Формирование дат периода загрузки
start_datetime, end_datetime    = preparation_date()

# Получение данных с биржи по 3 timeframes    
def get_kline_data_all_timeframe():
    
    minor_kline_data = run_get_data(config.MINOR_TIME_FRAME, start_datetime, end_datetime,  config.LIMIT) 
    work_kline_data = run_get_data(config.MINOR_TIME_FRAME, start_datetime, end_datetime,  config.LIMIT)
    senior_kline_data = run_get_data(config.MINOR_TIME_FRAME, start_datetime, end_datetime,  config.LIMIT)
    tickSize = instruments_info(session, config=config)
    
    
    return minor_kline_data, work_kline_data, senior_kline_data, tickSize

# сохранение dataFrame в файлы
def save_files_in_csv():
    # Получаем данные с биржи
    minor_kline_data, work_kline_data, senior_kline_data, tickSize = get_kline_data_all_timeframe()
    
    minor_kline_data.to_csv('minor_kline_data.csv', index=True, encoding='utf-8')
    work_kline_data.to_csv('work_kline_data.csv', index=True, encoding='utf-8')
    senior_kline_data.to_csv('senior_kline_data.csv', index=True, encoding='utf-8')
    print(f'Файлы сохранены')
    