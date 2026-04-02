"""
Сервис Voice Activity Detection — определяет когда пользователь замолчал.
Записывает аудио через sounddevice и использует webrtcvad для детекции тишины.
Когда тишина > silence_threshold — запись останавливается.
"""

import io
import struct
import threading
import time
import wave
from typing import Optional

import numpy as np
from loguru import logger

try:
    import sounddevice as sd
except OSError as e:
    sd = None
    logger.warning(f"sounddevice недоступен: {e}")

try:
    import webrtcvad
except ImportError:
    webrtcvad = None
    logger.warning("webrtcvad не установлен — VAD недоступен")


# Параметры аудио
SAMPLE_RATE = 16000        # 16 кГц — требование webrtcvad
CHANNELS = 1               # моно
SAMPLE_WIDTH = 2           # 16-bit (2 байта на семпл)


class VoiceActivityDetector:
    """
    Записывает голос пользователя и автоматически останавливается
    когда обнаруживает длительную тишину.
    """

    def __init__(
        self,
        aggressiveness: int = 2,
        silence_threshold: float = 1.5,
        sample_rate: int = SAMPLE_RATE,
        frame_duration: int = 30,
    ):
        """
        Инициализация VAD.

        Args:
            aggressiveness: Агрессивность фильтрации (0-3, где 3 — самый агрессивный)
            silence_threshold: Секунд тишины для автоматической остановки записи
            sample_rate: Частота дискретизации (должна быть 8000, 16000, 32000 или 48000)
            frame_duration: Длительность фрейма в мс (10, 20 или 30)
        """
        self._aggressiveness = aggressiveness
        self._silence_threshold = silence_threshold
        self._sample_rate = sample_rate
        self._frame_duration = frame_duration
        self._frame_samples = int(sample_rate * frame_duration / 1000)
        self._is_recording = False
        self._audio_frames: list[bytes] = []
        self._stream: Optional[sd.InputStream] = None
        self._record_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._recording_done = threading.Event()

        # Создаём VAD
        self._vad = None
        if webrtcvad is not None:
            self._vad = webrtcvad.Vad(aggressiveness)

        logger.info(
            f"VoiceActivityDetector создан | "
            f"aggressiveness={aggressiveness} | "
            f"silence={silence_threshold}s | "
            f"frame={frame_duration}ms"
        )

    @property
    def is_recording(self) -> bool:
        """Идёт ли запись прямо сейчас."""
        return self._is_recording

    def start_recording(self) -> None:
        """
        Начинает запись аудио. Запись автоматически остановится
        когда будет обнаружена тишина дольше silence_threshold.
        """
        if self._is_recording:
            logger.warning("Запись уже идёт")
            return

        if sd is None:
            logger.error("sounddevice недоступен — запись невозможна")
            return

        if self._vad is None:
            logger.error("webrtcvad не установлен — запись невозможна")
            return

        self._audio_frames = []
        self._stop_event.clear()
        self._recording_done.clear()
        self._is_recording = True

        self._record_thread = threading.Thread(
            target=self._record_loop,
            daemon=True,
            name="vad-recorder",
        )
        self._record_thread.start()
        logger.info("🎤 Начинаю запись — говорите...")

    def stop_recording(self) -> bytes:
        """
        Останавливает запись и возвращает аудио в формате WAV.

        Returns:
            bytes: Аудио данные в формате WAV (16-bit, 16kHz, mono).
        """
        if not self._is_recording and not self._audio_frames:
            logger.warning("Нет записи для остановки")
            return b""

        # Если запись ещё идёт — принудительно останавливаем
        self._stop_event.set()

        # Ждём завершения потока записи
        if self._record_thread is not None:
            self._record_thread.join(timeout=3.0)
            self._record_thread = None

        self._is_recording = False

        # Собираем все фреймы в WAV
        if not self._audio_frames:
            logger.warning("Запись пуста — нет аудио данных")
            return b""

        wav_bytes = self._frames_to_wav(self._audio_frames)
        duration = len(self._audio_frames) * self._frame_duration / 1000
        logger.info(
            f"✅ Запись завершена | "
            f"длительность: {duration:.1f}с | "
            f"размер WAV: {len(wav_bytes)} байт"
        )
        return wav_bytes

    def wait_for_silence(self, timeout: float = 30.0) -> bytes:
        """
        Блокирующий метод: ждёт пока VAD не обнаружит тишину,
        затем возвращает записанное аудио.

        Args:
            timeout: Максимальное время ожидания в секундах.

        Returns:
            bytes: Аудио данные в формате WAV.
        """
        if not self._is_recording:
            self.start_recording()

        # Ждём сигнал от _record_loop что запись закончена
        self._recording_done.wait(timeout=timeout)

        return self.stop_recording()

    def _record_loop(self) -> None:
        """Основной цикл записи с VAD (работает в отдельном потоке)."""
        import queue
        
        audio_queue = queue.Queue()
        
        def audio_callback(indata, frames, time_info, status):
            if status:
                logger.warning(f"VAD Audio status: {status}")
            audio_queue.put(bytes(indata))
            
        try:
            self._stream = sd.InputStream(
                samplerate=self._sample_rate,
                channels=CHANNELS,
                dtype="int16",
                blocksize=self._frame_samples,
                callback=audio_callback
            )
            self._stream.start()
            logger.debug(f"Аудио поток открыт для записи | {self._sample_rate}Hz")

            silence_frames = 0
            frames_for_threshold = int(
                self._silence_threshold / (self._frame_duration / 1000)
            )
            speech_detected = False

            while not self._stop_event.is_set():
                try:
                    frame_bytes = audio_queue.get(timeout=0.5)
                except queue.Empty:
                    continue

                # Сохраняем фрейм
                self._audio_frames.append(frame_bytes)

                # Проверяем голосовую активность
                is_speech = self._vad.is_speech(
                    frame_bytes, self._sample_rate
                )

                if is_speech:
                    speech_detected = True
                    silence_frames = 0
                else:
                    silence_frames += 1

                # Если была речь и потом тишина > порога — заканчиваем
                if speech_detected and silence_frames >= frames_for_threshold:
                    logger.info(
                        f"🔇 Обнаружена тишина > {self._silence_threshold}с — "
                        f"завершаю запись"
                    )
                    self._recording_done.set()
                    break

        except Exception as e:
            if not self._stop_event.is_set():
                logger.error(f"Ошибка в цикле записи VAD: {e}")
        finally:
            if self._stream is not None:
                try:
                    self._stream.stop()
                    self._stream.close()
                except Exception:
                    pass
                self._stream = None
            self._is_recording = False

    def _frames_to_wav(self, frames: list[bytes]) -> bytes:
        """
        Конвертирует список PCM фреймов в WAV файл в памяти.

        Args:
            frames: Список байтовых фреймов (16-bit PCM).

        Returns:
            bytes: Полный WAV файл в байтах.
        """
        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as wf:
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(SAMPLE_WIDTH)
            wf.setframerate(self._sample_rate)
            for frame in frames:
                wf.writeframes(frame)

        buffer.seek(0)
        return buffer.read()
