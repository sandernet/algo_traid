from get_dataBybit.get.index import get_kline_data_all_timeframe
from strategy.lecture_1 import strategy_extremes
import pandas as pd

# VPVR
from strategy.lecture_2 import all_lecture_2

# =================================================
# Библиотека для вывода в консоль форматированного DataFrame 
from tabulate import tabulate
import ta



# Логирование 
import logging
logger = logging.getLogger(__name__)
   

def run_strategy(config):
    
    # # Получаем данные с биржи
    # minor_kline_data, work_kline_data, senior_kline_data, tickSize = get_kline_data_all_timeframe()
    
    #         # Вывод данных
    # if not minor_kline_data.empty and not work_kline_data.empty and not senior_kline_data.empty:
    #     # print("Данные получены приступаем к анализу" + "\033[92m\u2713\033[0m")
    #     logger.info("Данные получены приступаем к анализу")

    # else:
    #     # print("Не удалось получить данные по свечам.")
    #     logger.info("Не удалось получить данные по свечам.")
    #     # Нужно завершить работу программы и отправить сообщение в TG
    
    
    # Рассчитываем стратегию
    # ****************************************
    # 1 лекция добавляем данные в массив с ценами
    # Определение тренда на высшем timeframe
    # 
    # senior_kline_data = strategy_extremes(work_kline_data)
    # print(senior_kline_data)
    
    
    work_kline_data = pd.read_csv('work_kline_data_full.csv', encoding='utf-8')
    print(work_kline_data)
    
    work_kline_data = strategy_extremes(work_kline_data)
    
    # Заполняем None значения предыдущими непропущенными значениями
    work_kline_data['extremum'] = work_kline_data['extremum'].fillna(0)
    work_kline_data['extremum_trend'] = work_kline_data['extremum_trend'].fillna(0)
    
    
    # # Заполняем None значения предыдущими непропущенными значениями
    # work_kline_data['extremum_trend'] = work_kline_data['extremum_trend'].ffill()
    work_kline_data['start_trend'] = work_kline_data['start_trend'].ffill()
    
    
    
    # Добавляем RSI с периодом 14
    work_kline_data['RSI'] = ta.momentum.rsi(work_kline_data['Close'], window=14)    

    # Добавляем стохастический осциллятор
    stoch = ta.momentum.StochasticOscillator(
        high=work_kline_data['High'], low=work_kline_data['Low'], close=work_kline_data['Close'], window=14, smooth_window=3
    )
    work_kline_data['STOCH_%K'] = stoch.stoch()
    work_kline_data['STOCH_%D'] = stoch.stoch_signal()

    # Добавляем Bollinger Bands
    bb = ta.volatility.BollingerBands(close=work_kline_data['Close'], window=20, window_dev=2)
    work_kline_data['BB_Middle'] = bb.bollinger_mavg()
    work_kline_data['BB_Upper'] = bb.bollinger_hband()
    work_kline_data['BB_Lower'] = bb.bollinger_lband()


    del work_kline_data['extremum']
    print(tabulate(work_kline_data, headers='keys', tablefmt='grid'))
    work_kline_data.to_csv('work__data.csv', index=True, encoding='utf-8')

    
    
    # ****************************************

    # ****************************************
    # Вторая лекция # 2 
    # Расчет VPVR
    # vpvr_data =  all_lecture_2(work_kline_data, config, float(tickSize))
    # ****************************************
    # return minor_kline_data, work_kline_data, senior_kline_data, vpvr_data
