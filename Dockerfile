FROM node:20-alpine

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем папку фронтенда внутрь контейнера
COPY frontend/ ./frontend/

# Переходим в директорию фронтенда
WORKDIR /app/frontend

# Устанавливаем зависимости
RUN npm install

# Собираем production версию Next.js приложения
RUN npm run build

# Открываем стандартный порт
EXPOSE 3000

# Запускаем приложение
CMD ["npm", "run", "start"]
