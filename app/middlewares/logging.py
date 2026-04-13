from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from app.core.logging_config import get_logger

logger = get_logger("middlewares.logging")


class LoggingMiddleware(BaseMiddleware):
    """Middleware для логирования всех запросов."""
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        """Логирование запроса."""
        
        # Логируем входящий запрос
        event_type = event.__class__.__name__
        
        if hasattr(event, 'from_user') and event.from_user:
            user_id = event.from_user.id
            user_name = event.from_user.full_name
            logger.info(
                "← Request | Type: {type} | User: {user} ({user_id})",
                type=event_type,
                user=user_name,
                user_id=user_id
            )
        else:
            logger.info("← Request | Type: {type}", type=event_type)
        
        # Вызываем handler
        try:
            result = await handler(event, data)
            logger.debug("✓ Handler completed | Type: {type}", type=event_type)
            return result
        except Exception as e:
            logger.error(
                "✗ Handler error | Type: {type} | Error: {error}",
                type=event_type,
                error=str(e)
            )
            raise
