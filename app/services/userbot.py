import asyncio
from typing import List, Optional
from pyrogram import Client, filters, idle
from pyrogram.types import Message
from pyrogram.handlers import MessageHandler
from pyrogram.errors import RPCError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.engine import db_manager
from app.database.models import MonitoredChat, Keyword, ParsedMessage
from app.core.cache import cache_manager
from app.config import settings
from app.core.logging_config import get_logger
from app.services.notification import NotificationService

logger = get_logger("services.userbot")


class UserbotService:
    """Сервис Userbot на Pyrogram для чтения сообщений из чатов."""
    
    def __init__(self, admin_ids: List[int]):
        self.admin_ids = admin_ids
        self.app: Optional[Client] = None
        self.is_running = False
        self.monitored_chat_ids: set = set()
        self.last_message_ids: dict = {}  # chat_id -> last_message_id
        logger.info("UserbotService инициализирован")
    
    async def init_client(self):
        """Инициализация Pyrogram клиента."""
        if settings.api_id == 0 or not settings.api_hash:
            logger.warning("API ID/Hash не настроены. Userbot отключен.")
            return False
        
        self.app = Client(
            name="userbot",
            api_id=settings.api_id,
            api_hash=settings.api_hash,
            session_string=None,  # Будет сохранена после авторизации
            workdir=".",
            sleep_threshold=30
        )
        
        logger.info("Pyrogram клиент инициализирован | API ID: {api_id}", 
                   api_id=settings.api_id)
        return True
    
    async def start(self):
        """Запуск userbot."""
        if not self.app:
            if not await self.init_client():
                return False
        
        try:
            await self.app.start()
            me = await self.app.get_me()
            logger.info("Userbot запущен | User: {name} (@{username}) | ID: {id}",
                       name=me.first_name, username=me.username, id=me.id)
            self.is_running = True
            
            # Загружаем monitored чаты
            await self._load_monitored_chats()
            
            # Регистрируем handler для новых сообщений
            @self.app.on_message(filters.group & filters.incoming)
            async def handle_group_message(client: Client, message: Message):
                await self._process_message(message)
            
            @self.app.on_message(filters.channel & filters.incoming)
            async def handle_channel_message(client: Client, message: Message):
                await self._process_message(message)
            
            logger.info("Handlers зарегистрированы. Мониторинг запущен.")
            return True
            
        except Exception as e:
            logger.error("Ошибка запуска userbot: {error}", error=str(e))
            return False
    
    async def stop(self):
        """Остановка userbot."""
        self.is_running = False
        if self.app:
            await self.app.stop()
            logger.info("Userbot остановлен")
    
    async def _load_monitored_chats(self):
        """Загрузить monitored чаты из БД."""
        async with db_manager.get_session() as session:
            result = await session.execute(
                select(MonitoredChat).where(MonitoredChat.is_active == True)
            )
            chats = result.scalars().all()
            
            for chat in chats:
                self.monitored_chat_ids.add(chat.chat_id)
                
                # Загружаем последний message_id
                last_msg_result = await session.execute(
                    select(ParsedMessage.message_id)
                    .where(ParsedMessage.chat_id == chat.chat_id)
                    .order_by(ParsedMessage.message_id.desc())
                    .limit(1)
                )
                last_msg = last_msg_result.scalar_one_or_none()
                self.last_message_ids[chat.chat_id] = last_msg or 0
            
            logger.info("Загружено {count} чатов для мониторинга", count=len(chats))
    
    async def reload_monitored_chats(self):
        """Перезагрузить список monitored чатов."""
        self.monitored_chat_ids.clear()
        await self._load_monitored_chats()
        logger.info("Список чатов перезагружен")
    
    async def _process_message(self, message: Message):
        """Обработать входящее сообщение."""
        chat_id = message.chat.id
        
        logger.debug("Прочитано сообщение | Chat: {chat} | Msg ID: {id} | Text: {text}",
                    chat=message.chat.title or chat_id,
                    id=message.id,
                    text=message.text[:50] if message.text else "[no text]")
        
        # Проверяем monitored ли это чат
        if chat_id not in self.monitored_chat_ids:
            return
        
        # Проверяем дубликаты
        last_id = self.last_message_ids.get(chat_id, 0)
        if message.id <= last_id:
            return
        
        # Проверяем ключевые слова
        if not message.text:
            return
        
        matched = await self._check_keywords(message.text)
        if not matched:
            return
        
        logger.info("Найдено совпадение | Chat: {chat} | User: {user} | Keywords: {kw}",
                   chat=message.chat.title or chat_id,
                   user=message.from_user.first_name if message.from_user else "N/A",
                   kw=", ".join(matched))
        
        # Сохраняем в БД
        await self._save_message(message, matched)
        
        # Обновляем last_message_id
        self.last_message_ids[chat_id] = message.id
    
    async def _check_keywords(self, text: str) -> List[str]:
        """Проверить текст на ключевые слова."""
        async with db_manager.get_session() as session:
            result = await session.execute(
                select(Keyword).where(Keyword.is_active == True)
            )
            keywords = result.scalars().all()
            
            text_lower = text.lower()
            matched = [kw.word for kw in keywords if kw.word.lower() in text_lower]
            
            return matched
    
    async def _save_message(self, message: Message, matched_keywords: List[str]):
        """Сохранить сообщение в БД и отправить уведомление."""
        async with db_manager.get_session() as session:
            # Создаём ссылку
            message_link = f"https://t.me/c/{str(message.chat.id).replace('-100', '')}/{message.id}"
            if message.chat.username:
                message_link = f"https://t.me/{message.chat.username}/{message.id}"
            
            user_id = message.from_user.id if message.from_user else None
            username = message.from_user.username if message.from_user else None
            
            parsed_msg = ParsedMessage(
                message_id=message.id,
                chat_id=message.chat.id,
                chat_title=message.chat.title,
                user_id=user_id,
                username=username,
                text=message.text[:1000] if message.text else "",
                matched_keywords=", ".join(matched_keywords),
                message_link=message_link,
                is_sent=False
            )
            
            session.add(parsed_msg)
            await session.commit()
            await session.refresh(parsed_msg)
            
            # Кешируем
            cache_key = f"processed_msg:{message.chat.id}:{message.id}"
            await cache_manager.set(cache_key, parsed_msg.id,
                                   ttl_l1=settings.cache_ttl_l1,
                                   ttl_l2=settings.cache_ttl_l2)
            
            logger.info("Сообщение сохранено | ID: {id} | Keywords: {kw}",
                       id=parsed_msg.id, kw=", ".join(matched_keywords))
            
            # Отправляем уведомление админам через бота
            # notification будет вызвана из main.py т.к. там есть bot instance
            return parsed_msg
    
    async def add_chat(self, chat_identifier: str) -> tuple[bool, str]:
        """
        Добавить чат в мониторинг через userbot.
        
        Args:
            chat_identifier: username, ссылка или ID чата
            
        Returns:
            (success, message)
        """
        try:
            # Очищаем от ссылок
            if chat_identifier.startswith("https://t.me/"):
                chat_identifier = "@" + chat_identifier.split("/")[-1]
            elif chat_identifier.startswith("t.me/"):
                chat_identifier = "@" + chat_identifier.split("/")[-1]
            elif not chat_identifier.startswith("@") and not chat_identifier.startswith("-"):
                chat_identifier = "@" + chat_identifier
            
            # Получаем чат
            chat = await self.app.get_chat(chat_identifier)
            
            logger.info("Добавление чата через userbot | {chat}", chat=chat.title)
            
            return True, f"✅ Чат найден: {chat.title}\n🆔 ID: <code>{chat.id}</code>"
            
        except RPCError as e:
            logger.error("Ошибка добавления чата: {error}", error=str(e))
            return False, f"❌ Ошибка: {str(e)}"
    
    async def get_my_chats(self) -> List[dict]:
        """Получить все чаты userbot."""
        if not self.app:
            return []
        
        chats = []
        async for dialog in self.app.get_dialogs(limit=100):
            chats.append({
                "id": dialog.chat.id,
                "title": dialog.chat.title,
                "type": dialog.chat.type,
                "username": dialog.chat.username
            })
        
        return chats
    
    def is_authenticated(self) -> bool:
        """Проверена ли сессия."""
        return self.app is not None and self.is_running
