import os
from dotenv import load_dotenv
load_dotenv()  # Загрузка переменных окружения из .env

class Config:
    """Базовый класс конфигурации с общими настройками для всех окружений."""
    CATEGORY            =   "spot"  # Выбор типа контракта (inverse, linear, etc.)
    SYMBOL              =   "BTCUSDT"                   # Выбор торгового символа
    TIMEFRAME       =   5
    LIMIT           =   1000  # количество баров  максимально 1000
    TESTNET         =   False                     # True means your API keys were generated on testnet.bybit.com
    START_DATETIME  =   "01-01-2024"                     # Начало периода загрузки данных (в формате DD-MM-YYYY) или None
    END_DATETIME    =   "01-01-2025"                     # Конец периода загрузки данных (в формате DD-MM-YYYY) или None
   

    INTERVAL_DAY        =   365 # INTERVAL_DAY
    # таймфраймы для получения данных
    MINOR_TIME_FRAME    =   5                          # Младший timeframe
    WORK_TIMEFRAME      =   15                          # рабочий timeframe 
    SENIOR_TIME_FRAME   =   30                         # Старший timeframe
    
    # Конфигурация графиков 
    SCROLLZOOM = {'scrollZoom': True,
                  'modeBarButtonsToRemove': ['zoom', 'select']
                  }
    # Лекция №2 настройки VPVR индикатора
    # количество свечей строк в индикаторе 
    ROW_SIZE            = 168 # на 1 час 4 часовом графике = 168, на D 360 на 1h 104
    NUMBER_BARS_CHECK   = 8 # Сколько свечей вперед для подтверждения минимума или максимума индикатора VPVR
    
    LEVELS_PARAM        = [50, 65, 80] # Параметр для расчета уровней слабый 30 средний 60, сильный 80
    PERCENTAGE          = 0.10 # процент отклонения от минимального объема для вхождения в уровень  (максимальный пик - минимальный объем) * config.PERCENTAGE
    API_KEY         = os.getenv("API_KEY")
    API_SECRET      = os.getenv("API_SECRET")

    
    # ==========================================================
    # Телеграмм настройка
    # ==========================================================
    TG_TOKEN            = "7816852065:AAH6XRD182B9uCk3Mb2JxI4myiHGak2FeV8" #os.getenv("TG_TOKEN") #'7494518927:AAEnNHZ8YXDSawS0vwtmkYM3jAyk4Gwrepc'
    TG_ADMINS           = '408983918,000002' # Вписать id администраторов телеграм бота через "," 

class TestingConfig(Config):
    """Конфигурация для среды тестирования."""
    API_KEY         = os.getenv("API_KEY")
    API_SECRET      = os.getenv("API_SECRET")
    TESTING         = True
    GRAFIC_SEE      = True
    # задаем свой период для тестов либо None #
    START_DATETIME  = None #1729710387000
    END_DATETIME    = None #1730401587000

class ProductionConfig(Config):
    """Конфигурация для продакшн-среды."""
