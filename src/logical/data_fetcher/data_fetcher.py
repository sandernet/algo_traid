"""# data_fetcher	
# Получение и хранение исторических/рыночных данных.	
# Подключение к API биржи (например, Binance, Bybit). 
# Загрузка OHLCV-свечей. Обновление рыночных данных в реальном времени.
"""

import ccxt
import pandas as pd
import time
from datetime import datetime
from typing import Optional
from src.utils.logger import get_logger 
from src.config.config import config

logger = get_logger(__name__)


# TODO: Добавить информацию о монете при иницыализации класса

class DataFetcher:
    """
    Класс для получения исторических данных с биржи с помощью пагинации.
    """
    def __init__(self):
        # Получение настроек
        exchange_id = config.get_setting("EXCHANGE_SETTINGS", "EXCHANGE_ID")
        self.symbol = config.get_setting("EXCHANGE_SETTINGS", "SYMBOL")
        self.timeframe = config.get_setting("EXCHANGE_SETTINGS", "TIMEFRAME")
        
        # Настройки для пагинации
        self.limit = 1000  # Максимальное количество свечей за запрос
        
        # 1. Инициализация биржи ccxt
        try:
            exchange_class = getattr(ccxt, exchange_id.lower())
            # Bybit не требует API-ключей для публичных данных (OHLCV)
            self.exchange = exchange_class() 
            logger.info(f"Подключение к бирже {exchange_id} успешно.")
        except AttributeError:
            logger.error(f"Биржа '{exchange_id}' не поддерживается библиотекой ccxt.")
            raise

    def _convert_date_to_ms(self, date_str: str) -> int:
        """Конвертирует дату YYYY-MM-DD в Unix-таймштамп в миллисекундах."""
        dt = datetime.strptime(date_str, '%Y-%m-%d')
        return int(dt.timestamp() * 1000)

    def fetch_all_historical_data(self) -> Optional[pd.DataFrame]:
        """
        Загружает исторические данные, используя пагинацию,
        начиная с BACKTEST_START_DATE и до текущей даты.
        """
        all_ohlcv = []
        
        # Получаем начальную дату из конфигурации
        start_date_str = config.get_setting("MODE_SETTINGS", "BACKTEST_START_DATE")
        since_ms = self._convert_date_to_ms(start_date_str)
        
        # Текущий таймштамп для остановки цикла
        now_ms = int(time.time() * 1000)
        
        logger.info(f"Начало загрузки {self.symbol} ({self.timeframe}) с {start_date_str}...")

        while since_ms < now_ms:
            try:
                # 2. Основной запрос к API с пагинацией
                ohlcv_chunk = self.exchange.fetch_ohlcv(
                    symbol=self.symbol,
                    timeframe=self.timeframe,
                    since=since_ms,
                    limit=self.limit
                )
                
                if not ohlcv_chunk:
                    logger.warning("Получен пустой ответ. Достигнут конец доступной истории.")
                    break

                all_ohlcv.extend(ohlcv_chunk)
                
                # 3. Обновление 'since' для следующего запроса
                # 'since' устанавливается на таймштамп ПОСЛЕДНЕЙ свечи в полученном чанке + 1мс.
                # Это гарантирует, что мы не получим дубликаты.
                last_timestamp = ohlcv_chunk[-1][0]
                since_ms = last_timestamp + 1
                
                # Логирование прогресса
                last_date = datetime.fromtimestamp(last_timestamp / 1000).strftime('%Y-%m-%d %H:%M:%S')
                logger.info(f"Успешно загружено свечей: {len(ohlcv_chunk)}. Продолжение с даты: {last_date}")
                
                # Защита от DoS (небольшая задержка между запросами)
                time.sleep(self.exchange.rateLimit / 1000) 

            except ccxt.ExchangeError as e:
                logger.error(f"Ошибка API при загрузке данных: {e}")
                time.sleep(5)  # Пауза и повторная попытка
                continue
            except Exception as e:
                logger.critical(f"Критическая ошибка загрузки данных: {e}", exc_info=True)
                return None

        if not all_ohlcv:
            logger.warning("Данные не загружены. Проверьте правильность SYMBOL и TIMEFRAME.")
            return None

        # 4. Формирование DataFrame
        df = pd.DataFrame(all_ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        
        # Удаление дубликатов (если они могли возникнуть из-за ошибки в since_ms)
        df.drop_duplicates(subset=['timestamp'], inplace=True) 
        
        # Установка таймштампа в качестве индекса и конвертация в формат datetime
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        
        logger.info(f"Загрузка завершена. Всего свечей: {len(df)}. Диапазон: {df.index.min()} - {df.index.max()}")
        
        return df

# # ======================================================================
# # ПРИМЕР ЗАПУСКА
# # ======================================================================
# if __name__ == '__main__':
#     # В реальном приложении этот код будет в модуле main
    
#     fetcher = DataFetcher()
#     data_df = fetcher.fetch_all_historical_data()
    
#     if data_df is not None:
#         print("\n--- Фрагмент загруженных данных (DataFrame) ---")
#         print(data_df.head())
#         print(data_df.tail())