import os
import asyncio
import json
import logging
from datetime import datetime
from dotenv import load_dotenv
from langchain_gigachat.chat_models import GigaChat
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent

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
    """Получение списка активных MCP серверов"""
    servers = {}
    for name, config in mcp_config['mcpServers'].items():
        if config.get('enabled', True):
            servers[name] = config
    return servers

def create_system_prompt(rules):
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
    
    return base_prompt

async def ask_confirmation(message):
    """Запрос подтверждения от пользователя"""
    print(f"\n⚠️  {message}")
    response = input("Подтвердить? (да/нет): ").strip().lower()
    return response in ['да', 'yes', 'y', 'д']

async def initialize_agent():
    """Инициализация агента с расширенной обработкой ошибок"""
    try:
        rules, mcp_config = load_config()
        llm = create_llm()
        mcp_servers = get_mcp_servers(mcp_config)
        
        if not mcp_servers:
            raise ValueError("Нет активных MCP серверов для подключения")
        
        logger.info(f"Подключение к MCP серверам: {list(mcp_servers.keys())}")
        
        # Настройка таймаута из конфигурации
        timeout = mcp_config.get('settings', {}).get('timeout', 30000) / 1000
        
        client = MultiServerMCPClient(mcp_servers)
        await asyncio.wait_for(client.__aenter__(), timeout=timeout)
        
        tools = await client.get_tools()
        logger.info(f"Загружено MCP инструментов: {len(tools)}")
        
        # Логируем доступные инструменты
        tool_names = [tool.name if hasattr(tool, 'name') else str(tool) for tool in tools]
        logger.info(f"Доступные инструменты: {', '.join(tool_names)}")
        
        agent = create_react_agent(llm, tools)
        
        return agent, client, rules
        
    except asyncio.TimeoutError:
        logger.error("Таймаут при подключении к MCP серверам")
        raise
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
        return True
    
    elif command in ['статус', 'status']:
        print(f"\n📊 Статус системы:")
        print(f"• Доступно MCP инструментов: {len(tools)}")
        print(f"• Время работы: {datetime.now().strftime('%H:%M:%S')}")
        print(f"• Логи: {os.getenv('LOGS_PATH', './logs')}")
        return True
    
    elif user_input.lower().startswith("прочитай файл"):
        # Команда для чтения содержимого DOCX-файла
        parts = user_input.split(maxsplit=2)
        if len(parts) == 3:
            file_path = parts[2]
        else:
            file_path = input("Введите путь к DOCX-файлу: ").strip()
        tool = next((t for t in tools if hasattr(t, 'name') and t.name == 'read_docx'), None)
        if not tool:
            print("❌ Инструмент чтения DOCX не найден.\n")
            return False
        try:
            result = await tool.ainvoke({"path": file_path})
            print(f"\n📄 Содержимое файла '{file_path}':\n{result if isinstance(result, str) else str(result)}\n")
        except Exception as e:
            print(f"❌ Ошибка при чтении файла: {e}\n")
        return True
    
    return False

async def run_agent():
    """Основной цикл работы агента с улучшенной обработкой"""
    agent = None
    client = None
    
    try:
        agent, client, rules = await initialize_agent()
        print_welcome_message(rules)
        
        system_prompt = create_system_prompt(rules)
        system_message = SystemMessage(content=system_prompt)
        
        messages = [system_message]
        tools = await client.get_tools()
        
        tool_names = [tool.name if hasattr(tool, 'name') else str(tool) for tool in tools]
        logger.info(f"Доступные инструменты: {', '.join(tool_names)}")
        
        while True:
            try:
                user_input = input("👤 Вы: ").strip()
                
                if user_input.lower() in ["выход", "exit", "quit", "q"]:
                    print("\n👋 До свидания! Удачной работы с документами!")
                    break
                
                if not user_input:
                    continue
                
                if await handle_special_commands(user_input, tools):
                    continue
                
                # Явная обработка ключевых слов для докладной записки
                keywords = ["докладная", "записка"]
                if any(word in user_input.lower() for word in keywords):
                    print("\n📝 Обнаружен запрос на создание докладной записки.")
                    # Запросить основной текст для вставки в шаблон
                    main_text = input("Введите основной текст для докладной записки: ").strip()
                    if not main_text:
                        print("❗ Текст не может быть пустым. Операция отменена.\n")
                        continue
                    # Путь к шаблону и выходному файлу
                    template_path = os.path.join("templates", "докладная записка.docx")
                    output_path = os.path.join("output", f"докладная_записка_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx")
                    context = {"text": main_text}
                    # Поиск инструмента генерации docx
                    tool = next((t for t in tools if hasattr(t, 'name') and t.name == 'generate_docx'), None)
                    if not tool:
                        print("❌ Инструмент генерации документов не найден.\n")
                        continue
                    # Вызов MCP-инструмента
                    try:
                        result = await tool.ainvoke({
                            "path_template": template_path,
                            "context": context,
                            "output_path": output_path
                        })
                        print(f"\n✅ {result if isinstance(result, str) else 'Докладная записка успешно создана.'}\n")
                    except Exception as e:
                        print(f"❌ Ошибка при создании докладной: {e}\n")
                    continue
                
                messages.append(HumanMessage(content=user_input))
                print("\n🤔 Анализирую запрос...")
                
                response = await asyncio.wait_for(
                    agent.ainvoke({"messages": messages}),
                    timeout=60
                )
                
                if hasattr(response['messages'][-1], 'content'):
                    reply = response['messages'][-1].content
                else:
                    reply = str(response['messages'][-1])
                
                print(f"\n🤖 Агент: {reply}")
                print("\n" + "-"*50 + "\n")
                
                messages.append(response['messages'][-1])
                
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
                await client.__aexit__(None, None, None)
                logger.info("MCP клиент корректно закрыт")
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