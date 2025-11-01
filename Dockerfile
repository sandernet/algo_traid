# Используем официальный образ Python как базовый
FROM python:3.11-slim

# Устанавливаем рабочую директорию внутри контейнера
WORKDIR /app

# Создаём необходимые директории
RUN mkdir -p DATA_OHLCV logs configs

# Копируем зависимости (если есть requirements.txt)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем само приложение
COPY . .

# Указываем тома, чтобы данные можно было монтировать извне
VOLUME ["/app/DATA_OHLCV", "/app/logs", "/app/configs"]


# Команда запуска
CMD ["python", "app.py"]