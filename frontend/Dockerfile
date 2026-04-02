FROM node:20-alpine

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем всё из текущей папки (frontend) внутрь контейнера
COPY . .

# Устанавливаем зависимости
RUN npm install

# Собираем production версию Next.js приложения
RUN npm run build

# Открываем стандартный порт
EXPOSE 3000

# Запускаем приложение
CMD ["npm", "run", "start"]
