import os
import asyncio
import json
import logging
from datetime import datetime
from dotenv import load_dotenv
from langchain_gigachat.chat_models import GigaChat
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_mcp_adapters.client import MultiServerMCPClient

# Настройка логирования
def setup_logging():
    """Настройка системы логирования"""
    log_dir = os.getenv('LOGS_PATH', './logs')
    os.makedirs(log_dir, exist_ok=True)
    
    log_file = os.path.join(log_dir, f"agent_{datetime.now().strftime('%Y%m%d')}.log")
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

# Загружаем переменные окружения
load_dotenv()
logger = setup_logging()

def load_config():
    """Загрузка и валидация конфигурационных файлов"""
    try:
        # Загружаем правила и роль агента
        with open('rules.json', encoding='utf-8') as f:
            rules = json.load(f)
        
        # Загружаем настройки MCP серверов
        with open('mcp_servers.json', encoding='utf-8') as f:
            mcp_config = json.load(f)
        
        # Валидация конфигурации
        validate_config(rules, mcp_config)
        
        return rules, mcp_config
        
    except FileNotFoundError as e:
        logger.error(f"Конфигурационный файл не найден: {e}")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Ошибка парсинга JSON: {e}")
        raise

def validate_config(rules, mcp_config):
    """Валидация конфигурации"""
    # Проверка обязательных полей в rules.json
    required_fields = ['role', 'language', 'rules']
    for field in required_fields:
        if field not in rules:
            raise ValueError(f"Отсутствует обязательное поле '{field}' в rules.json")
    
    # Проверка MCP серверов
    if 'mcpServers' not in mcp_config:
        raise ValueError("Отсутствует секция 'mcpServers' в mcp_servers.json")
    
    # Проверка активных серверов
    active_servers = [name for name, config in mcp_config['mcpServers'].items() 
                     if config.get('enabled', True)]
    
    if not active_servers:
        logger.warning("Нет активных MCP серверов")
    else:
        logger.info(f"Активные MCP серверы: {', '.join(active_servers)}")

def create_llm():
    """Создание объекта GigaChat LLM с расширенными настройками"""
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

def get_mcp_servers(mcp_config):
    servers = {}
    for name, config in mcp_config['mcpServers'].items():
        if config.get('enabled', True):
            servers[name] = config
    return servers

def create_system_prompt(rules, tools):
    """Создание системного промпта на основе конфигурации"""
    base_prompt = rules['role']
    
    # Добавляем правила
    if 'rules' in rules:
        rules_text = "\n".join([f"- {rule}" for rule in rules['rules']])
        base_prompt += f"\n\nПравила работы:\n{rules_text}"
    
    # Добавляем workflow если есть
    if 'workflows' in rules:
        workflows_text = ""
        for workflow_name, steps in rules['workflows'].items():
            steps_text = "\n".join([f"  {step}" for step in steps])
            workflows_text += f"\n\n{workflow_name.replace('_', ' ').title()}:\n{steps_text}"
        base_prompt += f"\n\nРабочие процессы:{workflows_text}"
    
    # Добавляем стиль общения
    if 'personality' in rules:
        personality = rules['personality']
        base_prompt += f"\n\nСтиль общения: {personality.get('style', 'профессиональный')}"
        base_prompt += f"\nТон: {personality.get('tone', 'помогающий')}"
        base_prompt += f"\nПодход: {personality.get('approach', 'методичный')}"
    
    # Добавляем информацию о доступных инструментах
    if tools:
        tools_info = []
        for tool in tools:
            tool_name = tool.name if hasattr(tool, 'name') else str(tool)
            tool_desc = getattr(tool, 'description', 'Описание недоступно')
            tools_info.append(f"- {tool_name}: {tool_desc}")
        
        base_prompt += f"\n\nДоступные инструменты:\n" + "\n".join(tools_info)
        base_prompt += f"\n\nВы можете использовать эти инструменты для выполнения задач пользователя. При необходимости использования инструмента, сначала объясните пользователю, что вы собираетесь делать."
    
    return base_prompt

async def call_tool_by_name(tools_dict, tool_name, params):
    """Вызов инструмента по имени с параметрами"""
    if tool_name not in tools_dict:
        return f"❌ Инструмент '{tool_name}' не найден."
    
    try:
        tool = tools_dict[tool_name]
        result = await tool.ainvoke(params)
        return result
    except Exception as e:
        logger.error(f"Ошибка вызова инструмента {tool_name}: {e}")
        return f"❌ Ошибка при выполнении {tool_name}: {e}"

