from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram import Bot
from sqlalchemy.ext.asyncio import AsyncSession
import asyncio
from app.keyboards.inline import (
    get_admin_main_keyboard,
    get_chat_list_keyboard,
    get_keyword_list_keyboard,
    get_message_list_keyboard,
    get_back_to_admin_keyboard,
    get_settings_keyboard
)
from app.services.admin_service import AdminService
from app.services.notification import NotificationService
from app.fsm.states import AdminStates
from app.core.logging_config import get_logger
from app.config import settings

logger = get_logger("handlers.admin")

router = Router()


def is_admin(user_id: int) -> bool:
    """Проверка является ли пользователь админом."""
    return user_id in settings.get_admin_ids()


# === ГЛАВНОЕ МЕНЮ АДМИНКИ ===

@router.callback_query(F.data == "admin:main")
async def cb_admin_main(callback: CallbackQuery, state: FSMContext):
    """Главное меню админ-панели."""
    logger.info("Вход в админ-панель | User: {user}", user=callback.from_user.id)
    
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ У вас нет доступа", show_alert=True)
        logger.warning("Попытка доступа не админа | User: {user}", user=callback.from_user.id)
        return
    
    await state.set_state(AdminStates.main_menu)
    
    text = (
        f"⚙️ <b>Админ-панель</b>\n\n"
        f"Выберите раздел:"
    )
    
    await callback.message.edit_text(
        text=text,
        reply_markup=get_admin_main_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "admin:refresh")
