# MCP-сервер для работы с файловой системой и базовыми операциями с файлами/папками
# Использует context7-mcp
from context7.mcp.server.fastmcp import FastMCP
import os
import shutil
from docx import Document
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализация MCP
mcp = FastMCP("FSManager")

@mcp.tool()
def create_docx(filename: str, text: str = "") -> str:
    """
    Создать новый DOCX документ с указанным текстом.
    Args:
        filename: Имя файла (с расширением .docx)
        text: Текст для вставки в документ
    Returns:
        Сообщение о результате
    """
    try:
        doc = Document()
        if text:
            doc.add_paragraph(text)
        doc.save(filename)
        return f"✅ DOCX файл '{filename}' успешно создан."
    except Exception as e:
        logger.error(f"Ошибка при создании DOCX: {e}")
        return f"❌ Ошибка при создании DOCX: {e}"

@mcp.tool()
def list_files(directory: str = ".") -> str:
    """
    Список всех файлов в указанной директории.
    Args:
        directory: Путь к директории
    Returns:
        Список файлов
    """
    try:
        files = os.listdir(directory)
        if not files:
            return f"📁 В директории '{directory}' нет файлов."
        return "\n".join(files)
    except Exception as e:
        logger.error(f"Ошибка при получении списка файлов: {e}")
        return f"❌ Ошибка: {e}"

@mcp.tool()
def copy_file(source: str, destination: str) -> str:
    """
    Копировать файл в другую папку.
    Args:
        source: Путь к исходному файлу
        destination: Путь назначения (папка или полный путь)
    Returns:
        Сообщение о результате
    """
    try:
        if os.path.isdir(destination):
            dest_path = os.path.join(destination, os.path.basename(source))
        else:
            dest_path = destination
        shutil.copy2(source, dest_path)
        return f"✅ Файл скопирован в '{dest_path}'."
    except Exception as e:
        logger.error(f"Ошибка при копировании файла: {e}")
        return f"❌ Ошибка при копировании файла: {e}"

@mcp.tool()
def move_file(source: str, destination: str) -> str:
    """
    Переместить файл в другую папку.
    Args:
        source: Путь к исходному файлу
        destination: Путь назначения (папка или полный путь)
    Returns:
        Сообщение о результате
    """
    try:
        if os.path.isdir(destination):
            dest_path = os.path.join(destination, os.path.basename(source))
        else:
            dest_path = destination
        shutil.move(source, dest_path)
        return f"✅ Файл перемещён в '{dest_path}'."
    except Exception as e:
        logger.error(f"Ошибка при перемещении файла: {e}")
        return f"❌ Ошибка при перемещении файла: {e}"

@mcp.tool()
def create_folder(folder_path: str) -> str:
    """
    Создать новую папку.
    Args:
        folder_path: Путь к новой папке
    Returns:
        Сообщение о результате
    """
    try:
        os.makedirs(folder_path, exist_ok=True)
        return f"✅ Папка '{folder_path}' создана."
    except Exception as e:
        logger.error(f"Ошибка при создании папки: {e}")
        return f"❌ Ошибка при создании папки: {e}"

@mcp.tool()
def delete_folder(folder_path: str) -> str:
    """
    Удалить папку и всё её содержимое.
    Args:
        folder_path: Путь к папке
    Returns:
        Сообщение о результате
    """
    try:
        shutil.rmtree(folder_path)
        return f"✅ Папка '{folder_path}' удалена."
    except Exception as e:
        logger.error(f"Ошибка при удалении папки: {e}")
        return f"❌ Ошибка при удалении папки: {e}"

@mcp.tool()
def delete_file(filename: str) -> str:
    """
    Удалить файл.
    Args:
        filename: Путь к файлу
    Returns:
        Сообщение о результате
    """
    try:
        os.remove(filename)
        return f"✅ Файл '{filename}' удалён."
    except Exception as e:
        logger.error(f"Ошибка при удалении файла: {e}")
        return f"❌ Ошибка при удалении файла: {e}"

# Точка входа MCP-сервера
if __name__ == "__main__":
    logger.info("Запуск MCP-сервера FSManager...")
    mcp.run(transport="stdio") 