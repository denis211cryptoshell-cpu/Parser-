from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy import select, delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from app.database.models import MonitoredChat, Keyword, ParsedMessage
from app.core.cache import cache_manager
from app.config import settings
from app.core.logging_config import get_logger

logger = get_logger("services.admin_service")


class AdminService:
    """Бизнес-логика админ-панели."""
    
    # === Мониторинг чатов ===
    
    @staticmethod
    async def add_chat(session: AsyncSession, bot: Bot, chat_input: str) -> tuple[Optional[MonitoredChat], str]:
        """
        Добавить чат в мониторинг.
        
        Поддерживаемые форматы ввода:
        - ID: -1001234567890
        - Username: @example_chat
        - Ссылка: https://t.me/example_chat
        - Ссылка: t.me/example_chat
        
        Returns: (chat_obj или None, сообщение об ошибке/успехе)
        """
        logger.info("Добавление чата | Input: {input}", input=chat_input)
        
        chat_input = chat_input.strip()
        chat_id = None
        chat_title = None
        chat_username = None
        
        # Парсим ввод
        if chat_input.startswith("http://") or chat_input.startswith("https://"):
            # Ссылка: https://t.me/username
            chat_username = chat_input.rstrip("/").split("/")[-1]
            if chat_username.startswith("+"):
                return None, "❌ Ссылки-приглашения не поддерживаются. Отправьте ID или @username"
        elif chat_input.startswith("t.me/"):
            # Ссылка без протокола: t.me/username
            chat_username = chat_input.split("/")[-1]
        elif chat_input.startswith("@"):
            # Username: @example_chat
            chat_username = chat_input.replace("@", "")
        elif chat_input.lstrip("-").isdigit():
            # ID: -1001234567890
            chat_id = int(chat_input)
        else:
            return None, "❌ Неверный формат. Отправьте ID, @username или ссылку t.me/..."
        
        # Если есть username — получаем chat_id через API
        if chat_username:
            try:
                chat_obj = await bot.get_chat("@" + chat_username)
                chat_id = chat_obj.id
                chat_title = chat_obj.title
                logger.info("Получен chat_id через API | Username: {user} | ID: {id}", 
                           user=chat_username, id=chat_id)
            except TelegramAPIError as e:
                logger.error("Ошибка получения чата через API: {error}", error=str(e))
                return None, f"❌ Не удалось найти чат: {str(e)}"
        
        # Проверяем существует ли
        cached = await cache_manager.get(f"chat:{chat_id}")
        if cached:
            logger.warning("Чат уже в кеше | ID: {chat_id}", chat_id=chat_id)
            return None, "⚠️ Чат уже добавлен"
        
        result = await session.execute(
            select(MonitoredChat).where(MonitoredChat.chat_id == chat_id)
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            logger.warning("Чат уже существует | ID: {chat_id}", chat_id=chat_id)
            return None, f"⚠️ Чат уже добавлен: {existing.chat_title or existing.chat_username}"
        
        new_chat = MonitoredChat(
            chat_id=chat_id,
            chat_title=chat_title,
            chat_username=chat_username,
            is_active=True
        )
        session.add(new_chat)
        await session.commit()
        await session.refresh(new_chat)
        
        # Кешируем
        await cache_manager.set(f"chat:{chat_id}", {
            "id": new_chat.id,
            "chat_id": chat_id,
            "title": chat_title,
            "username": chat_username
        }, ttl_l1=settings.cache_ttl_l1, ttl_l2=settings.cache_ttl_l2)
        
        logger.info("Чат добавлен | ID: {chat_id} | DB ID: {db_id} | Title: {title}", 
                   chat_id=chat_id, db_id=new_chat.id, title=chat_title)
        return new_chat, f"✅ Чат добавлен!\n\n📝 <b>{chat_title or chat_username}</b>\n🆔 ID: <code>{chat_id}</code>"
    
    @staticmethod
    async def remove_chat(session: AsyncSession, chat_id: int) -> bool:
        """Удалить чат из мониторинга."""
        logger.info("Удаление чата | ID: {chat_id}", chat_id=chat_id)
        
        result = await session.execute(
            select(MonitoredChat).where(MonitoredChat.chat_id == chat_id)
        )
        chat = result.scalar_one_or_none()
        
        if not chat:
            logger.warning("Чат не найден для удаления | ID: {chat_id}", chat_id=chat_id)
            return False
        
        await session.delete(chat)
        await session.commit()
        
        # Удаляем из кеша
        await cache_manager.delete(f"chat:{chat_id}")
        
        logger.info("Чат удалён | ID: {chat_id}", chat_id=chat_id)
        return True
    
    @staticmethod
    async def get_chats(session: AsyncSession) -> List[MonitoredChat]:
        """Получить все monitored чаты."""
        cache_key = "chats:all"
        
        # Проверяем кеш
        cached = await cache_manager.get(cache_key)
        if cached:
            logger.debug("Чаты из кеша | Count: {count}", count=len(cached))
            return [MonitoredChat(**data) for data in cached]
        
        result = await session.execute(
            select(MonitoredChat).where(MonitoredChat.is_active == True).order_by(MonitoredChat.created_at.desc())
        )
        chats = result.scalars().all()
        
        # Кешируем
        chats_data = [{
            "id": c.id,
            "chat_id": c.chat_id,
            "chat_title": c.chat_title,
            "chat_username": c.chat_username,
            "is_active": c.is_active
        } for c in chats]
        await cache_manager.set(cache_key, chats_data, 
                               ttl_l1=settings.cache_ttl_l1, ttl_l2=settings.cache_ttl_l2)
        
        logger.info("Получены чаты | Count: {count}", count=len(chats))
        return chats
    
    # === Ключевые слова ===
    
    @staticmethod
    async def add_keyword(session: AsyncSession, word: str) -> Optional[Keyword]:
        """Добавить ключевое слово."""
        word = word.strip().lower()
        logger.info("Добавление ключевого слова | Word: {word}", word=word)
        
        # Проверяем кеш
        cached = await cache_manager.get(f"keyword:{word}")
        if cached:
            logger.warning("Слово уже в кеше | Word: {word}", word=word)
            return None
        
        result = await session.execute(
            select(Keyword).where(Keyword.word == word)
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            logger.warning("Слово уже существует | Word: {word}", word=word)
            return existing
        
        new_keyword = Keyword(word=word, is_active=True)
        session.add(new_keyword)
        await session.commit()
        await session.refresh(new_keyword)
        
        # Кешируем
        await cache_manager.set(f"keyword:{word}", {
            "id": new_keyword.id,
            "word": word
        }, ttl_l1=settings.cache_ttl_l1, ttl_l2=settings.cache_ttl_l2)
        
        # Сбрасываем кеш списка
        await cache_manager.delete("keywords:all")
        
        logger.info("Ключевое слово добавлено | Word: {word} | ID: {id}", 
                   word=word, id=new_keyword.id)
        return new_keyword
    
    @staticmethod
    async def remove_keyword(session: AsyncSession, word: str) -> bool:
        """Удалить ключевое слово."""
        word = word.strip().lower()
        logger.info("Удаление ключевого слова | Word: {word}", word=word)
        
        result = await session.execute(
            select(Keyword).where(Keyword.word == word)
        )
        keyword = result.scalar_one_or_none()
        
        if not keyword:
            logger.warning("Слово не найдено | Word: {word}", word=word)
            return False
        
        await session.delete(keyword)
        await session.commit()
        
        # Удаляем из кеша
        await cache_manager.delete(f"keyword:{word}")
        await cache_manager.delete("keywords:all")
        
        logger.info("Ключевое слово удалено | Word: {word}", word=word)
        return True
    
    @staticmethod
    async def get_keywords(session: AsyncSession) -> List[Keyword]:
        """Получить все активные ключевые слова."""
        cache_key = "keywords:all"
        
        # Проверяем кеш
        cached = await cache_manager.get(cache_key)
        if cached:
            logger.debug("Ключевые слова из кеша | Count: {count}", count=len(cached))
            return [Keyword(**data) for data in cached]
        
        result = await session.execute(
            select(Keyword).where(Keyword.is_active == True).order_by(Keyword.created_at.desc())
        )
        keywords = result.scalars().all()
        
        # Кешируем
        keywords_data = [{
            "id": k.id,
            "word": k.word,
            "is_active": k.is_active
        } for k in keywords]
        await cache_manager.set(cache_key, keywords_data,
                               ttl_l1=settings.cache_ttl_l1, ttl_l2=settings.cache_ttl_l2)
        
        logger.info("Получены ключевые слова | Count: {count}", count=len(keywords))
        return keywords
    
    # === Парсенные сообщения ===
    
    @staticmethod
    async def get_parsed_messages(session: AsyncSession, page: int = 1, 
                                  limit: int = 10) -> tuple[List[ParsedMessage], int]:
        """Получить парсенные сообщения с пагинацией."""
        offset = (page - 1) * limit
        
        # Общее количество
        count_result = await session.execute(select(func.count(ParsedMessage.id)))
        total = count_result.scalar()
        
        # Сообщения
        result = await session.execute(
            select(ParsedMessage)
            .order_by(ParsedMessage.parsed_at.desc())
            .offset(offset)
            .limit(limit)
        )
        messages = result.scalars().all()
        
        has_next = offset + limit < total
        has_prev = page > 1
        
        logger.info("Получены сообщения | Page: {page} | Count: {count} | Total: {total}", 
                   page=page, count=len(messages), total=total)
        
        return messages, total, has_next, has_prev
    
    @staticmethod
    async def get_parsed_message(session: AsyncSession, message_id: int) -> Optional[ParsedMessage]:
        """Получить одно парсенное сообщение."""
        cache_key = f"parsed_msg:{message_id}"
        
        # Проверяем кеш
        cached = await cache_manager.get(cache_key)
        if cached:
            logger.debug("Сообщение из кеша | ID: {id}", id=message_id)
            return ParsedMessage(**cached)
        
        result = await session.execute(
            select(ParsedMessage).where(ParsedMessage.id == message_id)
        )
        message = result.scalar_one_or_none()
        
        if message:
            # Кешируем
            msg_data = {
                "id": message.id,
                "message_id": message.message_id,
                "chat_id": message.chat_id,
                "chat_title": message.chat_title,
                "user_id": message.user_id,
                "username": message.username,
                "text": message.text,
                "matched_keywords": message.matched_keywords,
                "message_link": message.message_link,
                "parsed_at": message.parsed_at.isoformat() if message.parsed_at else None,
                "is_sent": message.is_sent
            }
            await cache_manager.set(cache_key, msg_data,
                                   ttl_l1=settings.cache_ttl_l1, ttl_l2=settings.cache_ttl_l2)
        
        logger.info("Получено сообщение | ID: {id}", id=message_id)
        return message
    
    # === Статистика ===
    
    @staticmethod
    async def get_statistics(session: AsyncSession) -> Dict[str, Any]:
        """Получить статистику."""
        cache_key = "stats:general"
        
        # Проверяем кеш
        cached = await cache_manager.get(cache_key)
        if cached:
            logger.debug("Статистика из кеша")
            return cached
        
        # Чаты
        chats_result = await session.execute(
            select(func.count(MonitoredChat.id)).where(MonitoredChat.is_active == True)
        )
        chats_count = chats_result.scalar()
        
        # Ключевые слова
        keywords_result = await session.execute(
            select(func.count(Keyword.id)).where(Keyword.is_active == True)
        )
        keywords_count = keywords_result.scalar()
        
        # Сообщения
        messages_result = await session.execute(
            select(func.count(ParsedMessage.id))
        )
        messages_count = messages_result.scalar()
        
        stats = {
            "chats": chats_count,
            "keywords": keywords_count,
            "messages": messages_count
        }
        
        # Кешируем
        await cache_manager.set(cache_key, stats,
                               ttl_l1=settings.cache_ttl_l1, ttl_l2=settings.cache_ttl_l2)
        
        logger.info("Статистика | Chats: {chats} | Keywords: {kw} | Messages: {msg}",
                   chats=chats_count, kw=keywords_count, msg=messages_count)
        return stats
