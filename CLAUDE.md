Tomer AI — Project Context
Что это за проект
Голосовой AI-ассистент на иврите — аналог Яндекс Алисы, только на иврите.
Работает как умная колонка: всегда слушает, просыпается по wake word "הי תומר",
понимает иврит, отвечает голосом как живой израильтянин.
Текущий MVP: веб-приложение + iOS приложение.
Следующий шаг: переехать на Raspberry Pi 5 (физическая колонка).

Текущий этап
Этап 5 из 8 — подключаем Gemini 2.0 Flash Live (STT + LLM + TTS в одном)

Что уже работает ✅

POST /api/chat — Gemini 3.1 Flash Lite, отвечает на иврите
POST /api/stt — Google Cloud Speech-to-Text (he-IL)
POST /api/tts — Narakeet API, голос Duncan (мужской, иврит)
Wake Word — openWakeWord (сейчас "hey jarvis" placeholder)
VAD — webrtcvad, автоопределение конца речи
Voice Pipeline — полный цикл колонки (wake → запись → STT → LLM → TTS)
Фронтенд Next.js — localhost:3000, iOS дизайн, кнопка "Режим колонки"
iOS/macOS SwiftUI приложение — собирается в Xcode

Что делаем сейчас 🔄

Подключаем Gemini 2.0 Flash Live API
Один WebSocket вместо STT + LLM + TTS (3 отдельных сервиса)
Цель: снизить latency с 3-4 сек до 0.5-1 сек


Архитектура: было vs стало
Было (медленно, 3-4 сек):
Голос → Google STT → Gemini LLM → Narakeet TTS → Звук
         (0.8с)       (1.0с)        (0.8с)
Стало (быстро, 0.5-1 сек):
Голос → Gemini 2.0 Flash Live → Звук
         (всё в одном WebSocket)

Технический стек
Бэкенд

Python 3.11, FastAPI, asyncio, uvicorn
LLM: Google Gemini (gemini-3.1-flash-lite) — fallback
LLM Live: gemini-2.0-flash-live-001 — основной
STT: Google Cloud Speech-to-Text (he-IL) — fallback
TTS: Narakeet API (голос duncan) — fallback
Wake Word: openwakeword
VAD: webrtcvad
Аудио: sounddevice, pyaudio
Live SDK: google-genai

Фронтенд

Next.js 14, TypeScript, Tailwind CSS
MediaRecorder API для записи голоса в браузере

iOS

SwiftUI, AVFoundation
Подключается к бэкенду по Wi-Fi


Структура проекта
Tomer AI/
├── CLAUDE.md
├── backend/
│   ├── main.py
│   ├── routes/
│   │   ├── chat.py                ← POST /api/chat
│   │   └── speech.py              ← POST /api/stt, /api/tts, /api/live-chat
│   ├── services/
│   │   ├── llm.py                 ← Gemini API (fallback)
│   │   ├── stt.py                 ← Google STT (fallback)
│   │   ├── tts.py                 ← Narakeet duncan (fallback)
│   │   ├── gemini_live.py         ← Gemini Live API ← ДЕЛАЕМ СЕЙЧАС
│   │   ├── wake_word.py           ← openWakeWord
│   │   ├── vad.py                 ← webrtcvad
│   │   └── voice_pipeline.py     ← полный цикл колонки
│   ├── tools/
│   │   └── weather.py             ← Open-Meteo (потом)
│   ├── .env
│   ├── .env.example
│   └── requirements.txt
├── frontend/                      ← Next.js веб версия
└── ios-app/                       ← SwiftUI iOS версия

Переменные окружения (.env)
GEMINI_API_KEY=
GEMINI_MODEL=gemini-3.1-flash-lite
GOOGLE_CLOUD_API_KEY=
NARAKEET_API_KEY=
TTS_PROVIDER=narakeet
VOICE_PIPELINE_ENABLED=false
LIVE_API_ENABLED=false

Системный промпт Томера
אתה עוזר קולי בשם תומר.
אתה ישראלי אמיתי - מדבר עברית טבעית, מודרנית וחברותית.
השתמש בביטויים ישראליים: סבבה, יאללה, ממש, אחלה, וואלה.
תשובות קצרות - 1-2 משפטים בלבד. הן יושמעו בקול.
דבר כמו חבר טוב, לא כמו רובוט או עוזר רשמי.
אם שואלים בעברית - ענה בעברית.
אם שואלים ברוסית - ענה ברוסית.

Правила кода

async/await везде
Комментарии в коде на русском языке
Ошибки пользователю на иврите
try/except в каждой функции с логированием
loguru для всех логов (не print)
Секреты только через .env


Запуск проекта
bash# Бэкенд (разработка)
cd backend && uvicorn main:app --reload --port 8000

# Бэкенд (для iPhone по Wi-Fi)
cd backend && uvicorn main:app --host 0.0.0.0 --port 8000

# Фронтенд
cd frontend && npm run dev

# IP мака для iPhone
ipconfig getifaddr en0

Все этапы проекта

✅ Этап 1: Бэкенд FastAPI + Gemini чат
✅ Этап 2: STT + TTS (Google + Narakeet)
✅ Этап 3: Фронтенд Next.js + iOS SwiftUI
✅ Этап 4: Wake Word + VAD + Voice Pipeline
🔄 Этап 5: Gemini 2.0 Flash Live (сейчас)
✅ Этап 6: Деплой Railway + Vercel (Завершено, работает в связке с GitHub)
⏳ Этап 7: Raspberry Pi 5 — физическая колонка
⏳ Этап 8: Home Assistant + Wolt интеграции








# проверка логов

cd "/Users/zentrovoy/Documents/Project AI/Tomer AI"
source backend/venv/bin/activate
python show_dialogs.py

python show_dialogs.py
