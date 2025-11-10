# Логирование
# ====================================================
from src.utils.logger import get_logger
logger = get_logger(__name__)

# индикатор фибоначчи
from src.logical.indicators.fibonacci import fibonacci_levels
# индикатор zigzag
from src.logical.indicators.zigzag import ZigZag
# класс позиции
from src.risk_manager.trade_position import Position, TakeProfitLevel, StopLoss

# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# data_df - DataFrame с данными для расчета индикаторов Подается нужное кол-во баров для расчета
# расчет стратегии ZigZag и Фибоначчи 
# на выходе получаем dataframe с рассчитанными индикаторами
# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++

class ZigZagAndFibo:
    # 
    def __init__(self, symbol: str, tick_size: float):
        self.symbol = symbol # название монеты
        self.tick_size = tick_size # размер шага цены и минимальное изменение цены
        self.previous_direction = None # предыдущее направление zigzag

    # рассчитываем стратегию
    def calculate_strategy(self, data_df):
        """
        Запуск стратегии ZigZag и уровней Фибоначчи на переданных данных.
        Определяем есть ли сигнал и если есть создаем позицию
        """
        # Расчет индикаторов
        zigzag, fiboLev = calculate_indicators(data_df)
        
        # Проверка корректности результата
        if zigzag is None or fiboLev is None:
            logger.error(f"Стратегия не вернула корректные результаты.")
            return None

        logger.info(f"ZigZag / z1 =: {zigzag["z1"]}, z2 =: {zigzag["z2"]}, z2_index: {zigzag['z2_index']} direction: {zigzag['direction']}")        
        
        position = None
        direction = zigzag["direction"]
        
        if direction == -1 and (self.previous_direction == 1 or self.previous_direction == None):
            logger.info(f"🎢 Расчет сделки на [bold green] BUY [/bold green] / на баре - {data_df.index[-1]} ")
            
            entry_price = data_df["open"].iloc[-1]
            stop_loss = fiboLev[161.8]
            
            # Создание сделки
            tps= []
            # перебираем все 5 тейков в обратном порядке 
            for level, value in list(fiboLev.items())[:5][::-1]:
                # logger.info(f"Уровень Фибоначчи {level}%: {value}")
                tps.append(TakeProfitLevel(price=value, volume=0.2, tick_size=self.tick_size)) 
        
            position = Position(
                symbol=self.symbol,
                direction='long',
                entry_price=entry_price,
                volume=0.2,
                bar_index=data_df.index[-1],
                tick_size=self.tick_size,
            )
            position.set_take_profits(tps)
            position.add_stop_loss(StopLoss(price=stop_loss, volume=1, tick_size=self.tick_size))
            logger.info(f"Сделка создана: {position}, {position.status}")            
            self.previous_direction = -1
            
        if direction == 1 and (self.previous_direction == -1 or self.previous_direction == None):
            logger.info(f"🎢 Расчет сделки на [bold red] SELL [/bold red] / на баре - {data_df.index[-1]} ")    

            for level, value in fiboLev.items():
                logger.info(f"Уровень Фибоначчи {level}%: {value}")
            # запускаем расчет ордеров по стратегии
            # from src.risk_manager.risk_manager import RiskManager
            # risk_manager = RiskManager()
            # risk_manager.calculate_position_size()
            self.previous_direction = 1

        return position

    
# Расчет индикаторов
def calculate_indicators(data_df):
    try:
        
        zigzag_indicator = ZigZag()
        # z1, z2, direction, z2_index = zigzag_indicator.calculate_zigzag(data_df)
        zigzag = zigzag_indicator.calculate_zigzag(data_df)
        
        # Расчет уровней Фибоначчи
        fiboLev = fibonacci_levels(zigzag["z1"], zigzag["z2"], zigzag["direction"]) # fiboLev = fibonacci_levels(z1, z2, direction)

        return zigzag, fiboLev
    except Exception as e:
        logger.error(f"Ошибка при запуске стратегии ZigZag и Фибоначчи: {e}")
        return None, None



