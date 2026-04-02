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

# Hugging Face Spaces требует, чтобы приложение работало на порту 7860
ENV PORT=7860
EXPOSE 7860

# Запускаем FastAPI через Uvicorn на порту 7860
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]
