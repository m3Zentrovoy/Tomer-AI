"""
Voice Pipeline — полный голосовой цикл через Gemini Live.
Режим колонки: постоянно слушает через VAD → Gemini Live → динамик → повтор.
"""

import asyncio
import io
from typing import Optional

import numpy as np
from loguru import logger

try:
    import sounddevice as sd
except OSError:
    sd = None
    logger.warning("sounddevice недоступен")

from services.vad import VoiceActivityDetector
from services.gemini_live import GeminiLiveService


class VoicePipeline:
    """
    Голосовой пайплайн — режим колонки (без wake word).

    Бесконечный цикл:
    1. VAD записывает до тишины
    2. Отправляет в Gemini Live (аудио→аудио)
    3. Воспроизводит ответ
    4. Повторяет с шага 1
    """

    def __init__(self, vad_aggressiveness: int = 2, silence_threshold: float = 1.5):
        self._running = False
        self._vad = VoiceActivityDetector(
            aggressiveness=vad_aggressiveness,
            silence_threshold=silence_threshold,
        )
        self._gemini = GeminiLiveService()
        logger.info("🔧 VoicePipeline создан (Gemini Live, без wake word)")

    async def run_loop(self) -> None:
        """
        Бесконечный цикл: слушает → отвечает → слушает.
        Запускается как asyncio.Task из main.py.
        """
        self._running = True
        logger.info("🔁 VoicePipeline запущен в режиме колонки — слушаю постоянно...")

        try:
            while self._running:
                try:
                    await self._process_one_turn()
                except asyncio.CancelledError:
                    logger.info("VoicePipeline отменён")
                    break
                except Exception as e:
                    logger.error(f"❌ Ошибка в цикле: {e}")
                    await asyncio.sleep(1)  # Пауза перед повтором
        finally:
            self._running = False
            logger.info("👋 VoicePipeline остановлен")

    async def _process_one_turn(self) -> None:
        """Один цикл: запись → Gemini Live → воспроизведение."""
        
        # === Шаг 1: Записываем вопрос через VAD ===
        logger.info("🎤 Слушаю... (говорите)")
        audio_wav = await asyncio.to_thread(self._vad.wait_for_silence, 30.0)

        if not audio_wav or len(audio_wav) < 1000:
            logger.debug("Тишина — жду снова")
            return

        logger.info(f"📝 Записано аудио: {len(audio_wav)} байт")

        # === Шаг 2: Отправляем в Gemini Live ===
        logger.info("🚀 Отправляю в Gemini Live...")
        response_pcm = await self._gemini.send_audio(audio_wav)

        if not response_pcm:
            logger.warning("⚠️ Gemini Live не вернул аудио")
            return

        # === Шаг 3: Воспроизводим ответ ===
        logger.info(f"🎵 Воспроизвожу ответ | {len(response_pcm)} байт PCM")
        await asyncio.to_thread(self._play_pcm, response_pcm)
        
        # Пауза перед следующим циклом (чтобы не ловить эхо)
        await asyncio.sleep(0.5)

    async def run_once(self) -> None:
        """Один цикл — для совместимости."""
        self._running = True
        try:
            await self._process_one_turn()
        finally:
            self._running = False

    def stop(self) -> None:
        """Останавливает пайплайн."""
        if not self._running:
            return
        self._running = False
        if self._vad.is_recording:
            self._vad.stop_recording()
        logger.info("🛑 VoicePipeline: остановка запрошена")

    def _play_pcm(self, pcm_bytes: bytes, sample_rate: int = 24000) -> None:
        """Воспроизводит PCM аудио через sounddevice."""
        if sd is None:
            logger.warning("sounddevice недоступен — воспроизведение невозможно")
            return

        try:
            samples = np.frombuffer(pcm_bytes, dtype=np.int16).astype(np.float32)
            samples /= 32768.0
            sd.play(samples, samplerate=sample_rate)
            sd.wait()
            logger.info("✅ Воспроизведение завершено")
        except Exception as e:
            logger.error(f"❌ Ошибка воспроизведения: {e}")
