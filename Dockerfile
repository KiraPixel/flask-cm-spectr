# Используем базовый образ Python
FROM python:3.9-slim

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    build-essential \
    default-libmysqlclient-dev \
    pkg-config \
    bash \
    && rm -rf /var/lib/apt/lists/*

# Устанавливаем зависимости
RUN pip install -r requirements.txt

# Определяем команду для запуска
CMD ["python", "run.py"]
