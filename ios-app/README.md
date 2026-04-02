# Tomer AI - iOS Client

Это нативный iOS клиент на SwiftUI для голосового ассистента Tomer AI. 

## Как запустить:

1. Откройте Xcode на Mac.
2. Выберите **File > New > Project...**
3. Выберите **iOS > App**, нажмите Next.
4. Назовите проект `TomerAI`, выберите Interface: **SwiftUI**, Language: **Swift**.
5. Сохраните проект в удобное место.
6. Выделите созданные нами файлы из папки `/ios-app` (ContentView.swift, AudioRecorder.swift, APIService.swift, AudioPlayer.swift, ChatViewModel.swift).
7. Перетащите их мышкой в левое меню Xcode (Navigator), прямо в папку с кодом проекта. Выберите **"Copy items if needed"**. 
8. При необходимости удалите старый `ContentView.swift` (по-умолчанию с Hello World) перед копированием нашего.

## Настройка разрешений в Info.plist

Чтобы всё заработало, нужно добавить разрешения.
1. Нажмите на главный файл проекта `TomerAI` в самом верху списка файлов Xcode.
2. Перейдите во вкладку **Info**.
3. Добавьте новый ключ: `Privacy - Microphone Usage Description` (NSMicrophoneUsageDescription)
   - Значение: "Нужен микрофон для голосового общения с Томером"
4. Для работы с локальным сервером (без SSL):
   - Добавьте `App Transport Security Settings` (словарь)
   - Внутри него `Allow Arbitrary Loads` -> установите в **YES**

## Подключение к бэкенду (Python FastAPI)

1. Узнайте локальный IP вашего Mac в Wi-Fi сети. В терминале:
   ```bash
   ipconfig getifaddr en0
   ```
   *(Пример результата: `192.168.1.51`)*
   
2. Откройте файл `APIService.swift` в Xcode.
3. Измените строку `let API_BASE_URL`:
   ```swift
   // Вместо "http://127.0.0.1:8000" укажите ваш IP:
   let API_BASE_URL = "http://192.168.1.51:8000" 
   ```

4. Запустите Python-бэкенд с доступом по локальной сети:
   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8000
   ```

## Запуск

- Вы можете запустить приложение в **iPhone Simulator** (симулятор поддерживает локальный 127.0.0.1, так что шаг с IP можно пропустить, если тестируете в нём).
- Или подключите свой физический iPhone кабелем, выберите его в списке сверху и нажмите **Start (Play)**. На айфоне в настройках появится пункт "Доверять разработчику" (General > VPN & Device Management).
