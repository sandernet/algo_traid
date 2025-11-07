import yaml
import os
from typing import Any, Dict

# Путь к файлу конфигурации
CONFIG_FILE_PATH = os.path.join(os.getcwd(), "configs", 'config.yaml')


# Определение ожидаемых параметров и их типов
REQUIRED_SETTINGS: Dict[str, Dict[str, Any]] = {
    "EXCHANGE_SETTINGS": {
        "EXCHANGE_ID": str,
        "API_KEY": str,
        "API_SECRET": str,
        "TIMEFRAME": str,
        "CATEGORY": str,
        "LIMIT": int,
    },
    "STRATEGY_SETTINGS": {
        "ZIGZAG_DEPTH": (int, float),
        "ZIGZAG_DEVIATION": (int, float),
        "ZIGZAG_BACKTEP": (int, float),
        "FIBONACCI_LEVELS": list,
    },
    "RISK_SETTINGS": {
        "STOP_LOSS_PERCENT": (int, float),
        "TAKE_PROFIT_PERCENT": (int, float),
        "MAX_POSITIONS": int,
    },
    "MODE_SETTINGS": {
        "MODE": str,
    },
    "TELEGRAM_SETTINGS": {
        "TOKEN": str,
        "ADMIN_ID": int,
        "CHANNEL_ID": int
    }
}
# Определение ожидаемых параметров и их типов для каждого элемента в массиве COINS
REQUIRED_COIN_FIELDS: Dict[str, Any] = {
    "SYMBOL": str,
    "TIMEFRAME": str,
    "AUTO_TRADING": bool,
    "START_DEPOSIT_USDT": (int, float),
    # "ORDERTYPE": str
    "MINIMAL_TICK_SIZE": (int, float) # Минимальный размер шага цены
}

class ConfigValidationError(Exception):
    """Кастомное исключение для ошибок валидации конфигурации."""
    pass

