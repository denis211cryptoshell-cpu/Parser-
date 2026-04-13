from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart
from app.keyboards.inline import get_start_keyboard
from app.core.logging_config import get_logger
from app.config import settings

logger = get_logger("handlers.start")

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message):
    """Обработчик команды /start."""
    logger.info("Пользов запустил бота | User: {user} | ID: {id}", 
               user=message.from_user.full_name, id=message.from_user.id)
    
    text = (
        f"👋 <b>Привет, {message.from_user.full_name}!</b>\n\n"
        f"🤖 <b>Telegram Chat Parser Bot</b>\n\n"
        f"Я бот для мониторинга чатов по ключевым словам.\n"
        f"Отслеживаю сообщения в Telegram чатах и уведомляю о найденных совпадениях.\n\n"
        f"📊 <b>Возможности:</b>\n"
        f"• Мониторинг чатов\n"
        f"• Фильтрация по ключевым словам\n"
        f"• Уведомления в реальном времени\n"
        f"• Админ-панель для управления\n\n"
        f"Используйте кнопки ниже для навигации:"
    )
    
    await message.answer(
        text=text,
        reply_markup=get_start_keyboard(),
        parse_mode="HTML"
    )
    
    logger.info("Ответ отправлен | User: {user}", user=message.from_user.id)


@router.callback_query(F.data == "start:info")
async def cb_start_info(callback: CallbackQuery):
    """Обработчик кнопки 'О боте'."""
    logger.info("Пользователь запросил информацию | User: {user}", user=callback.from_user.id)
    
    text = (
        f"ℹ️ <b>О боте</b>\n\n"
        f"<b>Версия:</b> 1.0.0\n"
        f"<b>Стек:</b> Aiogram 3 + SQLAlchemy + Redis\n\n"
        f"<b>Функционал:</b>\n"
        f"• Парсинг чатов по ключевым словам\n"
        f"• Двухуровневое кеширование (L1 + L2)\n"
        f"• Inline админ-панель\n"
        f"• Готов к PostgreSQL\n\n"
        f"<b>Команды:</b>\n"
        f"/start - Главное меню\n"
        f"/admin - Админ-панель"
    )
    
    from app.keyboards.inline import get_back_to_admin_keyboard
    await callback.message.edit_text(
        text=text,
        reply_markup=get_back_to_admin_keyboard(),
        parse_mode="HTML"
    )
    
    await callback.answer()
    logger.info("Информация отправлена | User: {user}", user=callback.from_user.id)
