# 🇮🇱 Tomer AI: The Next-Gen Hebrew Voice Assistant

> **"Alice" for Israel.** A voice-first AI ecosystem that speaks, understands, and thinks like an Israeli.

---

## 🌟 Vision
**Tomer AI** is more than just a chatbot; it's a cultural bridging technology. While the world has Siri and Alexa, the Hebrew-speaking market has long suffered from high latency, robotic accents, and poor local understanding. 

Tomer AI solves this by combining **Gemini 2.0 Flash Live** with a custom-tuned "Israeli personality" to deliver the first sub-second latency, natural-speaking AI companion for the Israeli market.

---

## 🚀 Key Differentiators

### ⚡ Ultra-Low Latency (< 1s)
By leveraging a single-stream WebSocket connection (STT + LLM + TTS in one), we've cut response times from 4+ seconds to under 0.8 seconds. It feels like a real conversation, not a walkie-talkie.

### 🕍 Localized Intelligence
Tomer isn't just translating English to Hebrew. He uses Israeli slang (*sababa*, *yalla*, *achla*), understands local context, and switches seamlessly between Hebrew and Russian depending on the user's preference.

### 📱 Multi-Platform Ecosystem
*   **Web Dashboard:** High-performance Next.js interface for remote control and logging.
*   **iOS Native:** Full AVFoundation integration for mobile-first voice interaction.
*   **Physical Hardware (R&D):** Prototyping a Raspberry Pi 5-based smart speaker to replace the "dead" traditional smart home hubs.

---

## 🛠 Tech Stack (The "Secret Sauce")

*   **Brain:** Google Gemini 2.0 Flash Live (Multimodal Live API).
*   **Backend:** FastAPI (Python) optimized for high-concurrency WebSockets.
*   **Frontend:** Next.js 14 + Tailwind CSS (Premium aesthetics).
*   **Mobile:** SwiftUI + AVFoundation for low-level audio processing.
*   **Infrastructure:** Monorepo architecture deployed on **Railway** (Frontend) and **Hugging Face Spaces** (High-availability Docker backend).

---

## 📈 Roadmap

- [x] **Phase 1-4:** Core Voice Pipeline (STT/TTS/VAD/WakeWord).
- [x] **Phase 5:** Gemini Live Integration (Current).
- [ ] **Phase 6:** Public Beta Release (Railway + Vercel).
- [ ] **Phase 7:** **The Physical Speaker.** Production-ready Raspberry Pi 5 shell.
- [ ] **Phase 8:** **Local Integrations.** Wolt, Home Assistant, and Israeli banks/services.

---

## 🔒 Security & Performance
Built with enterprise-grade security protocols:
*   **Zero Leak Architecture:** All secrets managed via protected environment variables.
- **Scalable WebSockets:** Optimized for thousands of concurrent voice streams.
- **Privacy First:** Local speech processing (VAD/Wake Word) where possible.

---

## 🌍 Join the Revolution
We are building the future of Israeli interaction. Whether it's a smart home hub, a personal secretary, or an elderly care companion, Tomer AI is the infrastructure for a Hebrew-first voice economy.

**Interested in partnership or investment?**
[Contact via GitHub Profile]

---
*© 2026 Tomer AI. Built for Israel with ❤️*
