"""
Роутер для голосовых API.
POST /api/stt — аудио → текст (Google STT, fallback)
POST /api/tts — текст → аудио (Narakeet, fallback)
POST /api/live-chat — полный голосовой цикл через Gemini Live
"""

from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse, Response
from pydantic import BaseModel, Field
from loguru import logger
import io
import traceback

from services.stt import transcribe_audio
from services.tts import synthesize_speech
from services.gemini_live import GeminiLiveService

router = APIRouter()
gemini_live_service = GeminiLiveService()


# === Pydantic модели ===

class STTResponse(BaseModel):
    text: str = Field(..., description="Транскрипция аудио на иврите")


class TTSRequest(BaseModel):
    text: str = Field(..., min_length=1, description="Текст для озвучки на иврите")


# === Эндпоинты ===

@router.post("/stt", response_model=STTResponse)
async def speech_to_text(file: UploadFile = File(...)):
    """Fallback STT — аудио → текст через Google Cloud."""
    try:
        audio_bytes = await file.read()
        mime_type = file.content_type or "audio/webm"

        logger.info(f"🎤 STT запрос | файл: {file.filename}, тип: {mime_type}, размер: {len(audio_bytes)} байт")

        if len(audio_bytes) == 0:
            raise HTTPException(status_code=400, detail="קובץ שמע ריק")

        text = await transcribe_audio(audio_bytes, mime_type)
        logger.info(f"✅ STT результат: {text[:50]}...")
        return STTResponse(text=text)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Ошибка в /api/stt: {e}")
        logger.error(f"📋 Traceback:\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"שגיאה בזיהוי דיבור: {str(e)}")


@router.post("/tts")
async def text_to_speech(request: TTSRequest):
    """Fallback TTS — текст → MP3 через Narakeet."""
    try:
        logger.info(f"🔊 TTS запрос | текст: {request.text[:50]}...")
        audio_bytes = await synthesize_speech(request.text)
        logger.info(f"✅ TTS результат | размер: {len(audio_bytes)} байт")

        return StreamingResponse(
            io.BytesIO(audio_bytes),
            media_type="audio/mpeg",
            headers={"Content-Disposition": "attachment; filename=response.mp3"},
        )

    except Exception as e:
        logger.error(f"❌ Ошибка в /api/tts: {e}")
        raise HTTPException(status_code=500, detail="שגיאה ביצירת דיבור. נסה שוב.")


@router.post("/live-chat")
async def live_chat(audio: UploadFile = File(...)):
    """
    Полный голосовой цикл через Gemini Live.
    Вход: аудио файл (WAV/WebM)
    Выход: аудио PCM ответ для воспроизведения
    """
    try:
        logger.info(f"🎙️ Live chat: получен файл {audio.filename}")
        audio_bytes = await audio.read()

        if len(audio_bytes) == 0:
            raise HTTPException(status_code=400, detail="קובץ שמע ריק")

        response_audio = await gemini_live_service.send_audio(audio_bytes)

        if not response_audio:
            # Если Gemini промолчал, возвращаем пустой PCM вместо 500 ошибки
            return Response(status_code=204)

        return Response(
            content=response_audio,
            media_type="audio/pcm",
            headers={"X-Sample-Rate": "24000"},
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Ошибка live-chat: {e}")
        raise HTTPException(status_code=500, detail="שגיאה בעיבוד הבקשה")
