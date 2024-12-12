# Используем базовый образ Python 3.12
FROM python:3.12
# Команда для вывода логов в консоле
ENV PYTHONUNBUFFERED=1
# Устанавливаем рабочий каталог
WORKDIR /skill_tap
# Копируем файл requirements.txt
COPY requirements.txt requirements.txt
# Экспортируем порт, который будет использоваться для доступа к приложению
EXPOSE 8000
# Устанавливаем зависимости из файла requirements.txt без кэша
RUN pip install -r requirements.txt
# Копируем файлы и папки из папки CRM_system в рабочий каталог WORKDIR
COPY skill_tap .
# Запускаем Uvicorn сервер
CMD ["uvicorn", "dogs.asgi:application", "--host", "0.0.0.0", "--port", "8000 & python telegram.py"]
