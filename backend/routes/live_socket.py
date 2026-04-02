"""
WebSocket роутер для прямого подключения (Стриминг) к Gemini Live API.
Позволяет Frontend-у поддерживать постоянную сессию и не 'забывать' контекст каждые 5 сек.
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from loguru import logger
from google import genai
from google.genai import types
import os
import asyncio
import json
import uuid
from datetime import datetime

router = APIRouter()

async def log_conversation(session_id: str, role: str, text: str):
    """Асинхронно сохраняет реплики в JSONL лог-файл с привязкой к сессии"""
    record = {
        "timestamp": datetime.now().isoformat(),
        "session_id": session_id,
        "role": role,
        "text": text
    }
    def _write():
        os.makedirs("logs", exist_ok=True)
        with open("logs/conversations.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    # Используем to_thread, чтобы не блокировать event loop
    await asyncio.to_thread(_write)

TOMER_SYSTEM_PROMPT = """
אתה עוזר קולי חכם בשם תומר. אתה מתנהג כמו "אליסה" (Yandex Alice) אבל בגרסה ישראלית חברותית וטיפה שנונה.
כללים חשובים:
1. ענה תמיד תשובות קצרות מאוד (משפט אחד או שניים גג). 
2. אל תיתן רשימות, נתונים ארוכים או חפירות. במקום זה: תן שורה תחתונה וזרוק איזו בדיחה קטנה או מילה ישראלית (כמו 'סבבה', 'יאללה', 'אחי', 'תכלס').
3. אם מבקשים מזג אוויר: ציין רק את הטמפרטורה הנוכחית ואולי רמז קטן למחר אם זה רלוונטי, ותוסיף הערה מצחיקה (למשל: "25 מעלות אחי, קח כפכפים משקפי שמש ויאללה לים!"). 
4. אתה בשיחת קול חיה. חשוב מאוד: דבר לאט מאוד, ברור ורגוע (פי 2 יותר לאט מהרגיל). זה עבור אנשים שלומדים עברית - קצב איטי הוא קריטי.
"""

@router.websocket("/ws/live-chat")
async def websocket_live_chat(websocket: WebSocket):
    await websocket.accept()
    session_id = str(uuid.uuid4())[:8]  # Короткий ID для удобства чтения
    logger.info(f"🟢 WebSocket подключён для Gemini Live стриминга [session={session_id}]")
    await log_conversation(session_id, "system", "Тестировщик подключился")
    
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    client = genai.Client(api_key=api_key)
    
    from tools.weather import get_weather
    
    config = types.LiveConnectConfig(
        tools=[get_weather],
        response_modalities=["AUDIO"],
        system_instruction=types.Content(parts=[types.Part(text=TOMER_SYSTEM_PROMPT)]),
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Puck")
            )
        ),
        # Включаем транскрипции для логирования разговоров тестировщиков
        input_audio_transcription=types.AudioTranscriptionConfig(),
        output_audio_transcription=types.AudioTranscriptionConfig(),
    )
    
    try:
        async with client.aio.live.connect(model="gemini-2.5-flash-native-audio-latest", config=config) as session:
            logger.info("🚀 Gemini Live session открыта!")
            
            async def receive_from_client_and_send_to_gemini():
                try:
                    chunk_count = 0
                    while True:
                        data = await websocket.receive_bytes()
                        if not data:
                            continue
                        chunk_count += 1
                        if chunk_count % 10 == 0:
                            logger.debug(f"🎙️ Получено {len(data)} байт аудио от браузера (chunk #{chunk_count})")
                        # Получаем сырые PCM 16kHz данные от браузера
                        await session.send_realtime_input(
                            audio=types.Blob(data=data, mime_type="audio/pcm;rate=16000")
                        )
                except WebSocketDisconnect:
                    logger.info("🔌 Клиент отключился (WebSocketDisconnect)")
                except asyncio.CancelledError:
                    logger.debug("❌ receive_from_client ОТМЕНЕНА")
                except Exception as e:
                    logger.error(f"❌ Ошибка получения от браузера: {e}", exc_info=True)
                finally:
                    logger.warning("🔚 Задача: receive_from_client ЗАВЕРШЕНА")

            async def receive_from_gemini_and_send_to_client():
                try:
                    while True:
                        async for response in session.receive():
                            # Обработка server_content (транскрипции, перебивания, аудио)
                            if getattr(response, 'server_content', None):
                                sc = response.server_content
                                
                                # 1. Проверка на то, что модель прервали
                                if getattr(sc, "interrupted", False):
                                    logger.info("🛑 Gemini понял, что его перебили!")
                                    await websocket.send_text("INTERRUPT")
                                
                                # 2. Сохраняем текстовые транскрипции в файл
                                if hasattr(sc, 'input_transcription') and sc.input_transcription:
                                    if hasattr(sc.input_transcription, 'text') and sc.input_transcription.text:
                                        user_text = sc.input_transcription.text
                                        logger.info(f"📝 Пользователь сказал: {user_text}")
                                        await log_conversation(session_id, "user", user_text)
                                        
                                if hasattr(sc, 'output_transcription') and sc.output_transcription:
                                    if hasattr(sc.output_transcription, 'text') and sc.output_transcription.text:
                                        tomer_text = sc.output_transcription.text
                                        logger.info(f"🤖 Томер отвечает: {tomer_text}")
                                        await log_conversation(session_id, "tomer", tomer_text)
                                
                                # 3. Аудио данные от модели
                                if getattr(sc, 'model_turn', None):
                                    for part in sc.model_turn.parts:
                                        if getattr(part, 'inline_data', None) and getattr(part.inline_data, 'data', None):
                                            await websocket.send_bytes(part.inline_data.data)
                            elif getattr(response, 'data', None):
                                await websocket.send_bytes(response.data)
                                
                            # Обработка вызовов функций (Tool calling)
                            if getattr(response, 'tool_call', None):
                                logger.info(f"🛠️ Gemini вызывает инструменты: {response.tool_call}")
                                function_responses = []
                                
                                for fc in response.tool_call.function_calls:
                                    logger.info(f"⏩ Выполняю функцию {fc.name} с аргументами: {fc.args}")
                                    try:
                                        if fc.name == "get_weather":
                                            from tools.weather import get_weather
                                            res_text = await get_weather(**fc.args)
                                        else:
                                            res_text = f"Неизвестный навык: {fc.name}"
                                    except Exception as e:
                                        logger.error(f"Ошибка функции {fc.name}: {e}")
                                        res_text = f"Ошибка: {e}"
                                        
                                    logger.info(f"✅ Результат выполнения {fc.name}: {res_text}")
                                    function_responses.append(
                                        types.FunctionResponse(
                                            id=fc.id,
                                            name=fc.name,
                                            response={"result": res_text}
                                        )
                                    )
                                
                                # Отправляем результат обратно в Gemini Live
                                await session.send_tool_response(function_responses=function_responses)
                        
                        logger.warning("♻️ session.receive() завершил цикл. Начинаю следующий цикл ожиданий...")
                        await asyncio.sleep(0.1) # Защита от бесконечного цикла
                except asyncio.CancelledError:
                    logger.debug("❌ receive_from_gemini ОТМЕНЕНА")
                except Exception as e:
                    logger.error(f"❌ Ошибка получения от Gemini: {e}", exc_info=True)
                finally:
                    logger.warning("🔚 Задача: receive_from_gemini ЗАВЕРШЕНА")

            # Две задачи крутятся параллельно (дуплекс)
            t1 = asyncio.create_task(receive_from_client_and_send_to_gemini())
            t2 = asyncio.create_task(receive_from_gemini_and_send_to_client())
            
            done, pending = await asyncio.wait([t1, t2], return_when=asyncio.FIRST_COMPLETED)
            logger.info(f"🔄 Сработал выход из wait. Выполнено: {[task.get_name() for task in done]}")
            for p in pending:
                p.cancel()
                
    except Exception as e:
        logger.error(f"❌ Критическая ошибка WebSocket сессии: {e}", exc_info=True)
    finally:
        try:
            await websocket.close()
            logger.info("🔴 WebSocket закрыт")
        except:
            pass
