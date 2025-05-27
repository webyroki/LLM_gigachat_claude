# Интеллектуальный агент документооборота на базе LLM и MCP

## Описание

Данный проект реализует интеллектуального агента для автоматизации работы с документами и файловой системой с помощью LLM (GigaChat) и MCP-инструментов.  
Агент поддерживает генерацию документов по шаблонам, работу с файлами и папками, а также расширяемую архитектуру для интеграции новых инструментов.

---

## Основные возможности

- **Генерация .docx документов по шаблонам** (через MCP DocGenerator)
- **Анализ и валидация шаблонов** (поиск переменных, проверка структуры)
- **Работа с файлами и папками** (создание, удаление, копирование, перемещение, просмотр содержимого)
- **Логирование всех действий** (логи сохраняются в папке `logs/`)
- **Гибкая настройка через конфиги и расширяемые MCP-модули**
- **Режим только LLM** (без MCP, для диалогов и генерации текста)

---

## Структура проекта

```
├── agent.py                  # Главный агент (LLM + MCP)
├── llm_only_agent.py         # Агент только с LLM (без MCP)
├── mcp_modules/
│   ├── doc_generator.py      # MCP: генерация и анализ .docx по шаблонам
│   └── fs_mcp.py             # MCP: работа с файлами и папками
├── templates/                # Шаблоны .docx (пример: докладная записка, report_template)
├── output/                   # Сгенерированные документы
├── logs/                     # Логи работы агента и MCP
├── requirements.txt          # Зависимости Python
├── install_requirements.bat  # Установка зависимостей и создание .env
├── run_agent.bat             # Запуск агента (LLM + MCP)
├── run_all.bat               # Запуск MCP-серверов и агента (всё сразу)
├── mcp_servers.json          # Конфиг MCP-серверов
├── rules.json                # Правила и роль агента
├── README.md                 # Документация
```

---

## Быстрый старт

1. **Установите зависимости и создайте .env:**
   ```bat
   install_requirements.bat
   ```
   или вручную:
   ```bash
   python -m venv venv
   venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Проверьте/создайте файл `.env`** (автоматически создаётся скриптом):
   ```
   GIGACHAT_CREDENTIALS=your_gigachat_token
   GIGACHAT_SCOPE=GIGACHAT_API_PERS
   TAVILY_API_KEY=your_tavily_api_key
   ```

3. **Запустите все компоненты (MCP + агент):**
   ```bat
   run_all.bat
   ```
   или по отдельности:
   ```bat
   start cmd /k "python mcp_modules\fs_mcp.py"
   start cmd /k "python mcp_modules\doc_generator.py"
   python agent.py
   ```

4. **Для режима только LLM:**
   ```bat
   python llm_only_agent.py
   ```

---

## Использование

- Введите команду или запрос, например:
  - `создай докладную` — агент запросит текст, подставит его в шаблон и сгенерирует файл в `output/`
  - `покажи файлы templates` — список файлов в папке шаблонов
  - `создай папку output/test` — создать новую папку
  - `удали файл output/report.docx` — удалить файл
  - `прочитай файл output/report_filled_test.docx` — вывести содержимое docx

- Доступные команды:
  - `помощь` — список возможностей
  - `статус` — информация о системе и инструментах
  - `выход` — завершение работы

---

## MCP-модули

### `mcp_modules/fs_mcp.py` — файловый менеджер
- `list_files(directory)` — список файлов в директории
- `create_docx(filename, text)` — создать docx с текстом
- `create_folder(folder_path)` — создать папку
- `delete_file(filename)` — удалить файл
- `delete_folder(folder_path)` — удалить папку
- `copy_file(source, destination)` — копировать файл
- `move_file(source, destination)` — переместить файл

### `mcp_modules/doc_generator.py` — генерация документов по шаблонам
- `generate_docx(path_template, context, output_path)` — сгенерировать docx по шаблону с подстановкой переменных
- `get_template_variables(path_template)` — получить список переменных шаблона
- `validate_template(path_template)` — проверить корректность шаблона
- `read_docx(path)` — прочитать содержимое docx
- `append_to_docx(path, text)` — добавить текст в docx

---

## Пример шаблона .docx

- Положите шаблон в папку `templates/` (например, `докладная записка.docx`)
- Используйте переменные в формате `{{ variable_name }}` (например, `{{ text }}`)

---

## Расширение функционала

1. Добавьте новый шаблон в `templates/`
2. Добавьте ключевые слова и обработку в `agent.py`
3. (Опционально) Добавьте новый MCP-модуль в `mcp_modules/` и настройте его в `mcp_servers.json`

---

## Логи

- Все логи сохраняются в папке `logs/` (отдельно для агента и MCP-серверов)

---

## Поддержка

- Вопросы и предложения

