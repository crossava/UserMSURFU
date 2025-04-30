# Используем Python 3.11 в качестве базового образа
FROM python:3.11

# Устанавливаем рабочую директорию в контейнере
WORKDIR /app

# Копируем файлы проекта в контейнер
COPY . .

# Обновляем pip
RUN pip install --upgrade pip

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Запускаем приложение
CMD ["python", "main.py"]
