from typing import List
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from app.database.models import ParsedMessage
from app.config import settings
from app.core.logging_config import get_logger

logger = get_logger("services.notification")


class NotificationService:
    """Сервис уведомлений для админ-панели."""
    
    def __init__(self, bot: Bot):
        self.bot = bot
        logger.info("NotificationService инициализирован")
    
    async def notify_new_message(self, admin_ids: List[int], message: ParsedMessage):
        """Уведомить админов о новом найденном сообщении."""
        logger.info("Отправка уведомления | Message ID: {id} | Admins: {count}", 
                   id=message.id, count=len(admin_ids))
        
        text = (
            f"🔍 <b>Найдено новое сообщение!</b>\n\n"
            f"📝 <b>Группа:</b> {message.chat_title or 'N/A'}\n"
            f"👤 <b>Отправитель ID:</b> <code>{message.user_id or 'N/A'}</code>\n"
            f"🔑 <b>Ключевые слова:</b> <code>{message.matched_keywords}</code>\n\n"
            f"💬 <b>Сообщение:</b>\n"
            f"<blockquote>{message.text[:800] if message.text else 'Текст отсутствует'}</blockquote>\n\n"
            f"🆔 <b>Message ID:</b> <code>{message.message_id}</code>"
        )
        
        # Кнопка для перехода к сообщению
        builder = InlineKeyboardBuilder()
        if message.message_link:
            builder.row(
                InlineKeyboardButton(
                    text="🔗 Открыть в чате",
                    url=message.message_link
                )
            )
        
        sent_count = 0
        for admin_id in admin_ids:
            try:
                await self.bot.send_message(
                    chat_id=admin_id,
                    text=text,
                    reply_markup=builder.as_markup() if message.message_link else None,
                    parse_mode="HTML"
                )
                sent_count += 1
                logger.debug("Уведомление отправлено | Admin: {admin_id}", admin_id=admin_id)
            except Exception as e:
                logger.error("Ошибка отправки уведомления | Admin: {admin_id} | Error: {error}", 
                           admin_id=admin_id, error=str(e))
        
        # Отмечаем как отправленное
        if sent_count > 0:
            message.is_sent = True
        
        logger.info("Уведомления отправлены | Sent: {sent}/{total}", 
                   sent=sent_count, total=len(admin_ids))
    
    async def send_admin_message(self, admin_id: int, text: str, 
                                reply_markup: InlineKeyboardMarkup = None):
        """Отправить сообщение админу."""
        try:
            await self.bot.send_message(
                chat_id=admin_id,
                text=text,
                reply_markup=reply_markup,
                parse_mode="HTML"
            )
            logger.debug("Сообщение отправлено админу | Admin: {admin_id}", admin_id=admin_id)
        except Exception as e:
            logger.error("Ошибка отправки сообщения | Admin: {admin_id} | Error: {error}", 
                        admin_id=admin_id, error=str(e))
    
    @staticmethod
    def format_parsed_message(message: ParsedMessage) -> str:
        """Форматировать сообщение для отображения."""
        text = (
            f"📊 <b>Детали сообщения</b>\n\n"
            f"📝 <b>Группа:</b> {message.chat_title or 'N/A'}\n"
            f"🆔 <b>Chat ID:</b> <code>{message.chat_id}</code>\n"
            f"👤 <b>Отправитель:</b> {message.username or 'N/A'}\n"
            f"🔢 <b>User ID:</b> <code>{message.user_id or 'N/A'}</code>\n"
            f"🔑 <b>Ключевые слова:</b> <code>{message.matched_keywords or 'N/A'}</code>\n"
            f"🕒 <b>Время:</b> {message.parsed_at.strftime('%d.%m.%Y %H:%M') if message.parsed_at else 'N/A'}\n\n"
            f"💬 <b>Сообщение:</b>\n"
            f"<blockquote>{message.text[:900] if message.text else 'Текст отсутствует'}</blockquote>"
        )
        
        return text