class ConfigManager:
    """
    Класс для загрузки, парсинга и предоставления доступа к настройкам из config.yml.
    """
    def __init__(self, config_path: str = CONFIG_FILE_PATH):
        self.config_path = config_path
        self._config = self._load_config()
        # Вызов функции валидации сразу после загрузки
        self._validate_config()
        

    def _load_config(self) -> dict:
        """Загружает и возвращает данные из YAML-файла."""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as file:
                config_data = yaml.safe_load(file)
            print(f"✅ Конфигурация успешно загружена из: {self.config_path}")
            return config_data
        except FileNotFoundError:
            raise FileNotFoundError(f"❌ Файл конфигурации не найден по пути: {self.config_path}")
        except yaml.YAMLError as e:
            raise yaml.YAMLError(f"❌ Ошибка парсинга YAML-файла: {e}")
        
    def _validate_config(self):
        """Проверяет наличие и тип всех обязательных параметров."""
        print("🔍 Запуск валидации конфигурации...")
        errors = []
        mode = self.get_setting("MODE_SETTINGS", "MODE").lower()

        # 1. Проверка наличия и типа основных параметров
        for section, settings in REQUIRED_SETTINGS.items():
            if section not in self._config:
                errors.append(f"Отсутствует обязательная секция: {section}")
                continue

            for key, expected_type in settings.items():
                if key not in self._config[section]:
                    errors.append(f"Отсутствует обязательный параметр: [{section}][{key}]")
                    continue

                value = self._config[section][key]
                if not isinstance(value, expected_type):
                    # Обработка list как частного случая
                    if expected_type == list and value is None:
                        errors.append(f"Некорректный тип для [{section}][{key}]. Ожидается {expected_type.__name__}, но получено None.")
                    elif expected_type != list and value is not None and not isinstance(value, expected_type):
                        errors.append(f"Некорректный тип для [{section}][{key}]. Ожидается {expected_type.__name__}, но получено {type(value).__name__}.")

        # 2. Дополнительные логические проверки
        # 2. **НОВАЯ ПРОВЕРКА**: Проверка массива COINS
        if 'COINS' not in self._config:
            errors.append("Отсутствует обязательный массив: [COINS]")
        else:
            coins_list = self._config['COINS']
            if not isinstance(coins_list, list):
                errors.append("[COINS] должен быть списком (массивом). Получено: {type(coins_list).__name__}")
            elif not coins_list:
                errors.append("Массив [COINS] не должен быть пустым.")
            else:
                # Перебор каждой монеты в массиве
                for i, coin in enumerate(coins_list):
                    if not isinstance(coin, dict):
                        errors.append(f"[COINS][{i}]: Элемент должен быть объектом (словарем). Получено: {type(coin).__name__}")
                        continue

                    for key, expected_type in REQUIRED_COIN_FIELDS.items():
                        if key not in coin:
                            errors.append(f"[COINS][{i}] ({coin.get('SYMBOL', 'UNKNOWN')}): Отсутствует обязательный параметр: {key}")
                            continue

                        value = coin[key]
                        # Проверка типа
                        if not isinstance(value, expected_type):
                            errors.append(f"[COINS][{i}] ({coin.get('SYMBOL', 'UNKNOWN')}): Некорректный тип для '{key}'. Ожидается {expected_type.__name__}, но получено {type(value).__name__}.")
            
        
        # Проверка API-ключей, если это Live или Paper Trading
        if mode in ['live', 'paper']:
            api_key = self._config.get("EXCHANGE_SETTINGS", {}).get("API_KEY")
            secret_key = self._config.get("EXCHANGE_SETTINGS", {}).get("SECRET_KEY")
            
            if not api_key:
                errors.append("Для режима 'live'/'paper' требуется API_KEY.")
            if not secret_key:
                errors.append("Для режима 'live'/'paper' требуется SECRET_KEY.")
                
        # # Проверка параметров бэктестинга
        # if mode == 'backtest':
        #     if not self.get_setting("MODE_SETTINGS", "BACKTEST_START_DATE"):
        #         errors.append("Для режима 'backtest' требуется BACKTEST_START_DATE.")
        #     # Здесь можно добавить проверку формата даты
        
        # # Проверка параметров стратегии
        # deviation = self.get_setting("STRATEGY_SETTINGS", "ZIGZAG_DEVIATION_PERCENT")
        # if deviation <= 0:
        #     errors.append("ZIGZAG_DEVIATION_PERCENT должен быть положительным числом (> 0).")
            
        # fib_levels = self.get_setting("STRATEGY_SETTINGS", "FIBONACCI_LEVELS")
        # if not (0 < min(fib_levels) < 1 and 0 < max(fib_levels) < 1):
        #      errors.append("Уровни Фибоначчи должны быть в диапазоне (0, 1).")


        # 3. Вывод результатов валидации
        if errors:
            error_message = "\n\n❌ ОШИБКА ВАЛИДАЦИИ КОНФИГУРАЦИИ (config.yml):\n"
            error_message += "\n".join([f"- {err}" for err in errors])
            error_message += "\n\nПожалуйста, исправьте файл config.yml и перезапустите."
            raise ConfigValidationError(error_message)
        
        print("✅ Валидация конфигурации успешно пройдена.")
    
    def get_setting(self, section: str, key: str):
        """Возвращает конкретную настройку по секции и ключу."""
        # ... (Код без изменений)
        if section in self._config and key in self._config[section]:
            return self._config[section][key]
        else:
            # Во время runtime мы предполагаем, что _validate_config уже нашел все критические ошибки,
            # но для безопасности можно оставить эту проверку.
            # return None 
            raise KeyError(f"Настройка '{key}' не найдена в секции '{section}'.")

    def get_section(self, section: str) -> dict:
        """Возвращает всю секцию настроек."""
        if section in self._config:
            return self._config[section]
        else:
            raise KeyError(f"❌ Секция '{section}' не найдена в файле конфигурации.")

try:
    config = ConfigManager()
except (FileNotFoundError, yaml.YAMLError, ConfigValidationError) as e:
    # Важно: При ошибке валидации или загрузки, программа должна быть остановлена
    print(f"\nFATAL ERROR: {e}")
    # Вы можете добавить здесь os._exit(1) для принудительной остановки, 
    # если это главный скрипт
    raise SystemExit(1)

# # Создание синглтона для доступа к конфигурации
# config = ConfigManager()