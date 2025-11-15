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
from src.orders_block.trade_position import Position, TakeProfit,  float_to_decimal
from src.orders_block.trade_position import TakeProfit_Status, Position_Status, StopLoss_Status, Direction # статусы

# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# Класс стратегии
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
        
        direction_zigzag = zigzag["direction"] # направление позиции -1 long, 1 short
        z2_index = zigzag["z2_index"] # индекс ближайшей точки z2 
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
                logger.info(f"Цена входа {entry_price} [bold green] < [/bold green] {fiboLev[78.6]['level_price']} [bold green]long[/bold green]")
                direction = Direction.LONG # направление позиции -1 long, 1 short
            else :
                logger.info(f"Цена входа {entry_price} [bold red] > [/bold red] {fiboLev[78.6]['level_price']}")
                logger.info(f"Пропускаем сигнал на long")
                return {}

        if direction_zigzag == 1: #индикатор zigzag показывает что нужно входить в long
            logger.info(f"Индикатор zigzag показывает что нужно входить в long {direction_zigzag}")
            # проверяем цену входа в позицию с первым тейком 1 уровня фибоначчи цена входа должна быть меньше уровня 1
            if entry_price > fiboLev[78.6]['level_price']:
                logger.info(f"Цена входа {entry_price} [bold green] > [/bold green] {fiboLev[78.6]['level_price']}")
                direction = Direction.SHORT # направление позиции -1 long, 1 short
            else :
                logger.info(f"Цена входа {entry_price} [bold red] < [/bold red] {fiboLev[78.6]['level_price']}")
                logger.info(f"Пропускаем сигнал на long")
                return {}
            
                    
        if direction is None:
            logger.info(f"Нет сигнала на вход в позицию")
            return {}
        # Создание сделки
        tps= []
        # перебираем все 5 тейков в обратном порядке 
        for _, value in list(fiboLev.items())[:5][::-1]:
            tps.append(TakeProfit(price=value['level_price'], volume=value['volume'])) 
        
        signal = {
            "price": entry_price,
            "direction": direction,
            "take_profits": tps,
            "stop_loss": stop_loss,
            "stop_loss_volume": stop_loss_volume,
            "z2_index": z2_index
            }

        return signal

# ------------------------------------------
# Расчет индикаторов
# ------------------------------------------
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



