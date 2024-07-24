# Используем базовый образ Python
FROM python:3.9-slim

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    build-essential \
    default-libmysqlclient-dev \
    pkg-config \
    bash \
    && rm -rf /var/lib/apt/lists/*

# Копируем файлы проекта внутрь контейнера
WORKDIR /app
COPY . .

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Выводим список файлов для отладки
RUN ls -la /app

# Определяем команду для запуска
CMD ["python", "run.py"]
