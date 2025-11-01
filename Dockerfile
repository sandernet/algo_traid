FROM python:3.13-slim

# Установка рабочей директории
WORKDIR /app

# Установка зависимостей
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копирование исходного кода
COPY . .

# Создание volume для данных
VOLUME ["/app/data"]

# Команда запуска
CMD ["python", "app.py"]