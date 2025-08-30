# from src.Bybit.get.get_datatime import Preparation_period
# # =================================================
# # Вырезать
# import pandas as pd    
# # Берем настройки из config
# from config import Config
# config = Config()

# # создаем сессию подключения 
# from src.Bybit.client import Connector_Bybit
# session = Connector_Bybit(config)
# from datetime import datetime
# # =================================================



# # Логирование 
# import logging
# logger = logging.getLogger(__name__)


# start_datetime, end_datetime    = Preparation_period()


# # def date_preparation():
    
    
# def get_kline_data_all_timeframe(config):
    
   
#     # Временные метки
#     import time
#     current_time = int(time.time() * 1000)  # Текущее время в миллисекундах
#     one_year_ago = current_time - (365*2 * 24 * 60 * 60 * 1000)  # Время год назад
    
#     start_time = one_year_ago
#     end_time = current_time
    
    
#     work_kline_data = pd.DataFrame()
#     # Цикл для пагинации и сбора данных
#     while start_time < current_time:
        
#         print("===========================================")
#         print(F"start_time = {datetime.fromtimestamp(start_time / 1000)}")
#         print(F"current_time = {datetime.fromtimestamp(current_time / 1000)}")
#         print(F"end_time = {datetime.fromtimestamp(end_time / 1000)}")
#         print("===========================================")
        
            
#         df2 = get_klines(config.CATEGORY, config.SYMBOL, config.MINOR_TIME_FRAME, start_time, end_time, config.LIMIT)
#         if df2.empty:
#             break
#         df2['Time'] = pd.to_datetime(df2['Time'], unit='ms')
#         work_kline_data = pd.concat([work_kline_data, df2], axis=0, ignore_index=False)
#         print(work_kline_data)
#         print(df2)
        
#         print(work_kline_data.dtypes)
#         # Переводим в миллисекунды
#         print(int(work_kline_data.iloc[-1, 6]))
#         print(datetime.fromtimestamp(int(work_kline_data.iloc[-1, 6]) / 1000))

        
#         # Обновляем start_time для следующего запроса
#         last_timestamp = int(work_kline_data.iloc[-1, 6])  # Последний таймстамп
#         print(F"last_timestamp = {datetime.fromtimestamp(last_timestamp / 1000)}")
        
#         # Преобразуем миллисекунды в datetime
#         time_dt = pd.to_datetime(end_time, unit='ms')    
#         # Прибавляем 15000 минут
#         time_dt_plus_15000min = time_dt - pd.Timedelta(minutes=15000)

# # Преобразуем обратно в миллисекунды
#         time_ms_plus_15000min = int(time_dt_plus_15000min.timestamp() * 1000)

#         end_time = time_ms_plus_15000min #last_timestamp + 900000  # Переход на следующую свечу
        
        
        
        
    
#     # work_kline_data['Time'] = pd.to_datetime(work_kline_data['Time'], unit='ms')
#     work_kline_data.to_csv('work_kline_data.csv', index=False)
    
#     print('ОК!!!')
#     # return minor_kline_data, work_kline_data, senior_kline_data 
    

# # Функция для получения данных свечей (K-line)
# def get_klines(category, symbol, interval, start_time, end_time,  limit = 200):

#     kline_data = session.get_kline(
#         category    = category,  # Выбор типа контракта (inverse, linear, etc.)
#         symbol      = symbol,       # Символ, например BTCUSD
#         interval    = interval,   # Интервал в минутах (1,3,5,15,30,60,120,240,360,720,D,M,W)
#         start       = start_time,    # Начальное время в миллисекундах
#         end         = end_time,
#         limit       = limit
#     )
#     kline_data = kline_data["result"]["list"]
#     kline_data = pd.DataFrame(kline_data)
#     if not kline_data.empty:
#         kline_data = kline_data.iloc[:,:6]
#         kline_data.columns = ['Time', 'Open', 'High', 'Low', 'Close', 'Volume']
#         kline_data['Time_ms'] = kline_data['Time']
#     else:
#         print("Data is empty!")
        
#     return kline_data




# # def run_strategy(config):
    
# #     # Получаем данные с биржи
# #     minor_kline_data, work_kline_data, senior_kline_data = get_kline_data_all_timeframe(config)
    
# #             # Вывод данных
# #     if not minor_kline_data.empty and not work_kline_data.empty and not senior_kline_data.empty:
# #         # print("Данные получены приступаем к анализу" + "\033[92m\u2713\033[0m")
# #         logger.info("Данные получены приступаем к анализу")

# #     else:
# #         # print("Не удалось получить данные по свечам.")
# #         logger.info("Не удалось получить данные по свечам.")
# #         # Нужно завершить работу программы и отправить сообщение в TG
    
    
# #     # Рассчитываем стратегию
# #     # ****************************************
# #     # 1 лекция добавляем данные в массив с ценами
# #     # Определение тренда на высшем timeframe
# #     # 
# #     senior_kline_data = strategy_extremes(senior_kline_data)
# #     print(senior_kline_data)
    
    
# #     work_kline_data = strategy_extremes(senior_kline_data)
# #     print(work_kline_data)
# #     # ****************************************

# #     # ****************************************
# #     # Вторая лекция # 2 
# #     # Расчет VPVR
# #     vpvr_data =  all_lecture_2(work_kline_data, config, float(tickSize))
# #     # ****************************************
# #     return minor_kline_data, work_kline_data, senior_kline_data, vpvr_data