class PositionsManager():
    def __init__(self, position: Position):
        self.position = position
        
            # Проверяет, сработал ли Take Profit если закрыты все Take Profit возвращает True
    def check_take_profit(self, current_bar) -> bool:
        high_price = float_to_decimal(current_bar["high"])
        low_price = float_to_decimal(current_bar["low"])
        full_closed = False
        
        position = self.position
        
        # Проверяем каждый Take Profit
        for tp in position.take_profits:
            # Если Take Profit ещё не сработал
            if tp.bar_executed is None and tp.Status == TakeProfit_Status.ACTIVE:
                # Если позиция в long и текущая цена выше Take Profit               
                if (position.direction == Direction.LONG and high_price >= tp.price) or (position.direction == Direction.SHORT and low_price <= tp.price):
                    # меняем статус
                    tp.Status = TakeProfit_Status.EXECUTED
                    # устанавливаем индекс бара в котором был сработан Take Profit
                    tp.bar_executed = current_bar.name
                    logger.info(f"Take Profit с объемом {tp.volume} от позиции, ценой {tp.price} исполнен в баре {tp.bar_executed}")
        
        # Проверяем первый  Take Profit 
        if position.take_profits and position.take_profits[0].Status == TakeProfit_Status.EXECUTED:
            # меняем статус
            position.status = Position_Status.TAKEN_PART
            logger.info(f"Исполнен первый Take Profit")
            position.stop_loss_not_loss() # переводим стоп-лосс в без убыток
            logger.info(f"Переводим стоп-лосс в без убыток")
            
                        
        # Проверяем последний Take Profit исполнен
        if position.take_profits and position.take_profits[-1].Status == TakeProfit_Status.EXECUTED:
            # меняем статус
            position.status = Position_Status.TAKEN_FULL
            logger.info(f"Исполнен последний Take Profit [bold green] DONE [/bold green]")
            # устанавливаем индекс бара в котором был сработан stop_loss
            position.bar_closed = current_bar.name
            if position.stop_loss:
                position.stop_loss.status = StopLoss_Status.CANCELED
            full_closed = True  
        return full_closed
    
    # Проверяет, сработал ли Stop Loss
    # если закрыт стоп-лосс возвращает True
    def check_stop_loss(self, current_bar) -> bool:
        
        position = self.position
        # если статус stop_loss Активный
        if position.stop_loss and position.stop_loss.bar_executed is None and position.stop_loss.status == StopLoss_Status.ACTIVE:
            # проверяем с текущим баром
            if (position.direction == Direction.LONG and current_bar["low"] <= position.stop_loss.price) or (position.direction == Direction.SHORT and current_bar["high"] >= position.stop_loss.price):
                # меняем статус
                position.stop_loss.status = StopLoss_Status.EXECUTED
                position.status = Position_Status.STOPPED
                # устанавливаем индекс бара в котором был сработан stop_loss
                position.stop_loss.bar_executed = current_bar.name
                position.bar_closed = current_bar.name
                return True
        # если статус stop_loss Без убыток
        if position.stop_loss and position.stop_loss.bar_executed is None and position.stop_loss.status == StopLoss_Status.NO_LOSS:
            if (position.direction == Direction.LONG and current_bar["low"] <= position.entry_price) or (position.direction == Direction.SHORT and current_bar["high"] >= position.entry_price):
                # меняем статус
               
                # устанавливаем индекс бара в котором был сработан stop_loss
                position.stop_loss.bar_executed = current_bar.name
                position.bar_closed = current_bar.name
                return True
        return False
    
    # Останавливает позицию
    # если у позиции остался обьем не закрытый закрываем его по текущей цене (в бэктесте берем открытие текущей свечи)
    def close_orders(self, current_bar):
        
        position = self.position
        
        status = Position_Status.CANCELLED
        # если стоп-лосс не исполнен
        if position.stop_loss and position.stop_loss.bar_executed is None:
            status = Position_Status.CANCELLED
            position.stop_loss.status = StopLoss_Status.CANCELED
            position.stop_loss.bar_executed = current_bar.name
            position.stop_loss.price = current_bar["open"]

        
        if position.status == Position_Status.TAKEN_PART:
            status = Position_Status.TAKEN_PART
            for tp in position.take_profits:
                if tp.Status == TakeProfit_Status.ACTIVE:
                    tp.Status = TakeProfit_Status.CANCELED
                    tp.bar_executed = current_bar.name
        
        if position.status == Position_Status.TAKEN_FULL:
            status = Position_Status.TAKEN_FULL


        position.bar_closed = current_bar.name
        position.status = status
        
    # Расчет прибыли позиции по всем тейк-профитам или стоп-лосс
    def Calculate_profit(self):
        """
        Рассчитывает общую прибыль/убыток по позиции
        исходя из сработавших Take Profit и Stop Loss с использованием Decimal.
        """
                
        position = self.position
        
        # Инициализируем переменные для расчетов в Decimal
        total_profit = Decimal('0.0')
        closed_volume = Decimal('0.0')
        
        # Проверяем, установлен ли размер позиции
        if not hasattr(position, 'volume_size'):
            # Возможно, нужно вернуть 0.0 или вызвать ошибку, если позиция не имеет объема
            return Decimal('0')

        # 1. Расчет прибыли по сработавшим Take Profit
        for tp in position.take_profits:
            if tp.bar_executed is not None and tp.Status == TakeProfit_Status.EXECUTED:
                # Объем закрытия для данного TP (Decimal)
                # tp.volume - это доля (float), приводим к Decimal
                volume = position.volume_size * tp.volume
                # closed_volume = position.volume_size * float(tp.volume)
                
                if position.direction == Direction.LONG:
                    # Разница цены (Decimal)
                    price_diff = tp.price - position.entry_price
                else:  # Direction.SHORT
                    # Разница цены (Decimal)
                    price_diff = position.entry_price - tp.price
                    
                # Прибыль/убыток по данному TP (Decimal)
                profit = price_diff * volume
                
                # Сохраняем результат в атрибутах класса
                tp.profit = profit
                total_profit += profit
                closed_volume += volume
         
        
        # 2. Расчет прибыли/убытка по сработавшему Stop Loss
        if position.stop_loss and position.stop_loss.bar_executed is not None:
            # Оставшийся объем, закрытый по SL (Decimal)
            # total_volume = position.volume_size
            
            remaining_volume = position.volume_size - closed_volume
            
            if remaining_volume > Decimal('0.0'):
                if position.stop_loss.status == StopLoss_Status.NO_LOSS:
                    sl_price = position.entry_price
                else:
                    sl_price = position.stop_loss.price
                        
                if position.direction == Direction.LONG:
                    price_diff = sl_price - position.entry_price
                else:
                    price_diff = position.entry_price - sl_price
                    
                # Прибыль/убыток по SL (Decimal)
                sl_profit = price_diff * remaining_volume
                
                position.stop_loss.profit = sl_profit
                position.stop_loss.volume = remaining_volume # закрываем оставшийся объем
                total_profit += sl_profit
        
        # # 3. Обновление итоговой прибыли позиции
        # if position.volume_size == remaining_volume:
        position.profit = total_profit
        return position
        
    # def __repr__(self):
    #     return (f"Position(symbol={self.symbol}, entry_price={self.entry_price}, direction={self.direction.value}, \n"
    #             f"status={self.status.value} \n"
    #             f"volume_size={self.volume_size} \n"
    #             f"{self.take_profits}\n" 
    #             f"{self.stop_loss})")