"""
Сервис для работы с LLM (Claude или Gemini).
Отправляет сообщения и получает ответы на иврите.
Выбор провайдера через переменную LLM_PROVIDER.
"""

import os
from dotenv import load_dotenv
from loguru import logger

# Загружаем переменные окружения
load_dotenv()

# Выбор провайдера: "gemini" (по умолчанию) или "anthropic"
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini").lower()

# Системный промпт на иврите
SYSTEM_PROMPT = (
    "אתה עוזר קולי בשם תומר.\n"
    "אתה ישראלי אמיתי - מדבר עברית טבעית, מודרנית וחברותית.\n"
    "השתמש בביטויים ישראליים אמיתיים כמו: \"סבבה\", \"יאללה\", \"ממש\", \"אחלה\".\n"
    "תשובות קצרות - 1-2 משפטים בלבד. הן יושמעו בקול.\n"
    "אל תהיה רשמי מדי - דבר כמו חבר.\n"
    "אם שואלים בעברית - ענה בעברית.\n"
    "אם שואלים ברוסית - ענה ברוסית."
)

MAX_TOKENS = 300  # Короткие ответы — будут озвучены голосом


# === Инициализация клиентов ===

if LLM_PROVIDER == "gemini":
    import google.generativeai as genai
    from tools.weather import get_weather_sync as get_weather

    genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
    gemini_model = genai.GenerativeModel(
        model_name="gemini-2.5-flash",
        system_instruction=SYSTEM_PROMPT,
        tools=[get_weather],
        generation_config=genai.GenerationConfig(
            max_output_tokens=MAX_TOKENS,
        ),
    )
    logger.info("🤖 LLM провайдер: Google Gemini (gemini-2.5-flash) с инструментами (get_weather)")

elif LLM_PROVIDER == "anthropic":
    from anthropic import AsyncAnthropic

    anthropic_client = AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    ANTHROPIC_MODEL = "claude-3-5-haiku-20241022"
    logger.info(f"🤖 LLM провайдер: Anthropic Claude ({ANTHROPIC_MODEL})")

else:
    raise ValueError(f"Неизвестный LLM_PROVIDER: {LLM_PROVIDER}. Используй 'gemini' или 'anthropic'.")


# === Функции отправки сообщений ===

async def _send_gemini(user_text: str, history: list[dict]) -> str:
    """
    Отправляет сообщение через Google Gemini API.

    Args:
        user_text: Текст от пользователя.
        history: История в формате [{"role": "user"|"assistant", "content": "..."}].

    Returns:
        Текст ответа от Gemini.
    """
    # Конвертируем историю в формат Gemini
    gemini_history = []
    for msg in history:
        gemini_history.append({
            "role": "model" if msg["role"] == "assistant" else "user",
            "parts": [msg["content"]],
        })

    # Создаём чат с историей
    chat = gemini_model.start_chat(
        history=gemini_history,
        enable_automatic_function_calling=True
    )

    # Отправляем сообщение (async)
    response = await chat.send_message_async(user_text)

    # Поскольку могут быть вызовы функций, итоговые токены берём из последнего ответа
    logger.info(
        f"Ответ от Gemini получен | "
        f"tokens: {response.usage_metadata.prompt_token_count}→{response.usage_metadata.candidates_token_count}"
    )

    return response.text


async def _send_anthropic(user_text: str, history: list[dict]) -> str:
    """
    Отправляет сообщение через Anthropic Claude API.

    Args:
        user_text: Текст от пользователя.
        history: История в формате [{"role": "user"|"assistant", "content": "..."}].

    Returns:
        Текст ответа от Claude.
    """
    messages = [*history, {"role": "user", "content": user_text}]

    response = await anthropic_client.messages.create(
        model=ANTHROPIC_MODEL,
        max_tokens=MAX_TOKENS,
        system=SYSTEM_PROMPT,
        messages=messages,
    )

    assistant_text = response.content[0].text

    logger.info(
        f"Ответ от Claude получен | "
        f"tokens: {response.usage.input_tokens}→{response.usage.output_tokens}"
    )

    return assistant_text


# === Главная функция ===

async def send_message(user_text: str, history: list[dict]) -> str:
    """
    Отправляет сообщение в LLM и возвращает ответ.
    Провайдер выбирается через переменную LLM_PROVIDER.

    Args:
        user_text: Текст сообщения от пользователя (на иврите).
        history: История разговора в формате [{"role": "user"|"assistant", "content": "..."}].

    Returns:
        Текст ответа ассистента на иврите.

    Raises:
        Exception: При ошибке вызова API.
    """
    try:
        logger.debug(f"Отправляю запрос в {LLM_PROVIDER} | сообщений: {len(history) + 1}")

        if LLM_PROVIDER == "gemini":
            return await _send_gemini(user_text, history)
        else:
            return await _send_anthropic(user_text, history)

    except Exception as e:
        logger.error(f"Ошибка при вызове {LLM_PROVIDER} API: {e}")
        raise
