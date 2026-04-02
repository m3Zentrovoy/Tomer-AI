"""
Сервис Gemini Live — голосовой ввод/вывод через Gemini 2.5 Flash Native Audio.
Один WebSocket вместо цепочки STT → LLM → TTS.
"""

from google import genai
from google.genai import types
from loguru import logger
import os
import io
import wave

TOMER_SYSTEM_PROMPT = """
אתה עוזר קולי בשם תומר.
אתה ישראלי אמיתי - מדבר עברית טבעית וחברותית.
השתמש בביטויים: סבבה, יאללה, אחלה, וואלה.
תשובות קצרות - 1-2 משפטים בלבד. הן יושמעו בקול.
דבר כמו חבר טוב, לא כמו רובוט.
אם שואלים בעברית - ענה בעברית.
אם שואלים ברוסית - ענה ברוסית.
"""


class GeminiLiveService:
    """Сервис для работы с Gemini Live API — аудио вход → аудио выход."""
    
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            logger.error("❌ Нет API ключа! Установи GEMINI_API_KEY или GOOGLE_API_KEY в .env")
        self.model = "gemini-2.5-flash-native-audio-latest"
        self.client = genai.Client(api_key=self.api_key)
        logger.info(f"🔑 GeminiLiveService | модель: {self.model}")
    
    def _to_pcm(self, audio_bytes: bytes) -> tuple[bytes, int]:
        """Извлекает RAW PCM из любого формата (WEBM/WAV) используя pydub."""
        import pydub
        import io
        try:
            # Читаем WEBM из браузера, конвертируем в 16kHz, mono, 16-bit
            audio = pydub.AudioSegment.from_file(io.BytesIO(audio_bytes))
            audio = audio.set_frame_rate(16000).set_channels(1).set_sample_width(2)
            return audio.raw_data, 16000
        except Exception as e:
            logger.error(f"❌ Ошибка декодирования WEBM: {e}")
            # Возвращаем как есть (хуже не будет, если это уже pcm)
            return audio_bytes, 16000
    
    async def send_audio(self, audio_bytes: bytes) -> bytes:
        """
        Отправляет аудио в Gemini Live и получает аудио ответ.
        Вход: WAV или PCM байты от микрофона
        Выход: PCM байты ответа (24kHz, 16-bit, mono)
        """
        config = types.LiveConnectConfig(
            response_modalities=["AUDIO"],
            system_instruction=types.Content(parts=[types.Part(text=TOMER_SYSTEM_PROMPT)]),
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name="Puck"  # Мужской, дружелюбный голос (Tomer)
                    )
                )
            )
        )
        
        # Конвертируем WEBM (от браузера) → RAW PCM для Gemini
        pcm_data, sample_rate = self._to_pcm(audio_bytes)
        
        try:
            audio_chunks = []
            
            async with self.client.aio.live.connect(
                model=self.model,
                config=config
            ) as session:
                
                logger.info(f"🔴 Gemini Live подключён | PCM: {len(pcm_data)} байт @ {sample_rate}Hz")
                
                # Отправляем PCM аудио (новый API)
                await session.send_realtime_input(
                    audio=types.Blob(
                        data=pcm_data,
                        mime_type=f"audio/pcm;rate={sample_rate}"
                    )
                )
                
                # Отправляем текстовый контекст для триггера ответа
                await session.send_client_content(
                    turns=[types.Content(parts=[types.Part(text="Respond to this audio in Hebrew.")])],
                    turn_complete=True
                )
                
                logger.info("📤 Аудио отправлено, жду ответ...")
                
                # Получаем ответ
                async for response in session.receive():
                    
                    # Транскрипции
                    if response.server_content:
                        sc = response.server_content
                        if hasattr(sc, 'input_transcription') and sc.input_transcription:
                            logger.info(f"📝 Пользователь сказал: {sc.input_transcription.text}")
                        if hasattr(sc, 'output_transcription') and sc.output_transcription:
                            logger.info(f"🤖 Томер отвечает: {sc.output_transcription.text}")
                        
                        # Аудио чанки из model_turn
                        if hasattr(sc, 'model_turn') and sc.model_turn:
                            for part in sc.model_turn.parts:
                                if hasattr(part, 'inline_data') and part.inline_data:
                                    audio_chunks.append(part.inline_data.data)
                        
                        # Конец ответа
                        if hasattr(sc, 'turn_complete') and sc.turn_complete:
                            logger.info("✅ Ответ получен полностью")
                            break
                    
                    # Прямые данные
                    if response.data:
                        audio_chunks.append(response.data)
            
            if not audio_chunks:
                logger.warning("⚠️ Gemini Live не вернул аудио")
                return b""
            
            result = b"".join(audio_chunks)
            logger.info(f"🎵 Размер аудио ответа: {len(result)} байт | чанков: {len(audio_chunks)}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Ошибка Gemini Live: {e}")
            raise
