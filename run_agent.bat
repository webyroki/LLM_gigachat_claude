@echo off
REM Создание и активация виртуального окружения, установка зависимостей и запуск agent.py

REM Проверка наличия venv
if not exist venv (
    python -m venv venv
)

REM Активация виртуального окружения
call venv\Scripts\activate.bat

REM Установка зависимостей
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

REM Запуск агента
python agent.py

pause 