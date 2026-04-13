import sys
from pathlib import Path
from loguru import logger
from app.config import settings


def setup_logging():
    """Настройка кастомного логирования через Loguru."""
    
    # Создаём директорию для логов
    log_path = Path(settings.log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Удаляем стандартный handler
    logger.remove()
    
    # Консольный вывод (DEBUG и выше)
    logger.add(
        sys.stderr,
        level=settings.log_level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
               "<level>{level: <8}</level> | "
               "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
               "<level>{message}</level>",
        colorize=True,
        backtrace=True,
        diagnose=True
    )
    
    # Файловый вывод (все уровни, ротация по 50MB, хранение 30 дней)
    logger.add(
        settings.log_file,
        level="DEBUG",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
        rotation="50 MB",
        retention="30 days",
        compression="zip",
        encoding="utf-8",
        backtrace=True,
        diagnose=True
    )
    
    logger.info("Логирование инициализировано | Level: {level} | File: {file}", 
                level=settings.log_level, file=settings.log_file)


def get_logger(name: str):
    """Получить логгер с именем модуля."""
    return logger.bind(module=name)
