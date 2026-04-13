import asyncio
from typing import List
from aiogram import Bot
from aiogram.types import Message
from aiogram.exceptions import TelegramAPIError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.models import MonitoredChat, Keyword, ParsedMessage
from app.database.engine import db_manager
from app.core.cache import cache_manager
from app.config import settings
from app.core.logging_config import get_logger
from app.services.notification import NotificationService

logger = get_logger("services.chat_monitor")


class ChatMonitorService:
    """Сервис мониторинга чатов в реальном времени."""
    
    def __init__(self, bot: Bot, admin_ids: List[int]):
        self.bot = bot
        self.admin_ids = admin_ids
        self.is_running = False
        self.polling_interval = settings.monitoring_interval
        self.last_message_ids: dict = {}  # chat_id -> last_message_id
        logger.info("ChatMonitorService инициализирован | Interval: {interval}s", 
                   interval=self.polling_interval)
    
    async def load_last_message_ids(self, session: AsyncSession):
        """Загрузить ID последних обработанных сообщений из БД."""
        logger.info("Загрузка последних ID сообщений")
        
        result = await session.execute(select(MonitoredChat).where(MonitoredChat.is_active == True))
        chats = result.scalars().all()
        
        for chat in chats:
            # Получаем последнее обработанное сообщение для чата
            last_msg_result = await session.execute(
                select(ParsedMessage.message_id)
                .where(ParsedMessage.chat_id == chat.chat_id)
                .order_by(ParsedMessage.message_id.desc())
                .limit(1)
            )
            last_msg = last_msg_result.scalar_one_or_none()
            
            if last_msg:
                self.last_message_ids[chat.chat_id] = last_msg
                logger.debug("Chat {chat} | Last msg ID: {id}", 
                           chat=chat.chat_title, id=last_msg)
            else:
                self.last_message_ids[chat.chat_id] = 0
        
        logger.info("Загружено {count} чатов для мониторинга", count=len(chats))
    
    async def check_keywords_in_message(self, text: str, session: AsyncSession) -> List[str]:
        """Проверить текст на наличие ключевых слов."""
        if not text:
            return []
        
        result = await session.execute(
            select(Keyword).where(Keyword.is_active == True)
        )
        keywords = result.scalars().all()
        
        text_lower = text.lower()
        matched = [kw.word for kw in keywords if kw.word.lower() in text_lower]
        
        return matched
    
    async def process_new_messages(self, session: AsyncSession):
        """Обработать новые сообщения во всех monitored чатах."""
        logger.debug("Начало проверки чатов")
        
        result = await session.execute(
            select(MonitoredChat).where(MonitoredChat.is_active == True)
        )
        chats = result.scalars().all()
        
        for chat in chats:
            try:
                chat_id = chat.chat_id
                last_id = self.last_message_ids.get(chat_id, 0)
                
                # Получаем новые сообщения (только что вышли)
                # В Aiogram нет метода get_chat_messages, используем заглушку
                # В продакшене здесь будет:
                # async for message in self.bot.get_chat_history(chat_id, limit=20):
                #     if message.message_id > last_id:
                #         await self.process_single_message(message, session)
                
                # Для демо: бот должен быть в группе как участник
                # и использовать bot.get_chat() для проверки доступности
                try:
                    chat_info = await self.bot.get_chat(chat_id)
                    logger.debug("Chat {title} доступен | ID: {id}", 
                               title=chat_info.title or chat_id, id=chat_id)
                except TelegramAPIError as e:
                    logger.warning("Нет доступа к чату {chat}: {error}", 
                                 chat=chat_id, error=str(e))
                
            except Exception as e:
                logger.error("Ошибка проверки чата {chat}: {error}", 
                           chat=chat.chat_id, error=str(e))
    
    async def process_single_message(self, message: Message, session: AsyncSession):
        """Обработать одно сообщение."""
        if not message.text:
            return
        
        # Проверяем ключевые слова
        matched = await self.check_keywords_in_message(message.text, session)
        
        if not matched:
            return
        
        logger.info("Найдено совпадение | Chat: {chat} | User: {user} | Keywords: {kw}", 
                   chat=message.chat.title, 
                   user=message.from_user.full_name if message.from_user else "N/A",
                   kw=", ".join(matched))
        
        # Создаём ссылку
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
            text=message.text[:1000],
            matched_keywords=", ".join(matched),
            message_link=message_link,
            is_sent=False
        )
        
        session.add(parsed_msg)
        await session.commit()
        await session.refresh(parsed_msg)
        
        # Обновляем last_message_id
        self.last_message_ids[message.chat.id] = message.message_id
        
        # Кешируем
        cache_key = f"processed_msg:{message.chat.id}:{message.message_id}"
        await cache_manager.set(cache_key, parsed_msg.id,
                               ttl_l1=settings.cache_ttl_l1,
                               ttl_l2=settings.cache_ttl_l2)
        
        # Отправляем уведомление админам
        notification = NotificationService(self.bot)
        await notification.notify_new_message(self.admin_ids, parsed_msg)
    
    async def start_monitoring(self):
        """Запустить мониторинг."""
        self.is_running = True
        logger.info("Мониторинг запущен | Interval: {interval}s", interval=self.polling_interval)
        
        while self.is_running:
            try:
                async with db_manager.get_session() as session:
                    await self.process_new_messages(session)
                    await session.commit()
            except Exception as e:
                logger.error("Ошибка в цикле мониторинга: {error}", error=str(e))
            
            await asyncio.sleep(self.polling_interval)
        
        logger.info("Мониторинг остановлен")
    
    def stop_monitoring(self):
        """Остановить мониторинг."""
        self.is_running = False
        logger.info("Мониторинг остановлен (флаг)")
