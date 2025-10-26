"""# data_fetcher	
# Получение и хранение исторических/рыночных данных.	
# Подключение к API биржи (например, Binance, Bybit). 
# Загрузка OHLCV-свечей. Обновление рыночных данных в реальном времени.
"""

import ccxt
import pandas as pd
import time
from datetime import datetime
from typing import Optional, List
from src.utils.logger import get_logger 
from src.config.config import config

logger = get_logger(__name__)


# TODO: Добавить информацию о монете при иницыализации класса

class DataFetcher:
    """
    Класс для получения исторических данных с биржи с помощью пагинации для разных монет и временных интервалов.
    Параметры:
    - symbol: Торговая пара (например, 'BTC/USDT').
    - timeframe: Временной интервал (например, '1m' для минутных свечей).
    - exchange_id: Идентификатор биржи в ccxt (например, 'bybit').
    - limit: Максимальное количество свечей на один запрос (ограничение биржи).
    
    Поддерживает загрузку больших объемов данных, начиная с указанной даты.
    1. Инициализация биржи ccxt.
    2. Основной запрос к API с пагинацией.
    3. Обновление 'since' для следующего запроса.
    4. Формирование DataFrame.
    5. Обработка ошибок и логирование.
    """
    
    # Инициализация с параметрами монеты и биржи
    # ======================================================
    def __init__(self, symbol: str, timeframe: str, exchange_id: str, limit: int): 
        # Параметры, зависящие от монеты
        self.symbol = symbol 
        self.timeframe = timeframe 
        # Параметры биржи
        self.exchange_id = exchange_id
        self.limit = limit
        
        # 1. Инициализация биржи ccxt
        try:
            exchange_class = getattr(ccxt, exchange_id.lower())
            # Bybit не требует API-ключей для публичных данных (OHLCV)
            self.exchange = exchange_class() 
            logger.info(f"Подключение к бирже {exchange_id} успешно.")
        except AttributeError:
            logger.error(f"Биржа '{exchange_id}' не поддерживается библиотекой ccxt.")
            raise

    def _convert_date_to_ms(self, date_str: str, is_end_date: bool = False) -> int:
        """
        Конвертирует дату YYYY-MM-DD в Unix-таймштамп в миллисекундах.
        Для конечной даты (is_end_date=True) устанавливает время на конец дня (23:59:59.999).
        """
        try:
            dt = datetime.strptime(date_str, '%Y-%m-%d')
            if is_end_date:
                # Конец дня: 23:59:59.999
                dt = dt.replace(hour=23, minute=59, second=59, microsecond=999000)
            
            return int(dt.timestamp() * 1000)
        except ValueError:
            logger.error(f"Неверный формат даты: {date_str}. Ожидается 'YYYY-MM-DD'.")
            raise
        
    def _generic_fetcher(self, start_date_ms: Optional[int] = None, end_date_ms: Optional[int] = None) -> Optional[pd.DataFrame]:
        """
        Универсальный метод для загрузки данных с пагинацией НАЗАД ВО ВРЕМЕНИ.
        
        :param start_date_ms: Самый ранний таймштамп в мс, который нужно загрузить.
                              Если None, загрузка идет до самой ранней доступной даты.
        :param end_date_ms: Таймштамп в мс, с которого НАЧИНАЕТСЯ загрузка (самая новая дата).
                             Если None, начинается с текущего времени.
        """
        all_ohlcv: List[List] = []
        
        # 1. Определение начальной точки загрузки (самой новой свечи)
        # Если end_date_ms не указан, начинаем с текущего момента.
        since_ms = end_date_ms if end_date_ms is not None else int(time.time() * 1000)
        
        # 2. Определение точки остановки (самой старой свечи)
        # Если start_date_ms не указан, загрузка идет до конца истории (0).
        stop_ms = start_date_ms if start_date_ms is not None else 0 
        
        start_log = datetime.fromtimestamp(stop_ms / 1000).strftime('%Y-%m-%d') if stop_ms > 0 else "начала доступной истории"
        end_log = datetime.fromtimestamp(since_ms / 1000).strftime('%Y-%m-%d %H:%M:%S')
        logger.info(f"Начало загрузки {self.symbol} ({self.timeframe}) НАЗАД с {end_log} до {start_log}...")


        while True:
            try:
                # 3. Запрос: мы запрашиваем чанк, который ЗАКАНЧИВАЕТСЯ временем since_ms
                # Фактически, мы просим ccxt дать нам limit свечей, предшествующих since_ms.
                # Большинство бирж поддерживают такой режим, если since/until не указаны, 
                # но для пагинации назад мы используем параметр 'since' как 'until' 
                # или полагаемся на внутреннюю логику ccxt.
                ohlcv_chunk = self.exchange.fetch_ohlcv(
                    symbol=self.symbol,
                    timeframe=self.timeframe,
                    since=since_ms - 1000 * 60 * 60 * 24 * 365 * 10, # Приблизительная дата, чтобы ccxt мог начать, не критично, но лучше
                    limit=self.limit,
                    params={'until': since_ms} # Используем until/since, если биржа это поддерживает
                )
                
                # --- Важный момент: Биржи и ccxt ---
                # Самый надежный способ: ccxt.exchange.fetch_ohlcv()
                # Если биржа поддерживает 'until', ccxt использует его для загрузки НАЗАД.
                # На практике, передача None в 'since' и использование 'params={'until': since_ms}' 
                # часто заставляет ccxt загружать последние свечи до 'since_ms'.
                
                # Если fetch_ohlcv не поддерживает 'until' через params, 
                # нам нужно загрузить chunk, найти его первый таймштамп, 
                # и использовать его как точку 'since' для следующего шага назад. 
                # Ниже мы используем 'until' и полагаемся на ccxt.

                if not ohlcv_chunk or len(ohlcv_chunk) < 2:
                    logger.info(f"[{self.symbol}] Получен пустой ответ или менее двух свечей. Достигнут конец истории.")
                    break # Конец истории

                # 4. Обработка полученного чанка
                first_timestamp = ohlcv_chunk[0][0]
                last_timestamp = ohlcv_chunk[-1][0]
                
                # Если самая старая свеча (first_timestamp) уже старше нашей точки остановки (stop_ms)
                if first_timestamp <= stop_ms:
                    # Фильтруем свечи, которые выходят за рамки 'stop_ms' (слишком старые)
                    valid_chunk = [candle for candle in ohlcv_chunk if candle[0] >= stop_ms]
                    all_ohlcv.extend(valid_chunk)
                    logger.info(f"[{self.symbol}] Загрузка завершена по достижении начальной даты.")
                    break # Выход из цикла
                
                # Обычный случай: продолжаем пагинацию
                valid_chunk = ohlcv_chunk 
                all_ohlcv.extend(valid_chunk)

                # 5. Обновление 'since' (для следующего шага назад)
                # Следующая точка "until" будет на 1мс раньше самой первой свечи в этом чанке
                since_ms = first_timestamp - 1 
                
                # Логирование прогресса
                first_date = datetime.fromtimestamp(first_timestamp / 1000).strftime('%Y-%m-%d %H:%M:%S')
                logger.info(f"[{self.symbol}] Успешно загружено свечей: {len(valid_chunk)}. Продолжение НАЗАД с: {first_date}")
                
                # Защита от DoS
                time.sleep(self.exchange.rateLimit / 1000) 

            except ccxt.ExchangeError as e:
                # ... (обработка ошибок)
                logger.error(f"[{self.symbol}] Ошибка API при загрузке данных: {e}. Пауза 5с.", exc_info=True)
                time.sleep(5)
                continue
            except Exception as e:
                # ... (обработка ошибок)
                logger.critical(f"[{self.symbol}] Критическая ошибка загрузки данных: {e}", exc_info=True)
                return None

        # 6. Формирование DataFrame
        if not all_ohlcv:
            logger.warning(f"[{self.symbol}] Данные не загружены.")
            return None

        df = pd.DataFrame(all_ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        
        # Так как загрузка шла от нового к старому, список all_ohlcv будет обратным.
        # Сортируем его по таймштампу, чтобы данные были в хронологическом порядке.
        df.sort_values('timestamp', ascending=True, inplace=True) 
        df.drop_duplicates(subset=['timestamp'], inplace=True) 
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        
        logger.info(f"[{self.symbol}] Загрузка завершена. Всего свечей: {len(df)}. Диапазон: {df.index.min()} - {df.index.max()}")
        
        return df
    
    # -------------------------------------------------------------
    # 1. МЕТОД: Загрузка за весь период
    # -------------------------------------------------------------
    def fetch_entire_history(self) -> Optional[pd.DataFrame]:
        """
        Загружает максимально доступную историю (от самой ранней до текущей).
        """
        # start_date_ms=None и end_date_ms=None активируют логику "весь период" в _generic_fetcher
        return self._generic_fetcher(start_date_ms=None, end_date_ms=None)
    
    # -------------------------------------------------------------
    # 2. МЕТОД: Загрузка за определенный период
    # -------------------------------------------------------------
    def fetch_history_range(self, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        """
        Загружает данные за указанный период (включительно). 
        Формат даты: 'YYYY-MM-DD'.
        """
        start_ms = self._convert_date_to_ms(start_date, is_end_date=False)
        end_ms = self._convert_date_to_ms(end_date, is_end_date=True) # Конечная дата должна быть до конца дня!

        if start_ms >= end_ms:
            logger.error("Начальная дата должна быть раньше конечной даты.")
            return None
        
        return self._generic_fetcher(start_date_ms=start_ms, end_date_ms=end_ms)