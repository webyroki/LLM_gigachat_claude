@echo off
REM Установка зависимостей для проекта GigaChat + MCP

REM Создание виртуального окружения, если не существует
if not exist venv (
    python -m venv venv
)

REM Активация виртуального окружения
call venv\Scripts\activate.bat

REM Создание файла .env с нужными ключами, если он не существует
if not exist .env (
    echo GIGACHAT_CREDENTIALS=your_gigachat_auth_key_here> .env
    echo GIGACHAT_SCOPE=GIGACHAT_API_CORP>> .env
    echo TAVILY_API_KEY=your_tavily_api_key_here>> .env
    echo Файл .env создан с шаблонными ключами.
) else (
    echo Файл .env уже существует, пропускаю создание.
)

REM Проверка наличия pip
python -m pip --version >nul 2>&1
IF ERRORLEVEL 1 (
    echo pip не найден. Устанавливаю pip...
    python -m ensurepip --upgrade
)

REM Установка зависимостей
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

if %ERRORLEVEL% EQU 0 (
    echo Все зависимости успешно установлены.
) else (
    echo Произошла ошибка при установке зависимостей.
)

pause 