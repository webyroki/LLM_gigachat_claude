@echo off
REM === Запуск MCP серверов в отдельных окнах ===
start "MCP FS Server" cmd /c "python mcp_modules\fs_mcp.py"
start "MCP DocGen Server" cmd /c "python mcp_modules\doc_generator.py"
REM === Ждем 3 секунды для инициализации MCP серверов ===
ping 127.0.0.1 -n 4 > nul
REM === Активация виртуального окружения (если есть) ===
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
)
REM === Запуск основного агента ===
python agent.py 