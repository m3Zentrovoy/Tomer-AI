"use client";

import { useState, useEffect } from "react";

interface LogEntry {
  timestamp: string;
  session_id: string;
  role: string;
  text: string;
}

export default function LogsPage() {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [translations, setTranslations] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);

  // Fetch logs via API endpoint
  const fetchLogs = async () => {
    try {
      const res = await fetch("https://zentrovoy-tomer-ai.hf.space/api/logs");
      const data = await res.json();
      setLogs(data.logs || []);
    } catch (e) {
      console.error("Failed to load logs", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLogs();
  }, []);

  // Use Free Google Translate endpoint to translate Hebrew to Russian
  const translateText = async (text: string) => {
    if (translations[text]) return; // already translated
    if (!text || text.length < 2) return;
    
    // Quick heuristic: If it contains Hebrew letters, translate it
    if (!/[א-ת]/.test(text)) {
        setTranslations(prev => ({ ...prev, [text]: text }));
        return;
    }
    
    try {
      const res = await fetch(`https://translate.googleapis.com/translate_a/single?client=gtx&sl=he&tl=ru&dt=t&q=${encodeURIComponent(text)}`);
      const data = await res.json();
      const translation = data[0].map((item: any) => item[0]).join("");
      setTranslations(prev => ({ ...prev, [text]: translation }));
    } catch (e) {
      console.error("Translation error", e);
    }
  };

  useEffect(() => {
    // Attempt translation for new messages
    logs.forEach(log => {
        if (log.role !== 'system') translateText(log.text);
    });
  }, [logs]);

  // Group by session
  const sessions: Record<string, LogEntry[]> = {};
  logs.forEach(log => {
    if (!sessions[log.session_id]) sessions[log.session_id] = [];
    sessions[log.session_id].push(log);
  });

  if (loading) return <div style={{ padding: 40, fontFamily: 'system-ui' }}>Загрузка логов...</div>;

  return (
    <div style={{ maxWidth: 800, margin: "0 auto", padding: "40px 20px", fontFamily: "system-ui, sans-serif" }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 30 }}>
        <h1 style={{ fontSize: 24, margin: 0 }}>📊 Логи разговоров с Томером</h1>
        <button 
            onClick={() => fetchLogs()} 
            style={{ padding: "8px 16px", borderRadius: 8, background: "#007AFF", color: "white", border: "none", cursor: "pointer" }}
        >
          Обновить
        </button>
      </div>

      {Object.entries(sessions).reverse().map(([session_id, sessionLogs]) => (
        <div key={session_id} style={{ background: "#f9f9f9", borderRadius: 16, padding: 20, marginBottom: 30, boxShadow: "0 4px 12px rgba(0,0,0,0.05)" }}>
          <div style={{ fontSize: 12, color: "#8E8E93", marginBottom: 16, borderBottom: "1px solid #eee", paddingBottom: 8 }}>
            Сессия: {session_id} • Начинается: {new Date(sessionLogs[0]?.timestamp).toLocaleString('ru-RU')}
          </div>
          
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            {sessionLogs.map((log, idx) => {
              const isUser = log.role === "user";
              const isSystem = log.role === "system";
              
              if (isSystem) {
                return <div key={idx} style={{ textAlign: "center", fontSize: 12, color: "#8E8E93" }}>{log.text}</div>;
              }

              return (
                <div key={idx} style={{ display: "flex", flexDirection: "column", alignItems: isUser ? "flex-end" : "flex-start" }}>
                  <div style={{ fontSize: 12, color: "#8E8E93", marginBottom: 4 }}>
                    {isUser ? "Тестировщик" : "Томер"} • {new Date(log.timestamp).toLocaleTimeString('ru-RU')}
                  </div>
                  
                  <div style={{ 
                    background: isUser ? "#007AFF" : "#E9E9EB", 
                    color: isUser ? "white" : "black",
                    padding: "12px 16px", 
                    borderRadius: 16, 
                    borderBottomRightRadius: isUser ? 4 : 16,
                    borderBottomLeftRadius: isUser ? 16 : 4,
                    maxWidth: "80%" 
                  }}>
                    {/* Оригинал на иврите */}
                    <div style={{ fontSize: 16, direction: "rtl", marginBottom: translations[log.text] ? 8 : 0 }}>
                      {log.text}
                    </div>
                    {/* Перевод на русский */}
                    {translations[log.text] && translations[log.text] !== log.text && (
                      <div style={{ fontSize: 14, opacity: isUser ? 0.9 : 0.6, borderTop: isUser ? "1px solid rgba(255,255,255,0.2)" : "1px solid rgba(0,0,0,0.1)", paddingTop: 8 }}>
                        🇷🇺 {translations[log.text]}
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      ))}

      {logs.length === 0 && <div style={{ textAlign: 'center', color: '#8E8E93' }}>Логи пока пусты. Поговорите с Томером!</div>}
    </div>
  );
}