async def process_user_request(user_input, llm, tools_dict, messages):
    """Обработка запроса пользователя с возможностью вызова инструментов"""
    
    # Прямые команды для инструментов
    if user_input.lower().startswith("покажи файлы") and "list_files" in tools_dict:
        parts = user_input.split(maxsplit=2)
        directory = parts[2] if len(parts) > 2 else "."
        result = await call_tool_by_name(tools_dict, "list_files", {"directory": directory})
        return f"📁 Список файлов в '{directory}':\n{result}"
    
    elif user_input.lower().startswith("создай папку") and "create_folder" in tools_dict:
        parts = user_input.split(maxsplit=2)
        if len(parts) < 3:
            return "❗ Укажите имя папки."
        folder_path = parts[2]
        result = await call_tool_by_name(tools_dict, "create_folder", {"folder_path": folder_path})
        return f"📁 {result}"
    
    elif user_input.lower().startswith("удали файл") and "delete_file" in tools_dict:
        parts = user_input.split(maxsplit=2)
        if len(parts) < 3:
            return "❗ Укажите имя файла."
        filename = parts[2]
        result = await call_tool_by_name(tools_dict, "delete_file", {"filename": filename})
        return f"🗑️ {result}"
    
    elif user_input.lower().startswith("создай файл") and "create_docx" in tools_dict:
        parts = user_input.split(maxsplit=2)
        if len(parts) < 3:
            return "❗ Укажите имя файла и текст."
        filename_and_text = parts[2].split(maxsplit=1)
        filename = filename_and_text[0]
        text = filename_and_text[1] if len(filename_and_text) > 1 else ""
        result = await call_tool_by_name(tools_dict, "create_docx", {"filename": filename, "text": text})
        return f"📄 {result}"
    
    elif user_input.lower().startswith("прочитай файл") and "read_docx" in tools_dict:
        parts = user_input.split(maxsplit=2)
        if len(parts) < 3:
            return "❗ Укажите имя файла."
        path = parts[2]
        result = await call_tool_by_name(tools_dict, "read_docx", {"path": path})
        return f"📄 Содержимое файла '{path}':\n{result}"
    
    # Для сложных запросов используем LLM
    else:
        messages.append(HumanMessage(content=user_input))
        
        # Создаем чистые сообщения для GigaChat
        clean_messages = []
        for msg in messages:
            if isinstance(msg, SystemMessage):
                clean_messages.append(SystemMessage(content=msg.content))
            elif isinstance(msg, HumanMessage):
                clean_messages.append(HumanMessage(content=msg.content))
            elif isinstance(msg, AIMessage):
                clean_messages.append(AIMessage(content=msg.content))
        
        response = await llm.ainvoke(clean_messages)
        
        if hasattr(response, 'content'):
            reply = response.content
        else:
            reply = str(response)
        
        # Добавляем ответ в историю
        messages.append(AIMessage(content=reply))
        
        return reply

async def ask_confirmation(message):
    """Запрос подтверждения от пользователя"""
    print(f"\n⚠️  {message}")
    response = input("Подтвердить? (да/нет): ").strip().lower()
    return response in ['да', 'yes', 'y', 'д']

async def initialize_agent():
    """Инициализация агента с поддержкой MCP"""
    try:
        rules, mcp_config = load_config()
        llm = create_llm()
        mcp_servers = get_mcp_servers(mcp_config)
        
        if not mcp_servers:
            raise ValueError("Нет активных MCP серверов для подключения")
        
        logger.info(f"Подключение к MCP серверам: {list(mcp_servers.keys())}")
        client = MultiServerMCPClient(mcp_servers)
        tools = await client.get_tools()
        
        logger.info(f"Загружено MCP инструментов: {len(tools)}")
        
        return client, rules, tools, llm
        
    except Exception as e:
        logger.error(f"Ошибка инициализации агента: {e}")
        raise

