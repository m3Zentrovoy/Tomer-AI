"""
Сервис Speech-to-Text через Google Cloud Speech API (REST).
Транскрибирует аудио на иврите в текст.
Использует GOOGLE_API_KEY — без сервисного аккаунта.
"""

import os
import base64
from dotenv import load_dotenv
import httpx
from loguru import logger

# Загружаем переменные окружения
load_dotenv()

# Google API
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
STT_URL = f"https://speech.googleapis.com/v1/speech:recognize?key={GOOGLE_API_KEY}"


async def transcribe_audio(audio_bytes: bytes, mime_type: str = "audio/webm") -> str:
    """
    Транскрибирует аудио в текст через Google Cloud Speech API.

    Args:
        audio_bytes: Байты аудио файла.
        mime_type: MIME тип файла (audio/webm, audio/mp3, audio/wav и т.д.).

    Returns:
        Текст транскрипции на иврите.

    Raises:
        Exception: При ошибке вызова Speech API.
    """
    try:
        # Маппинг MIME типов в формат кодирования Google Speech API
        encoding_map = {
            "audio/webm": "WEBM_OPUS",
            "audio/ogg": "OGG_OPUS",
            "audio/wav": "LINEAR16",
            "audio/mp3": "MP3",
            "audio/mpeg": "MP3",
            "audio/flac": "FLAC",
            "audio/mp4": "MP3",
            "audio/m4a": "MP3",
        }
        encoding = encoding_map.get(mime_type, "WEBM_OPUS")

        # Кодируем аудио в base64
        audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")

        logger.debug(f"Отправляю аудио в Google STT | размер: {len(audio_bytes)} байт, кодирование: {encoding}")

        # Формируем запрос
        payload = {
            "config": {
                "encoding": encoding,
                "languageCode": "he-IL",
                "enableAutomaticPunctuation": True,
            },
            "audio": {
                "content": audio_base64,
            },
        }

        # Отправляем запрос через httpx
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(STT_URL, json=payload)
            response.raise_for_status()

        result = response.json()

        # Извлекаем текст из ответа
        results = result.get("results", [])
        if not results:
            logger.warning("Google STT вернул пустой результат")
            return ""

        text = results[0]["alternatives"][0]["transcript"]
        logger.info(f"Транскрипция получена | текст: {text[:50]}...")

        return text

    except Exception as e:
        logger.error(f"Ошибка при транскрипции аудио: {e}")
        raise
