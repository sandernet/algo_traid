from decimal import Decimal
# Логирование
# ====================================================
from src.utils.logger import get_logger
logger = get_logger(__name__)

# индикатор фибоначчи
from src.logical.indicators.fibonacci import fibonacci_levels
# индикатор zigzag
from src.logical.indicators.zigzag import ZigZag
# класс позиции
from src.orders_block.trade_position import TakeProfitLevel, Direction

# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# data_df - DataFrame с данными для расчета индикаторов Подается нужное кол-во баров для расчета
# расчет стратегии ZigZag и Фибоначчи 
# на выходе получаем dataframe с рассчитанными индикаторами
# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++

class ZigZagAndFibo:
    # 
    def __init__(self, symbol: str):
        self.symbol = symbol # название монеты
        
        

    # Ищем точку входа по стратегии
    def find_entry_point(self, data_df) -> dict:
        """
        Запуск стратегии ZigZag и уровней Фибоначчи на переданных данных.
        Определяем есть ли сигнал и если есть создаем позицию
        """
        # Расчет индикаторов
        zigzag, fiboLev = calculate_indicators(data_df)
        
        # Проверка корректности результата
        if zigzag is None or fiboLev is None:
            logger.error(f"Стратегия не вернула корректные результаты.")
            return {} 

        logger.info(f"ZigZag / z1 =: {zigzag["z1"]}, z2 =: {zigzag["z2"]}, z2_index: {zigzag['z2_index']} direction: {zigzag['direction']}")        
        

        logger.info(f"Открытой позиций нет. запускаем стратегию")

        direction_zigzag = zigzag["direction"] # направление позиции -1 long, 1 short
        z2_index = zigzag["z2_index"] # индекс ближайшей точки z2 
        signal_bar = data_df.index[-1] # индекс последнего бара
        # current_index = current_bar.name # индекс текущего бара
        entry_price = data_df["close"].iloc[-1] # цена входа
        stop_loss = fiboLev[161.8]['level_price'] # уровень стоп лосс
        stop_loss_volume = fiboLev[161.8]['volume'] # объем стоп лосс
        direction = None
        
                    
        # # Проверяем индекс бара zigzag он должен совпадать с свечей расчета
        # if index_bar != z2_index or not z2_index != current_index:
        #     logger.info(f"z2_index {z2_index} бара расчета образовался раньше текущего бара {index_bar}")
        #     return {}
        
        # logger.info(f"index_bar {index_bar} == z2_index {z2_index}")
        
        if direction_zigzag == -1: #индикатор zigzag показывает что нужно входить в long
            logger.info(f"Индикатор zigzag показывает что нужно входить в long {direction_zigzag}")
            # проверяем цену входа в позицию с первым тейком 1 уровня фибоначчи цена входа должна быть меньше уровня 1
            if entry_price < fiboLev[78.6]['level_price']:
                logger.info(f"Цена входа {entry_price} [bold green]l < [/bold green] {fiboLev[78.6]['level_price']} [bold green]long[/bold green]")
                direction = Direction.LONG # направление позиции -1 long, 1 short
            else :
                logger.info(f"Цена входа {entry_price} [bold red]l > [/bold red] {fiboLev[78.6]['level_price']}")
                logger.info(f"Пропускаем сигнал на long")
                return {}

        if direction_zigzag == 1: #индикатор zigzag показывает что нужно входить в long
            logger.info(f"Индикатор zigzag показывает что нужно входить в long {direction_zigzag}")
            # проверяем цену входа в позицию с первым тейком 1 уровня фибоначчи цена входа должна быть меньше уровня 1
            if entry_price > fiboLev[78.6]['level_price']:
                logger.info(f"Цена входа {entry_price} [bold green]l > [/bold green] {fiboLev[78.6]['level_price']}")
                direction = Direction.SHORT # направление позиции -1 long, 1 short
            else :
                logger.info(f"Цена входа {entry_price} [bold red]l < [/bold red] {fiboLev[78.6]['level_price']}")
                logger.info(f"Пропускаем сигнал на long")
                return {}
            
                    
        if direction is None:
            logger.info(f"Нет сигнала на вход в позицию")
            return {}
        # Создание сделки
        tps= []
        # перебираем все 5 тейков в обратном порядке 
        for _, value in list(fiboLev.items())[:5][::-1]:
            tps.append(TakeProfitLevel(price=value['level_price'], volume=value['volume'])) 
        
        signal = {
            "price": entry_price,
            "direction": direction,
            "take_profits": tps,
            "stop_loss": stop_loss,
            "stop_loss_volume": stop_loss_volume,
            }

        return signal
        
        

    
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