def print_welcome_message(rules):
    """Красивое приветственное сообщение"""
    print("\n" + "="*70)
    print("🤖 ИНТЕЛЛЕКТУАЛЬНЫЙ АГЕНТ ДОКУМЕНТООБОРОТА")
    print("="*70)
    
    print(f"\n👤 Роль: {rules.get('role', 'Помощник по документам')}")
    print(f"🌐 Язык: {rules.get('language', 'русский')}")
    
    if 'personality' in rules:
        personality = rules['personality']
        print(f"🎭 Стиль: {personality.get('style', 'профессиональный')}")
    
    if 'rules' in rules:
        print(f"\n📋 Основные правила ({len(rules['rules'])}):")
        for i, rule in enumerate(rules['rules'][:5], 1):  # Показываем первые 5 правил
            print(f"   {i}. {rule}")
        if len(rules['rules']) > 5:
            print(f"   ... и еще {len(rules['rules']) - 5} правил")
    
    if 'examples' in rules and 'greetings' in rules['examples']:
        import random
        greeting = random.choice(rules['examples']['greetings'])
        print(f"\n💬 {greeting}")
    
    print("\n" + "="*70)
    print("💡 Введите ваш запрос или команду:")
    print("   • 'помощь' - список доступных команд")
    print("   • 'статус' - информация о системе") 
    print("   • 'выход' - завершение работы")
    print("="*70 + "\n")

async def handle_special_commands(user_input, tools):
    """Обработка специальных команд"""
    command = user_input.lower().strip()
    
    if command in ['помощь', 'help']:
        print("\n📖 Доступные команды:")
        print("• Создание документов по шаблонам")
        print("• Анализ структуры шаблонов")  
        print("• Поиск актуальной информации")
        print("• Автоматизация документооборота")
        print("• MCP команды: 'покажи файлы', 'создай файл', 'создай папку', 'удали файл'")
        return True
    
    elif command in ['статус', 'status']:
        print(f"\n📊 Статус системы:")
        print(f"• Доступно MCP инструментов: {len(tools)}")
        print(f"• Время работы: {datetime.now().strftime('%H:%M:%S')}")
        print(f"• Логи: {os.getenv('LOGS_PATH', './logs')}")
        return True
    
    return False

async def run_agent():
    """Основной цикл работы агента с исправленной архитектурой"""
    client = None
    try:
        client, rules, tools, llm = await initialize_agent()
        print_welcome_message(rules)
        
        system_prompt = create_system_prompt(rules, tools)
        system_message = SystemMessage(content=system_prompt)
        messages = [system_message]
        
        tool_names = [tool.name if hasattr(tool, 'name') else str(tool) for tool in tools]
        logger.info(f"Доступные инструменты: {', '.join(tool_names)}")
        
        tools_dict = {tool.name: tool for tool in tools if hasattr(tool, 'name')}
        
        while True:
            try:
                user_input = input("👤 Вы: ").strip()
                
                if user_input.lower() in ["выход", "exit", "quit", "q"]:
                    print("\n👋 До свидания! Удачной работы с документами!")
                    break
                
                if not user_input:
                    continue
                
                # Обработка специальных команд
                if await handle_special_commands(user_input, tools):
                    continue
                
                print("\n🤔 Анализирую запрос...")
                
                # Обработка запроса пользователя
                response = await asyncio.wait_for(
                    process_user_request(user_input, llm, tools_dict, messages),
                    timeout=60
                )
                
                print(f"\n🤖 Агент: {response}")
                print("\n" + "-"*50 + "\n")
                
            except asyncio.TimeoutError:
                print("⏰ Запрос занимает слишком много времени. Попробуйте упростить задачу.")
            except KeyboardInterrupt:
                print("\n\n👋 Работа прервана пользователем.")
                break
            except Exception as e:
                logger.error(f"Ошибка в цикле агента: {e}")
                print(f"❌ Произошла ошибка: {e}")
                print("Попробуйте еще раз или обратитесь к администратору.\n")
                
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
        print(f"❌ Критическая ошибка при запуске: {e}")
    finally:
        if client:
            try:
                await client.close()
                logger.info("MCP клиент завершил работу")
            except Exception as e:
                logger.error(f"Ошибка закрытия MCP клиента: {e}")

if __name__ == "__main__":
    try:
        print("🚀 Запуск интеллектуального агента...")
        asyncio.run(run_agent())
    except KeyboardInterrupt:
        print("\n👋 Программа завершена пользователем.")
    except Exception as e:
        logger.error(f"Фатальная ошибка: {e}")
        print(f"💥 Фатальная ошибка: {e}")
        print("Проверьте конфигурацию и логи для диагностики.")