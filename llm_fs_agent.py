import os
import asyncio
import logging
from dotenv import load_dotenv
from langchain_gigachat.chat_models import GigaChat
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_mcp_adapters.client import MultiServerMCPClient

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Загружаем переменные окружения
load_dotenv()

# Функция для создания LLM
def create_llm():
    credentials = os.getenv('GIGACHAT_CREDENTIALS')
    if not credentials:
        raise ValueError("GIGACHAT_CREDENTIALS не найден в переменных окружения")
    logger.info("Инициализация GigaChat LLM...")
    return GigaChat(
        credentials=credentials,
        scope=os.getenv('GIGACHAT_SCOPE', 'GIGACHAT_API_PERS'),
        verify_ssl_certs=False,
        model=os.getenv('GIGACHAT_MODEL', 'GigaChat'),
        temperature=float(os.getenv('GIGACHAT_TEMPERATURE', '0.1')),
        max_tokens=int(os.getenv('GIGACHAT_MAX_TOKENS', '2048'))
    )

# Конфигурация только для fs-mcp
FS_MCP_CONFIG = {
    "fs-mcp": {
        "command": "python",
        "args": ["mcp_modules/fs_mcp.py"],
        "enabled": True,
        "cwd": ".",
        "env": {},
        "description": "Файловые операции: создание, копирование, перемещение, удаление файлов и папок",
        "autoApprove": [],
        "transport": "stdio"
    }
}

# Основная асинхронная функция агента
async def run_llm_fs_agent():
    llm = create_llm()
    # Подключаем только fs-mcp
    client = MultiServerMCPClient(FS_MCP_CONFIG)
    tools = await client.get_tools(server_name="fs-mcp")
    # Для быстрого поиска инструментов по имени
    tools_dict = {tool.name: tool for tool in tools}

    # Приветствие
    print("\n" + "="*70)
    print("🤖 LLM+FS MCP АГЕНТ (GigaChat + файловые инструменты)")
    print("="*70)
    print("\n💡 Введите ваш запрос или команду:")
    print("   • 'выход' - завершение работы")
    print("   • MCP-команды: 'покажи файлы', 'создай файл', 'создай папку', 'удали файл', ...")
    print("="*70 + "\n")

    messages = []
    # Можно добавить системный промпт, если нужно:
    # system_message = SystemMessage(content="Вы — интеллектуальный помощник.")
    # messages.append(system_message)

    while True:
        try:
            user_input = input("👤 Вы: ").strip()
            if user_input.lower() in ["выход", "exit", "quit", "q"]:
                print("\n👋 До свидания! Удачной работы!")
                break
            if not user_input:
                continue

            # --- MCP: простейший парсер команд ---
            # Пример: "покажи файлы [папка]"
            if user_input.lower().startswith("покажи файлы"):
                parts = user_input.split(maxsplit=2)
                directory = parts[2] if len(parts) > 2 else "."
                tool = tools_dict.get("list_files")
                if tool:
                    result = await tool.ainvoke({"directory": directory})
                    print(f"\n📁 Список файлов в '{directory}':\n{result}\n")
                else:
                    print("❌ Инструмент list_files не найден.")
                continue
            # Пример: "создай папку [имя]"
            if user_input.lower().startswith("создай папку"):
                parts = user_input.split(maxsplit=2)
                if len(parts) < 3:
                    print("❗ Укажите имя папки.")
                    continue
                folder_path = parts[2]
                tool = tools_dict.get("create_folder")
                if tool:
                    result = await tool.ainvoke({"folder_path": folder_path})
                    print(f"\n📁 {result}\n")
                else:
                    print("❌ Инструмент create_folder не найден.")
                continue
            # Пример: "удали файл [имя]"
            if user_input.lower().startswith("удали файл"):
                parts = user_input.split(maxsplit=2)
                if len(parts) < 3:
                    print("❗ Укажите имя файла.")
                    continue
                filename = parts[2]
                tool = tools_dict.get("delete_file")
                if tool:
                    result = await tool.ainvoke({"filename": filename})
                    print(f"\n🗑️ {result}\n")
                else:
                    print("❌ Инструмент delete_file не найден.")
                continue
            # Пример: "создай файл [имя] [текст]"
            if user_input.lower().startswith("создай файл"):
                parts = user_input.split(maxsplit=2)
                if len(parts) < 3:
                    print("❗ Укажите имя файла и текст.")
                    continue
                filename_and_text = parts[2].split(maxsplit=1)
                filename = filename_and_text[0]
                text = filename_and_text[1] if len(filename_and_text) > 1 else ""
                tool = tools_dict.get("create_docx")
                if tool:
                    result = await tool.ainvoke({"filename": filename, "text": text})
                    print(f"\n📄 {result}\n")
                else:
                    print("❌ Инструмент create_docx не найден.")
                continue
            # --- /MCP ---

            # Всё остальное — отправляем в LLM
            messages.append(HumanMessage(content=user_input))
            print("\n🤔 Анализирую запрос...")
            response = await asyncio.wait_for(
                llm.ainvoke(messages),
                timeout=60
            )
            if hasattr(response, 'content'):
                reply = response.content
            else:
                reply = str(response)
            print(f"\n🤖 Агент: {reply}")
            print("\n" + "-"*50 + "\n")
            messages.append(response)
        except asyncio.TimeoutError:
            print("⏰ Запрос занимает слишком много времени. Попробуйте упростить задачу.")
        except KeyboardInterrupt:
            print("\n\n👋 Работа прервана пользователем.")
            break
        except Exception as e:
            logger.error(f"Ошибка в цикле агента: {e}")
            print(f"❌ Произошла ошибка: {e}")
            print("Попробуйте еще раз или обратитесь к администратору.\n")

def get_mcp_servers(mcp_config):
    servers = {}
    for name, config in mcp_config['mcpServers'].items():
        if config.get('enabled', True):
            servers[name] = config
    return servers

if __name__ == "__main__":
    try:
        asyncio.run(run_llm_fs_agent())
    except KeyboardInterrupt:
        print("\n👋 Программа завершена пользователем.")
    except Exception as e:
        logger.error(f"Фатальная ошибка: {e}")
        print(f"💥 Фатальная ошибка: {e}")
        print("Проверьте конфигурацию и логи для диагностики.") 