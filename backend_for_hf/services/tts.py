"""
Сервис Text-to-Speech с поддержкой Narakeet, OpenAI, ElevenLabs и Google Cloud TTS.
"""

import os
import base64
from dotenv import load_dotenv
import httpx
from loguru import logger

# Загружаем переменные окружения
load_dotenv()

TTS_PROVIDER = os.getenv("TTS_PROVIDER", "narakeet").lower()

# Google Cloud
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_TTS_URL = f"https://texttospeech.googleapis.com/v1/text:synthesize?key={GOOGLE_API_KEY}"

# ElevenLabs
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
VOICE_ID = "onwK4e9ZLuTAKqWW03F9" # Daniel
ELEVENLABS_TTS_URL = f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}"

# OpenAI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_TTS_URL = "https://api.openai.com/v1/audio/speech"

# Narakeet
NARAKEET_API_KEY = os.getenv("NARAKEET_API_KEY")
NARAKEET_VOICE = os.getenv("NARAKEET_VOICE", "duncan")
NARAKEET_TTS_URL = f"https://api.narakeet.com/text-to-speech/mp3?voice={NARAKEET_VOICE}"


async def synthesize_speech(text: str) -> bytes:
    """
    Синтезирует речь из текста. Выбирает провайдера на основе TTS_PROVIDER.
    """
    logger.debug(f"Отправляю текст в TTS ({TTS_PROVIDER}) | длина: {len(text)} символов")

    if TTS_PROVIDER == "narakeet":
        return await _synthesize_narakeet(text)
    elif TTS_PROVIDER == "openai":
        return await _synthesize_openai(text)
    elif TTS_PROVIDER == "elevenlabs":
        return await _synthesize_elevenlabs(text)
    elif TTS_PROVIDER == "google":
        return await _synthesize_google(text)
    else:
        return await _synthesize_narakeet(text)

async def _synthesize_narakeet(text: str) -> bytes:
    """Narakeet TTS — Duncan (мужской, иврит). Streaming API, возвращает MP3."""
    try:
        headers = {
            "x-api-key": NARAKEET_API_KEY,
            "Content-Type": "text/plain",
            "accept": "application/octet-stream",
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                NARAKEET_TTS_URL,
                headers=headers,
                content=text.encode("utf-8"),
            )
            response.raise_for_status()

        audio_bytes = response.content
        logger.info(f"Аудио получено от Narakeet TTS | размер: {len(audio_bytes)} байт")
        return audio_bytes

    except Exception as e:
        logger.error(f"Ошибка Narakeet TTS: {e}")
        logger.info("Пробуем фолбэк на Google TTS...")
        return await _synthesize_google(text)


async def _synthesize_openai(text: str) -> bytes:
    try:
        headers = {
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "tts-1",
            "input": text,
            "voice": "onyx", # Мужской, глубокий, очень разговорный и естественный голос
            "response_format": "mp3"
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(OPENAI_TTS_URL, headers=headers, json=payload)
            response.raise_for_status()

        audio_bytes = response.content
        logger.info(f"Аудио получено от OpenAI TTS | размер: {len(audio_bytes)} байт")
        return audio_bytes

    except Exception as e:
        logger.error(f"Ошибка OpenAI TTS: {e}")
        logger.info("Пробуем фолбэк на Google TTS...")
        return await _synthesize_google(text)

async def _synthesize_elevenlabs(text: str) -> bytes:
    try:
        headers = {
            "xi-api-key": ELEVENLABS_API_KEY,
            "Content-Type": "application/json"
        }
        payload = {
            "text": text,
            "model_id": "eleven_multilingual_v2",
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75,
                "style": 0.3,
                "use_speaker_boost": True
            }
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(ELEVENLABS_TTS_URL, headers=headers, json=payload)
            response.raise_for_status()
            
        audio_bytes = response.content
        logger.info(f"Аудио получено от ElevenLabs | размер: {len(audio_bytes)} байт")
        return audio_bytes
        
    except Exception as e:
        logger.error(f"Ошибка ElevenLabs TTS: {e}")
        # Фолбэк на Google если ElevenLabs упал (например закончились лимиты)
        logger.info("Пробуем фолбэк на Google TTS...")
        return await _synthesize_google(text)

async def _synthesize_google(text: str) -> bytes:
    try:
        payload = {
            "input": {"text": text},
            "voice": {
                "languageCode": "he-IL",
                "name": "he-IL-Wavenet-D",
            },
            "audioConfig": {
                "audioEncoding": "MP3",
                "speakingRate": 0.95,
                "pitch": -2.0,
            },
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(GOOGLE_TTS_URL, json=payload)
            response.raise_for_status()

        result = response.json()
        audio_bytes = base64.b64decode(result["audioContent"])
        logger.info(f"Аудио получено от Google TTS | размер: {len(audio_bytes)} байт")
        return audio_bytes

    except Exception as e:
        logger.error(f"Ошибка при синтезе речи Google: {e}")
        raise