async def cb_admin_refresh(callback: CallbackQuery, state: FSMContext):
    """Обновить данные."""
    logger.info("Обновление админ-панели | User: {user}", user=callback.from_user.id)
    
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ У вас нет доступа", show_alert=True)
        return
    
    await callback.message.edit_text(
        text="⚙️ <b>Админ-панель</b>\n\nДанные обновлены.\nВыберите раздел:",
        reply_markup=get_admin_main_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer("✅ Обновлено", show_alert=False)


@router.callback_query(F.data == "admin:back_to_main")
async def cb_admin_back(callback: CallbackQuery, state: FSMContext):
    """Вернуться в главное меню админки."""
    logger.info("Возврат в главное меню | User: {user}", user=callback.from_user.id)
    
    await state.set_state(AdminStates.main_menu)
    
    await callback.message.edit_text(
        text="⚙️ <b>Админ-панель</b>\n\nВыберите раздел:",
        reply_markup=get_admin_main_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


# === УПРАВЛЕНИЕ ЧАТАМИ ===

@router.callback_query(F.data == "admin:chats")
async def cb_admin_chats(callback: CallbackQuery, session: AsyncSession):
    """Меню управления чатами."""
    logger.info("Открыто меню чатов | User: {user}", user=callback.from_user.id)
    
    chats = await AdminService.get_chats(session)
    
    if chats:
        chat_list = "\n".join([
            f"• {chat.chat_title or chat.chat_username} (<code>{chat.chat_id}</code>)"
            for chat in chats[:10]
        ])
        
        text = (
            f"💬 <b>Мониторинг чатов</b>\n\n"
            f"<b>Всего:</b> {len(chats)}\n\n"
            f"<b>Список:</b>\n{chat_list}"
        )
    else:
        text = (
            f"💬 <b>Мониторинг чатов</b>\n\n"
            f"Нет добавленных чатов.\n"
            f"Нажмите ➕ чтобы добавить."
        )
    
    await callback.message.edit_text(
        text=text,
        reply_markup=get_chat_list_keyboard(len(chats)),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "chat:add")
async def cb_chat_add(callback: CallbackQuery, state: FSMContext):
    """Добавить чат - запрос ID."""
    logger.info("Добавление чата | User: {user}", user=callback.from_user.id)
    
    await state.set_state(AdminStates.chat_add)
    
    text = (
        f"➕ <b>Добавить чат</b>\n\n"
        f"Отправьте ID, username или ссылку:\n\n"
        f"<b>Примеры:</b>\n"
        f"• <code>-1001234567890</code> (ID)\n"
        f"• <code>@example_chat</code> (username)\n"
        f"• <code>https://t.me/example_chat</code> (ссылка)\n"
        f"• <code>t.me/example_chat</code> (ссылка)\n\n"
        f"Или нажмите 🔙 Назад."
    )
    
    await callback.message.edit_text(
        text=text,
        reply_markup=get_back_to_admin_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(AdminStates.chat_add)
async def process_chat_add(message: Message, state: FSMContext, session: AsyncSession, bot: Bot):
    """Обработка добавления чата."""
    logger.info("Обработка добавления чата | User: {user} | Input: {input}", 
               user=message.from_user.id, input=message.text)
    
    chat_input = message.text.strip()
    chat, result_text = await AdminService.add_chat(session, bot, chat_input)
    
    await message.answer(
        text=result_text,
        reply_markup=get_back_to_admin_keyboard(),
        parse_mode="HTML"
    )
    
    if chat:
        await state.set_state(AdminStates.main_menu)
        logger.info("Чат добавлен | User: {user} | Chat: {chat}", 
                   user=message.from_user.id, chat=chat_input)
    else:
        logger.warning("Не удалось добавить чат | User: {user} | Input: {input}", 
                      user=message.from_user.id, input=chat_input)


# === УПРАВЛЕНИЕ КЛЮЧЕВЫМИ СЛОВАМИ ===

@router.callback_query(F.data == "admin:keywords")
async def cb_admin_keywords(callback: CallbackQuery, session: AsyncSession):
    """Меню управления ключевыми словами."""
    logger.info("Открыто меню ключевых слов | User: {user}", user=callback.from_user.id)
    
    keywords = await AdminService.get_keywords(session)
    
    if keywords:
        kw_list = "\n".join([f"• <code>{kw.word}</code>" for kw in keywords[:10]])
        
        text = (
            f"🔑 <b>Ключевые слова</b>\n\n"
            f"<b>Всего:</b> {len(keywords)}\n\n"
            f"<b>Список:</b>\n{kw_list}"
        )
    else:
        text = (
            f"🔑 <b>Ключевые слова</b>\n\n"
            f"Нет добавленных слов.\n"
            f"Нажмите ➕ чтобы добавить."
        )
    
    await callback.message.edit_text(
        text=text,
        reply_markup=get_keyword_list_keyboard(len(keywords)),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "keyword:add")
async def cb_keyword_add(callback: CallbackQuery, state: FSMContext):
    """Добавить ключевое слово."""
    logger.info("Добавление ключевого слова | User: {user}", user=callback.from_user.id)
    
    await state.set_state(AdminStates.keyword_add)
    
    text = (
        f"➕ <b>Добавить ключевое слово</b>\n\n"
        f"Отправьте слово для отслеживания.\n\n"
        f"Или нажмите 🔙 Назад."
    )
    
    await callback.message.edit_text(
        text=text,
        reply_markup=get_back_to_admin_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(AdminStates.keyword_add)
async def process_keyword_add(message: Message, state: FSMContext, session: AsyncSession):
    """Обработка добавления ключевого слова."""
    logger.info("Обработка добавления слова | User: {user} | Word: {word}", 
               user=message.from_user.id, word=message.text)
    
    word = message.text.strip()
    keyword = await AdminService.add_keyword(session, word)
    
    if keyword:
        text = f"✅ <b>Слово добавлено!</b>\n\n<code>{keyword.word}</code>"
    else:
        text = "⚠️ Слово уже существует."
    
    await message.answer(
        text=text,
        reply_markup=get_back_to_admin_keyboard(),
        parse_mode="HTML"
    )
    
    await state.set_state(AdminStates.main_menu)
    logger.info("Слово добавлено | User: {user} | Word: {word}", 
               user=message.from_user.id, word=word)


# === ПРОСМОТР СООБЩЕНИЙ ===

@router.callback_query(F.data == "admin:messages")
async def cb_admin_messages(callback: CallbackQuery, session: AsyncSession):
    """Просмотр парсенных сообщений."""
    logger.info("Открыто меню сообщений | User: {user}", user=callback.from_user.id)
    
    messages, total, has_next, has_prev = await AdminService.get_parsed_messages(session, page=1)
    
    if messages:
        msg = messages[0]
        text = (
            f"📨 <b>Парсенные сообщения</b>\n\n"
            f"<b>Всего:</b> {total}\n"
            f"<b>Страница:</b> 1\n\n"
            f"<b>Последнее:</b>\n"
            f"📝 Группа: {msg.chat_title or 'N/A'}\n"
            f"👤 User ID: <code>{msg.user_id or 'N/A'}</code>\n"
            f"🔑 Ключи: <code>{msg.matched_keywords}</code>\n\n"
            f"{msg.text[:200] if msg.text else 'Нет текста'}..."
        )
        
        keyboard = get_message_list_keyboard(
            has_next=has_next, 
            has_prev=has_prev, 
            page=1,
            message_id=msg.id
        )
    else:
        text = (
            f"📨 <b>Парсенные сообщения</b>\n\n"
            f"Сообщений пока нет."
        )
        keyboard = get_back_to_admin_keyboard()
    
    await callback.message.edit_text(
        text=text,
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("messages:page:"))
async def cb_messages_page(callback: CallbackQuery, session: AsyncSession):
    """Пагинация сообщений."""
    page = int(callback.data.split(":")[2])
    logger.info("Пагинация сообщений | User: {user} | Page: {page}", 
               user=callback.from_user.id, page=page)
    
    messages, total, has_next, has_prev = await AdminService.get_parsed_messages(session, page=page)
    
    if messages:
        msg = messages[0]
        text = (
            f"📨 <b>Парсенные сообщения</b>\n\n"
            f"<b>Всего:</b> {total}\n"
            f"<b>Страница:</b> {page}\n\n"
            f"<b>Последнее:</b>\n"
            f"📝 Группа: {msg.chat_title or 'N/A'}\n"
            f"👤 User ID: <code>{msg.user_id or 'N/A'}</code>\n"
            f"🔑 Ключи: <code>{msg.matched_keywords}</code>\n\n"
            f"{msg.text[:200] if msg.text else 'Нет текста'}..."
        )
        
        keyboard = get_message_list_keyboard(
            has_next=has_next,
            has_prev=has_prev,
            page=page,
            message_id=msg.id
        )
    else:
        text = "Сообщений нет."
        keyboard = get_back_to_admin_keyboard()
    
    await callback.message.edit_text(
        text=text,
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("message:open:"))
async def cb_message_open(callback: CallbackQuery, session: AsyncSession):
    """Открыть детали сообщения."""
    message_id = int(callback.data.split(":")[2])
    logger.info("Открыто сообщение | User: {user} | Msg ID: {id}", 
               user=callback.from_user.id, id=message_id)
    
    message = await AdminService.get_parsed_message(session, message_id)
    
    if message:
        text = NotificationService.format_parsed_message(message)
        keyboard = get_back_to_admin_keyboard()
        
        if message.message_link:
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            from aiogram.utils.keyboard import InlineKeyboardBuilder
            builder = InlineKeyboardBuilder()
            builder.row(InlineKeyboardButton(text="🔗 Открыть в чате", url=message.message_link))
            builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="admin:back_to_main"))
            keyboard = builder.as_markup()
        
        await callback.message.edit_text(
            text=text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    else:
        await callback.answer("❌ Сообщение не найдено", show_alert=True)


# === НАСТРОЙКИ ===

@router.callback_query(F.data == "admin:settings")
async def cb_admin_settings(callback: CallbackQuery):
    """Меню настроек."""
    logger.info("Открыто меню настроек | User: {user}", user=callback.from_user.id)
    
    from app.main import chat_monitor
    monitoring_active = chat_monitor.is_running if chat_monitor else False
    
    text = (
        f"⚙️ <b>Настройки</b>\n\n"
        f"📡 <b>Мониторинг:</b> {'✅ Активен' if monitoring_active else '❌ Остановлен'}\n"
        f"🔄 <b>Интервал:</b> {chat_monitor.polling_interval}s\n\n"
        f"Выберите действие:"
    )
    
    await callback.message.edit_text(
        text=text,
        reply_markup=get_settings_keyboard(monitoring_active),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "settings:stats")
async def cb_settings_stats(callback: CallbackQuery, session: AsyncSession):
    """Показать статистику."""
    logger.info("Запрос статистики | User: {user}", user=callback.from_user.id)
    
    stats = await AdminService.get_statistics(session)
    
    text = (
        f"📈 <b>Статистика</b>\n\n"
        f"💬 <b>Чатов:</b> {stats['chats']}\n"
        f"🔑 <b>Ключевых слов:</b> {stats['keywords']}\n"
        f"📨 <b>Сообщений:</b> {stats['messages']}"
    )
    
    await callback.message.edit_text(
        text=text,
        reply_markup=get_settings_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "settings:clear_cache")
async def cb_settings_clear_cache(callback: CallbackQuery):
    """Очистить кеш."""
    logger.info("Очистка кеша | User: {user}", user=callback.from_user.id)
    
    from app.core.cache import cache_manager
    cache_manager.l1_cache.clear()
    
    await callback.answer("✅ Кеш очищен", show_alert=True)
    
    await callback.message.edit_text(
        text="✅ <b>Кеш очищен!</b>",
        reply_markup=get_settings_keyboard(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "settings:toggle_monitor")
async def cb_settings_toggle_monitor(callback: CallbackQuery):
    """Включить/выключить мониторинг."""
    logger.info("Переключение мониторинга | User: {user}", user=callback.from_user.id)
    
    from app.main import chat_monitor
    
    if not chat_monitor:
        await callback.answer("❌ Мониторинг не инициализирован", show_alert=True)
        return
    
    if chat_monitor.is_running:
        chat_monitor.stop_monitoring()
        text = "⏹️ <b>Мониторинг остановлен</b>"
    else:
        chat_monitor.is_running = True
        asyncio.create_task(chat_monitor.start_monitoring())
        text = "▶️ <b>Мониторинг запущен</b>"
    
    from app.main import chat_monitor
    monitoring_active = chat_monitor.is_running
    
    await callback.answer("✅ Переключено", show_alert=True)
    
    await callback.message.edit_text(
        text=f"⚙️ <b>Настройки</b>\n\n📡 <b>Мониторинг:</b> {'✅ Активен' if monitoring_active else '❌ Остановлен'}\n\nВыберите действие:",
        reply_markup=get_settings_keyboard(monitoring_active),
        parse_mode="HTML"
    )
