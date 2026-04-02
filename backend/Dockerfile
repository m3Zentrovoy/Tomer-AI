FROM python:3.11-slim

WORKDIR /app

# Устанавливаем системные зависимости для PyAudio и работы со звуком
RUN apt-get update && apt-get install -y \
    gcc \
    portaudio19-dev \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Копируем файл с зависимостями и устанавливаем их
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь код бэкенда
COPY . .

# Создаем папку для логов, если она нужна
RUN mkdir -p logs

# Запускаем FastAPI через Uvicorn, используя динамический порт от Railway (по дефолту 8000)
CMD sh -c "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"
