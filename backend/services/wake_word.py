"""
Сервис Wake Word Detection — детектирует "hey tomer" через openwakeword.
Постоянно слушает микрофон и вызывает callback при обнаружении фразы.

Пока используем модель "hey_jarvis" как placeholder,
пока не обучим кастомную модель для "הי תומר".
"""

import asyncio
import threading
import numpy as np
from typing import Callable, Optional

from loguru import logger

try:
    import sounddevice as sd
except OSError as e:
    sd = None
    logger.warning(f"sounddevice недоступен (нет физического микрофона?): {e}")

try:
    import openwakeword
    from openwakeword.model import Model as OWWModel
except ImportError:
    OWWModel = None
    logger.warning("openwakeword не установлен — wake word детекция недоступна")


# Параметры аудио (требования openwakeword)
SAMPLE_RATE = 16000       # 16 кГц
FRAME_MS = 80             # 80 мс фреймы — оптимально для openwakeword
FRAME_SAMPLES = int(SAMPLE_RATE * FRAME_MS / 1000)  # 1280 семплов
CHANNELS = 1              # моно

# Модель wake word (placeholder — потом заменим на кастомную "הי תומר")
WAKEWORD_MODEL = "alexa"


class WakeWordDetector:
    """
    Детектор wake word через openwakeword.
    Постоянно слушает микрофон и вызывает callback при обнаружении фразы.
    """

    def __init__(
        self,
        on_wake: Optional[Callable[[], None]] = None,
        threshold: float = 0.4,
        model_name: str = WAKEWORD_MODEL,
    ):
        """
        Инициализация детектора.

        Args:
            on_wake: callback функция, вызываемая при детекции wake word
            threshold: порог срабатывания (0.0 - 1.0)
            model_name: имя модели openwakeword
        """
        self._on_wake = on_wake
        self._threshold = threshold
        self._model_name = model_name
        self._is_listening = False
        self._stream: Optional[sd.InputStream] = None
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._model: Optional[OWWModel] = None
        self._cooldown_seconds = 2.0  # минимум 2 сек между срабатываниями
        self._last_detection_time = 0.0

        logger.info(
            f"WakeWordDetector создан | модель: {model_name} | порог: {threshold}"
        )

    @property
    def is_listening(self) -> bool:
        """Слушает ли детектор микрофон прямо сейчас."""
        return self._is_listening

    def start(self) -> None:
        """Запускает прослушивание микрофона в фоновом потоке."""
        if self._is_listening:
            logger.warning("Детектор уже слушает")
            return

        if sd is None:
            logger.error("sounddevice недоступен — невозможно запустить детектор")
            return

        if OWWModel is None:
            logger.error("openwakeword не установлен — невозможно запустить детектор")
            return

        try:
            # Скачиваем модели при первом запуске
            openwakeword.utils.download_models()

            # Создаём модель
            self._model = OWWModel(
                wakeword_models=[self._model_name],
                inference_framework="onnx",
            )
            logger.info(f"Модель {self._model_name} загружена")

        except Exception as e:
            logger.error(f"Ошибка загрузки модели wake word: {e}")
            return

        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._listen_loop,
            daemon=True,
            name="wake-word-listener",
        )
        self._thread.start()
        self._is_listening = True
        logger.info("🎙️ Wake word детектор запущен — слушаю микрофон...")

    def stop(self) -> None:
        """Останавливает прослушивание микрофона."""
        if not self._is_listening:
            logger.warning("Детектор не запущен")
            return

        self._stop_event.set()

        if self._stream is not None:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception as e:
                logger.debug(f"Ошибка при закрытии аудио потока: {e}")
            self._stream = None

        if self._thread is not None:
            self._thread.join(timeout=3.0)
            self._thread = None

        self._is_listening = False
        self._model = None
        logger.info("🔇 Wake word детектор остановлен")

    def _listen_loop(self) -> None:
        """Основной цикл прослушивания микрофона (работает в отдельном потоке)."""
        import time
        import queue
        
        audio_queue = queue.Queue()
        
        def audio_callback(indata, frames, time_info, status):
            if status:
                logger.warning(f"WakeWord Audio status: {status}")
            audio_queue.put(bytes(indata))

        try:
            self._stream = sd.InputStream(
                samplerate=SAMPLE_RATE,
                channels=CHANNELS,
                dtype="int16",
                blocksize=FRAME_SAMPLES,
                callback=audio_callback
            )
            self._stream.start()
            logger.debug(
                f"Аудио поток открыт | rate={SAMPLE_RATE} | frame={FRAME_MS}ms"
            )

            while not self._stop_event.is_set():
                try:
                    frame_bytes = audio_queue.get(timeout=0.5)
                except queue.Empty:
                    continue

                # Конвертируем в 1D numpy array (int16)
                frame_data = np.frombuffer(frame_bytes, dtype=np.int16)

                # Получаем предсказание от модели
                prediction = self._model.predict(frame_data)

                # Проверяем каждый ключ в предсказании
                for wake_word, score in prediction.items():
                    if score >= self._threshold:
                        current_time = time.time()

                        # Кулдаун — не срабатывать слишком часто
                        if (
                            current_time - self._last_detection_time
                            < self._cooldown_seconds
                        ):
                            continue

                        self._last_detection_time = current_time
                        logger.info(
                            f"🔔 Wake word детектирован! "
                            f"| слово: {wake_word} | уверенность: {score:.3f}"
                        )

                        # Сбрасываем скоры модели для чистого старта
                        self._model.reset()

                        # Вызываем callback
                        if self._on_wake is not None:
                            try:
                                self._on_wake()
                            except Exception as e:
                                logger.error(f"Ошибка в on_wake callback: {e}")

        except Exception as e:
            if not self._stop_event.is_set():
                logger.error(f"Ошибка в цикле прослушивания: {e}")
        finally:
            self._is_listening = False
            logger.debug("Цикл прослушивания завершён")
