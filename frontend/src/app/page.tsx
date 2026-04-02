"use client";

import { useState, useRef, useEffect, useCallback } from "react";

export default function VoiceChat() {
  const [started, setStarted] = useState(false);
  const [status, setStatus] = useState("initializing");
  const [error, setError] = useState("");

  const liveRef = useRef(false);
  const schedRef = useRef(0);
  const sourcesRef = useRef<AudioBufferSourceNode[]>([]);
  const ctxRef = useRef<AudioContext | null>(null);

  useEffect(() => {
    if (error) {
      const t = setTimeout(() => setError(""), 6000);
      return () => clearTimeout(t);
    }
  }, [error]);

  const playPcm = useCallback((buf: ArrayBuffer) => {
    try {
      const windowAny = window as any;
      const AC = window.AudioContext || windowAny.webkitAudioContext;
      if (!ctxRef.current || ctxRef.current.state === "closed") {
        ctxRef.current = new AC({ sampleRate: 24000 });
        schedRef.current = ctxRef.current.currentTime;
      }
      const c = ctxRef.current;
      
      // Auto-resume if it was suspended
      if (c.state === "suspended") c.resume().catch(e => console.error("resume err", e));

      const i16 = new Int16Array(buf);
      const ab = c.createBuffer(1, i16.length, 24000);
      const ch = ab.getChannelData(0);
      for (let i = 0; i < i16.length; i++) ch[i] = i16[i] / 32768;

      const src = c.createBufferSource();
      src.buffer = ab;
      src.connect(c.destination);

      const now = c.currentTime;
      if (schedRef.current < now) schedRef.current = now + 0.05;
      src.start(schedRef.current);
      schedRef.current += ab.duration;

      src.onended = () => {
        sourcesRef.current = sourcesRef.current.filter((s) => s !== src);
      };
      sourcesRef.current.push(src);
    } catch (e) {
      console.error("pcm err", e);
    }
  }, []);

  const connect = useCallback(() => {
    if (liveRef.current) return;
    liveRef.current = true;
    setStarted(true);
    setStatus("connecting");

    // Initialize AudioContext immediately
    try {
      const windowAny = window as any;
      const AC = window.AudioContext || windowAny.webkitAudioContext;
      if (!ctxRef.current || ctxRef.current.state === "closed") {
        ctxRef.current = new AC({ sampleRate: 24000 });
      }
      if (ctxRef.current.state === "suspended") {
        ctxRef.current.resume().catch(e => console.error("initial resume error", e));
      }
    } catch(err) {
      console.error("AudioContext init error:", err);
    }

    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      setError("❌ Микрофон недоступен! Вы открыли сайт через HTTP (IP адрес)? Нужно использовать HTTPS (ngrok/Cloudflare) ссылку.");
      setStatus("error");
      liveRef.current = false;
      return;
    }

    // Connect directly to the Hugging Face backend to avoid Vercel edge websocket drops
    const wsUrl = `wss://zentrovoy-tomer-ai.hf.space/ws/live-chat`;
    const ws = new WebSocket(wsUrl);

    ws.onopen = async () => {
      if (!liveRef.current) return;
      setStatus("listening");

      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          audio: { sampleRate: 16000, channelCount: 1, echoCancellation: true, noiseSuppression: true },
        });
        
        const windowAny = window as any;
        const AC = window.AudioContext || windowAny.webkitAudioContext;
        const mc = new AC({ sampleRate: 16000 });
        if (mc.state === "suspended") await mc.resume();

        const src = mc.createMediaStreamSource(stream);
        const proc = mc.createScriptProcessor(2048, 1, 1);
        proc.onaudioprocess = (e) => {
          if (ws.readyState !== WebSocket.OPEN || !liveRef.current) return;
          const inp = e.inputBuffer.getChannelData(0);
          const p = new Int16Array(inp.length);
          for (let i = 0; i < inp.length; i++) {
            const s = Math.max(-1, Math.min(1, inp[i]));
            p[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
          }
          ws.send(p.buffer);
        };
        const g = mc.createGain();
        g.gain.value = 0;
        src.connect(proc);
        proc.connect(g);
        g.connect(mc.destination);

        const iv = setInterval(() => {
          if (!liveRef.current) {
            clearInterval(iv);
            ws.close();
            stream.getTracks().forEach((t) => t.stop());
            proc.disconnect();
            src.disconnect();
            mc.close();
          }
        }, 300);
      } catch (e: any) {
        console.error("mic err", e);
        if (e.name === "NotAllowedError" || e.name === "SecurityError") {
          setError("У Томера нет разрешения на микрофон. Разрешите доступ в браузере!");
        } else {
          setError(`Ошибка микрофона: ${e.message}`);
        }
        setStatus("disconnected");
        liveRef.current = false;
      }
    };

    ws.onmessage = async (e) => {
      if (!liveRef.current) return;
      if (typeof e.data === "string") {
        if (e.data === "INTERRUPT") {
          sourcesRef.current.forEach((s) => { try { s.stop(); } catch (_) {} });
          sourcesRef.current = [];
          if (ctxRef.current) schedRef.current = ctxRef.current.currentTime;
        }
        return;
      }
      const ab = await e.data.arrayBuffer();
      if (ab.byteLength > 0) {
        setStatus("speaking");
        playPcm(ab);
        // After sending audio chunk, status returns to listening after a small delay
        setTimeout(() => {
            if (liveRef.current && status === "speaking") setStatus("listening");
        }, 500); 
      }
    };

    ws.onerror = () => {
      console.warn("Ошибка соединения с сервером Tomer AI. Пробуем переподключиться...");
    };

    ws.onclose = () => {
      if (liveRef.current) {
        setStatus("connecting");
        liveRef.current = false;
        // Автоматическое переподключение через 0.5 сек
        setTimeout(() => {
          connect();
        }, 500);
      }
    };
  }, []);

  // Try Auto-starting immediately!
  useEffect(() => {
    connect();
    
    return () => {
      liveRef.current = false;
      if (ctxRef.current) ctxRef.current.close();
    };
  }, [connect]);

  // Click handler to catch iOS issues where AudioContext is suspended
  const handleGlobalTap = useCallback(() => {
    if (ctxRef.current && ctxRef.current.state === "suspended") {
      ctxRef.current.resume().catch(console.error);
    }
    // If it was disconnected due to error, clicking tries reconnecting
    if (status === "disconnected" || status === "error") {
      connect();
    }
  }, [status, connect]);

  const statusLabel: Record<string, string> = {
    initializing: "Запуск...",
    connecting: "🟢 Подключение к Томеру...",
    listening: "🟢 Томер слушает (Говорите!)",
    speaking: "🔊 Томер отвечает...",
    disconnected: "Связь разорвана. Нажмите чтобы переподключиться.",
    error: "Ошибка запуска. Проверьте HTTPS ссылку."
  };

  const isActive = status === "listening" || status === "speaking";

  return (
    <div
      onClick={handleGlobalTap}
      onTouchStart={handleGlobalTap}
      style={{
        position: "fixed",
        inset: 0,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        background: "linear-gradient(135deg, #f8f9ff 0%, #f0f0ff 50%, #faf8ff 100%)",
        fontFamily: "-apple-system, BlinkMacSystemFont, 'SF Pro Display', sans-serif",
        cursor: "pointer",
        userSelect: "none",
        WebkitTouchCallout: "none",
        WebkitTapHighlightColor: "transparent",
        overflow: "hidden",
      }}
    >
      {/* Background glow */}
      {isActive && (
        <div style={{
          position: "absolute",
          width: "60vw",
          height: "60vw",
          borderRadius: "50%",
          background: "radial-gradient(circle, rgba(0,122,255,0.15) 0%, transparent 70%)",
          animation: "pulse 3s ease-in-out infinite",
          pointerEvents: "none"
        }} />
      )}

      {/* Error toast */}
      {error && (
        <div style={{
          position: "absolute",
          top: 40,
          left: 20,
          right: 20,
          textAlign: "center",
          background: "rgba(255,59,48,0.9)",
          color: "white",
          padding: "16px 20px",
          borderRadius: 20,
          fontSize: 15,
          fontWeight: 500,
          zIndex: 100,
          boxShadow: "0 10px 30px rgba(255,59,48,0.4)",
          backdropFilter: "blur(10px)",
        }}>
          {error}
        </div>
      )}

      {/* Title */}
      <h1 style={{
        marginTop: -60,
        marginBottom: 60,
        fontSize: 32,
        fontWeight: 700,
        color: "#000",
        letterSpacing: "-0.5px"
      }}>
        Тֹомер AI
      </h1>

      {/* Central circle */}
      <div style={{ position: "relative", width: 160, height: 160, marginBottom: 48 }}>
        {isActive && (
          <>
            <div style={{
              position: "absolute", inset: -20,
              borderRadius: "50%", border: "2px solid rgba(0,122,255,0.2)",
              animation: "ping 2s cubic-bezier(0,0,0.2,1) infinite",
            }} />
            <div style={{
              position: "absolute", inset: -40,
              borderRadius: "50%", border: "1px solid rgba(0,122,255,0.1)",
              animation: "ping 2.5s cubic-bezier(0,0,0.2,1) infinite 0.5s",
            }} />
          </>
        )}
        <div style={{
          width: 160,
          height: 160,
          borderRadius: "50%",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          transition: "all 0.5s cubic-bezier(0.175, 0.885, 0.32, 1.275)",
          transform: isActive ? "scale(1.05)" : "scale(1)",
          ...(isActive
            ? {
                background: "linear-gradient(135deg, #007AFF, #5856D6)",
                color: "white",
                boxShadow: "0 15px 40px rgba(0,122,255,0.4)",
              }
            : status === "error" || status === "disconnected" 
            ? {
                background: "white",
                border: "3px solid #FF3B30",
                color: "#FF3B30",
                boxShadow: "0 8px 32px rgba(255,59,48,0.15)",
              }
            : {
                background: "white",
                border: "3px solid #007AFF",
                color: "#007AFF",
                boxShadow: "0 8px 32px rgba(0,122,255,0.15)",
              }),
        }}>
          {isActive ? (
            <svg width="60" height="60" fill="currentColor" viewBox="0 0 24 24">
              <path d="M12 14c1.66 0 2.99-1.34 2.99-3L15 5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3zm5.3-3c0 3-2.54 5.1-5.3 5.1S6.7 14 6.7 11H5c0 3.41 2.72 6.23 6 6.72V21h2v-3.28c3.28-.48 6-3.3 6-6.72h-1.7z" />
            </svg>
          ) : (
            <svg width="64" height="64" fill="currentColor" viewBox="0 0 24 24">
              <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z" />
            </svg>
          )}
        </div>
      </div>

      {/* Status */}
      <div style={{ textAlign: "center", padding: "0 20px" }}>
        <div style={{ 
          fontSize: 18, 
          fontWeight: 600, 
          color: isActive ? "#007AFF" : (status === "error" ? "#FF3B30" : "#8e8e93"),
          transition: "color 0.3s ease"
        }}>
          {statusLabel[status] || status}
        </div>
        
        {status === "disconnected" && (
           <div style={{ marginTop: 16, fontSize: 14, color: "#8e8e93" }}>
             Нажмите в любом месте экрана, чтобы переподключиться
           </div>
        )}
        
        {isActive && (
           <div style={{ marginTop: 12, fontSize: 14, color: "#8e8e93", opacity: 0.8 }}>
             Говорите свободно. Томер сразу ответит.
           </div>
        )}
      </div>

      <style>{`
        @keyframes ping {
          75%, 100% { transform: scale(1.8); opacity: 0; }
        }
        @keyframes pulse {
          0%, 100% { transform: scale(1); opacity: 0.5; }
          50% { transform: scale(1.1); opacity: 1; }
        }
      `}</style>
    </div>
  );
}
