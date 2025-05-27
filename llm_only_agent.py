import os
import asyncio
import logging
from datetime import datetime
from dotenv import load_dotenv
from langchain_gigachat.chat_models import GigaChat
from langchain_core.messages import HumanMessage, SystemMessage

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

# Основная асинхронная функция агента
async def run_llm_agent():
    llm = create_llm()
    # Приветственное сообщение
    print("\n" + "="*70)
    print("🤖 LLM-АГЕНТ (только GigaChat, без MCP)")
    print("="*70)
    print("\n💡 Введите ваш запрос или команду:")
    print("   • 'выход' - завершение работы")
    print("="*70 + "\n")

    # Инициализация истории сообщений
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
            # Добавляем сообщение пользователя в историю
            messages.append(HumanMessage(content=user_input))
            print("\n🤔 Анализирую запрос...")
            # Отправляем запрос в LLM
            response = await asyncio.wait_for(
                llm.ainvoke(messages),
                timeout=60
            )
            # Получаем текст ответа
            if hasattr(response, 'content'):
                reply = response.content
            else:
                reply = str(response)
            print(f"\n🤖 Агент: {reply}")
            print("\n" + "-"*50 + "\n")
            # Добавляем ответ LLM в историю
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

if __name__ == "__main__":
    try:
        asyncio.run(run_llm_agent())
    except KeyboardInterrupt:
        print("\n👋 Программа завершена пользователем.")
    except Exception as e:
        logger.error(f"Фатальная ошибка: {e}")
        print(f"💥 Фатальная ошибка: {e}")
        print("Проверьте конфигурацию и логи для диагностики.") 