"""
Hebrew Voice Assistant — главный файл FastAPI приложения.
Сервер работает ТОЛЬКО как API. Никогда не использует микрофон/динамик Mac.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
import sys
import os
from dotenv import load_dotenv

load_dotenv()

# === Настройка логирования ===
logger.remove()
logger.add(
    sys.stderr,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
    level="DEBUG",
)
logger.add(
    "logs/app.log",
    rotation="10 MB",
    retention="7 days",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function} - {message}",
    level="INFO",
)

# === Создаём приложение ===
app = FastAPI(
    title="Hebrew Voice Assistant",
    description="голосовой AI-ассистент на иврите",
    version="0.2.1",
)

# === CORS ===
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    logger.info("🚀 Hebrew Voice Assistant v0.2.1 запускается...")
    logger.info("📡 Сервер работает ТОЛЬКО как API (без микрофона/динамика)")


@app.on_event("shutdown")
async def shutdown_event():
    logger.info("👋 Сервер останавливается...")


# === Базовые эндпоинты ===

@app.get("/")
async def root():
    return {
        "status": "ok",
        "message": "שלום! אני תומר, העוזר הקולי שלך",
        "version": "0.2.1",
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


@app.get("/api/logs")
async def get_logs():
    import json
    import os
    try:
        if not os.path.exists("logs/conversations.jsonl"):
            return {"logs": []}
        with open("logs/conversations.jsonl", "r", encoding="utf-8") as f:
            lines = f.readlines()
            logs = [json.loads(line) for line in lines if line.strip()]
            return {"logs": logs}
    except Exception as e:
        return {"logs": [], "error": str(e)}

# === Подключение роутеров ===
from routes.chat import router as chat_router
from routes.speech import router as speech_router
from routes.live_socket import router as live_socket_router

app.include_router(chat_router, prefix="/api")
app.include_router(speech_router, prefix="/api")
app.include_router(live_socket_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
