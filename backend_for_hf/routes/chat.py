"""
Роутер для текстового чата с ассистентом.
Эндпоинт POST /api/chat — принимает сообщение, возвращает ответ.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from loguru import logger

from services.llm import send_message

router = APIRouter()


# === Pydantic модели ===

class ChatMessage(BaseModel):
    """Одно сообщение в истории разговора."""
    role: str = Field(..., description="Роль: 'user' или 'assistant'")
    content: str = Field(..., description="Текст сообщения")


class ChatRequest(BaseModel):
    """Запрос к чату."""
    message: str = Field(..., min_length=1, description="Текст сообщения от пользователя")
    history: list[ChatMessage] = Field(default=[], description="История разговора")


class ChatResponse(BaseModel):
    """Ответ от чата."""
    response: str = Field(..., description="Текст ответа ассистента")
    history: list[ChatMessage] = Field(..., description="Обновлённая история разговора")


# === Эндпоинт ===

@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Принимает сообщение пользователя и возвращает ответ ассистента.

    Обновляет историю разговора и возвращает её обратно клиенту,
    чтобы фронтенд мог передать её в следующем запросе.
    """
    try:
        logger.info(f"📩 Новое сообщение: {request.message[:50]}...")

        # Конвертируем историю в формат для Claude API
        history_dicts = [msg.model_dump() for msg in request.history]

        # Отправляем в Claude
        assistant_text = await send_message(request.message, history_dicts)

        # Обновляем историю: добавляем сообщение пользователя и ответ
        updated_history = [
            *request.history,
            ChatMessage(role="user", content=request.message),
            ChatMessage(role="assistant", content=assistant_text),
        ]

        logger.info(f"✅ Ответ отправлен | история: {len(updated_history)} сообщений")

        return ChatResponse(
            response=assistant_text,
            history=updated_history,
        )

    except Exception as e:
        logger.error(f"❌ Ошибка в /api/chat: {e}")
        raise HTTPException(
            status_code=500,
            detail="שגיאה בעיבוד הבקשה. נסה שוב.",  # Ошибка обработки. Попробуйте снова.
        )
