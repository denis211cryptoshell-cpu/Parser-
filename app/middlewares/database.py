from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from app.database.engine import db_manager
from app.core.logging_config import get_logger

logger = get_logger("middlewares.database")


class DatabaseSessionMiddleware(BaseMiddleware):
    """Middleware для автоматического создания/закрытия сессии БД."""
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        """Создание сессии БД для запроса."""
        session = db_manager.get_session()
        data["session"] = session
        
        try:
            result = await handler(event, data)
            return result
        finally:
            await session.close()
            logger.debug("Сессия БД закрыта")
