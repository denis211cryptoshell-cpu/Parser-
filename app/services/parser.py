from typing import List, Optional, Dict, Any
from datetime import datetime
import asyncio
from aiogram import Bot
from aiogram.types import Message
from aiogram.exceptions import TelegramForbiddenError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.models import MonitoredChat, Keyword, ParsedMessage
from app.core.cache import cache_manager
from app.config import settings
from app.core.logging_config import get_logger

logger = get_logger("services.parser")


class ParserService:
    """Сервис парсинга Telegram чатов."""
    
    def __init__(self, bot: Bot):
        self.bot = bot
        self.is_running = False
        logger.info("ParserService инициализирован")
    
    async def check_message_for_keywords(self, message: Message, session: AsyncSession) -> Optional[ParsedMessage]:
        """Проверить сообщение на наличие ключевых слов."""
        logger.debug("Проверка сообщения | Chat: {chat} | User: {user}", 
                    chat=message.chat.id, user=message.from_user.id if message.from_user else None)
        
        if not message.text:
            return None
        
        # Получаем ключевые слова
        keywords = await self._get_active_keywords(session)
        
        if not keywords:
            return None
        
        # Проверяем наличие ключевых слов
        text_lower = message.text.lower()
        matched = [kw.word for kw in keywords if kw.word.lower() in text_lower]
        
        if not matched:
            return None
        
        logger.info("Найдено совпадение | Chat: {chat} | Keywords: {kw}", 
                   chat=message.chat.title or message.chat.id, kw=", ".join(matched))
        
        # Создаём ссылку на сообщение
        message_link = f"https://t.me/c/{str(message.chat.id).replace('-100', '')}/{message.message_id}"
        
        if message.chat.username:
            message_link = f"https://t.me/{message.chat.username}/{message.message_id}"
        
        # Сохраняем в БД
        parsed_msg = ParsedMessage(
            message_id=message.message_id,
            chat_id=message.chat.id,
            chat_title=message.chat.title,
            user_id=message.from_user.id if message.from_user else None,
            username=message.from_user.username if message.from_user else None,
            text=message.text[:1000],  # Ограничиваем длину
            matched_keywords=", ".join(matched),
            message_link=message_link,
            is_sent=False
        )
        
        session.add(parsed_msg)
        await session.commit()
        await session.refresh(parsed_msg)
        
        # Кешируем ID обработанных сообщений
        cache_key = f"processed_msg:{message.chat.id}:{message.message_id}"
        await cache_manager.set(cache_key, parsed_msg.id, 
                               ttl_l1=settings.cache_ttl_l1, ttl_l2=settings.cache_ttl_l2)
        
        logger.info("Сообщение сохранено | ID: {id} | Keywords: {kw}", 
                   id=parsed_msg.id, kw=", ".join(matched))
        
        return parsed_msg
    
    async def parse_chat_history(self, session: AsyncSession, chat: MonitoredChat, 
                                limit: int = None) -> List[ParsedMessage]:
        """Парсинг истории чата."""
        limit = limit or settings.parsing_limit
        logger.info("Начало парсинга чата | Chat: {chat} | Limit: {limit}", 
                   chat=chat.chat_title or chat.chat_id, limit=limit)
        
        parsed_messages = []
        
        try:
            # Получаем последние сообщения из чата
            # В реальном боте здесь будет использование bot.get_chat_history()
            # Для демо используем заглушку
            
            history = await self._get_chat_history_stub(chat.chat_id, limit)
            
            for msg_data in history:
                # Проверяем кеш
                cache_key = f"processed_msg:{chat.chat_id}:{msg_data['message_id']}"
                cached = await cache_manager.get(cache_key)
                if cached:
                    logger.debug("Сообщение уже обработано | Msg ID: {id}", 
                               id=msg_data['message_id'])
                    continue
                
                # Проверяем ключевые слова
                if msg_data.get('text'):
                    keywords = await self._get_active_keywords(session)
                    text_lower = msg_data['text'].lower()
                    matched = [kw.word for kw in keywords if kw.word.lower() in text_lower]
                    
                    if matched:
                        message_link = f"https://t.me/c/{str(chat.chat_id).replace('-100', '')}/{msg_data['message_id']}"
                        if chat.chat_username:
                            message_link = f"https://t.me/{chat.chat_username}/{msg_data['message_id']}"
                        
                        parsed_msg = ParsedMessage(
                            message_id=msg_data['message_id'],
                            chat_id=chat.chat_id,
                            chat_title=chat.chat_title,
                            user_id=msg_data.get('user_id'),
                            username=msg_data.get('username'),
                            text=msg_data['text'][:1000],
                            matched_keywords=", ".join(matched),
                            message_link=message_link,
                            is_sent=False
                        )
                        
                        session.add(parsed_msg)
                        await session.commit()
                        await session.refresh(parsed_msg)
                        
                        await cache_manager.set(cache_key, parsed_msg.id,
                                               ttl_l1=settings.cache_ttl_l1, 
                                               ttl_l2=settings.cache_ttl_l2)
                        
                        parsed_messages.append(parsed_msg)
            
            logger.info("Парсинг завершён | Chat: {chat} | New messages: {count}", 
                       chat=chat.chat_title or chat.chat_id, count=len(parsed_messages))
            
        except Exception as e:
            logger.error("Ошибка парсинга чата {chat}: {error}", 
                        chat=chat.chat_id, error=str(e))
        
        return parsed_messages
    
    async def _get_active_keywords(self, session: AsyncSession) -> List[Keyword]:
        """Получить активные ключевые слова."""
        from app.services.admin_service import AdminService
        return await AdminService.get_keywords(session)
    
    async def _get_chat_history_stub(self, chat_id: int, limit: int) -> List[Dict[str, Any]]:
        """Заглушка для получения истории чата (демо)."""
        # В продакшене здесь будет:
        # messages = []
        # async for message in self.bot.get_chat_history(chat_id, limit=limit):
        #     messages.append({...})
        # return messages
        
        logger.warning("Используется заглушка для истории чата | Chat: {chat}", chat=chat_id)
        return []
    
    def start_parsing_loop(self):
        """Запустить цикл парсинга."""
        self.is_running = True
        logger.info("Цикл парсинга запущен")
    
    def stop_parsing_loop(self):
        """Остановить цикл парсинга."""
        self.is_running = False
        logger.info("Цикл парсинга остановлен")
