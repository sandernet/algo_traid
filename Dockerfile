# Используем официальный образ Python как базовый
FROM python:3.14-slim as builder
WORKDIR /install
RUN apt-get update && apt-get install -y build-essential
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip wheel --no-deps --wheel-dir /wheels -r requirements.txt

FROM python:3.14-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Устанавливаем рабочую директорию внутри контейнера
WORKDIR /app
COPY --from=builder /wheels /wheels
COPY requirements.txt .
RUN pip install --no-deps --no-index --find-links=/wheels -r requirements.txt

# Создаём необходимые директории
RUN mkdir -p DATA_OHLCV LOGS configs REPORTS

# Копируем само приложение
COPY . .

# Указываем тома, чтобы данные можно было монтировать извне
VOLUME ["/app/DATA_OHLCV", "/app/LOGS", "/app/configs, /app/REPORTS", "/app/TEMPLATES"]

# Команда запуска
CMD ["python", "app.py"]