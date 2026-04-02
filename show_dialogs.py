import json
import sys
import urllib.request
import urllib.parse
from collections import defaultdict
from colorama import init, Fore, Style

# Инициализируем цвета для терминала
init(autoreset=True)

# URL вашего бэкенда на Hugging Face
API_URL = "https://zentrovoy-tomer-ai.hf.space/api/logs"

def translate_he_to_ru(text):
    if not text or not any("\u0590" <= c <= "\u05FF" for c in text): # Проверка на иврит
        return text
    try:
        url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=he&tl=ru&dt=t&q={urllib.parse.quote(text)}"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            return "".join([x[0] for x in data[0]])
    except Exception as e:
        return text + f" [Ошибка перевода: {e}]"

print(Fore.CYAN + "📥 Скачиваем логи с сервера Hugging Face...\n")

try:
    req = urllib.request.Request(API_URL, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req) as response:
        data = json.loads(response.read().decode())
        lines = data.get("logs", [])
except Exception as e:
    print(Fore.RED + f"❌ Ошибка скачивания логов с сервера: {e}")
    sys.exit(1)

if not lines:
    print(Fore.RED + "Файл логов пуст! Никто еще не говорил с Томером.")
    sys.exit(0)

# Группируем по сессиям
sessions = defaultdict(list)

for msg in lines:
    try:
        sessions[msg['session_id']].append(msg)
    except:
        continue

print(Fore.CYAN + "=== 📋 ИСТОРИЯ РАЗГОВОРОВ ТЕСТИРОВЩИКОВ ===\n")

for session_id, messages in sessions.items():
    print(Fore.YELLOW + f"[{session_id}] Сессия тестировщика (начинается: {messages[0]['timestamp'][:10]} {messages[0]['timestamp'][11:19]})")
    print(Fore.YELLOW + "-" * 60)
    
    current_role = None
    accumulated_text = ""
    last_timestamp = ""

    def print_message(role, text, time):
        if not text.strip():
            return
            
        time_short = time.split('T')[1][:8] if 'T' in time else time
        ru_text = translate_he_to_ru(text)
        
        if role == 'user':
            print(f"  {Fore.GREEN}🗣  Тестировщик ({time_short}):")
            print(f"      {Fore.WHITE}{text}")
            if text != ru_text:
                print(f"      {Fore.LIGHTBLACK_EX}🇷🇺 {ru_text}{Style.RESET_ALL}")
        elif role == 'tomer':
            print(f"  {Fore.BLUE}🤖 Томер ({time_short}):")
            print(f"      {Fore.WHITE}{text}")
            if text != ru_text:
                print(f"      {Fore.LIGHTBLACK_EX}🇷🇺 {ru_text}{Style.RESET_ALL}")
        elif role == 'system':
            print(f"  {Fore.MAGENTA}⚡ Системное событие:{Style.RESET_ALL} {text}")
        print("")

    for msg in messages:
        role = msg['role']
        text = msg['text']
        time = msg['timestamp']

        if role == current_role:
            # Склеиваем кусочки текста
            accumulated_text += text
        else:
            if current_role is not None:
                print_message(current_role, accumulated_text, last_timestamp)
            current_role = role
            accumulated_text = text
            last_timestamp = time

    if current_role is not None:
        print_message(current_role, accumulated_text, last_timestamp)

print(Fore.CYAN + f"Всего сессий: {len(sessions)}")
