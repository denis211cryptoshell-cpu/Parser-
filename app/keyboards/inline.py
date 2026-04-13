from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from app.core.logging_config import get_logger

logger = get_logger("keyboards.inline")


def get_start_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для /start."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="📊 Админ-панель",
            callback_data="admin:main"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="ℹ️ О боте",
            callback_data="start:info"
        )
    )
    logger.debug("Создана клавиатура: start")
    return builder.as_markup()


def get_admin_main_keyboard() -> InlineKeyboardMarkup:
    """Главное меню админ-панели."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="💬 Чаты", callback_data="admin:chats"),
        InlineKeyboardButton(text="🔑 Ключевые слова", callback_data="admin:keywords")
    )
    builder.row(
        InlineKeyboardButton(text="📨 Сообщения", callback_data="admin:messages"),
        InlineKeyboardButton(text="⚙️ Настройки", callback_data="admin:settings")
    )
    builder.row(
        InlineKeyboardButton(text="🔄 Обновить", callback_data="admin:refresh")
    )
    logger.debug("Создана клавиатура: admin_main")
    return builder.as_markup()


def get_chat_list_keyboard(chat_count: int = 0) -> InlineKeyboardMarkup:
    """Клавиатура списка чатов."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="➕ Добавить чат", callback_data="chat:add")
    )
    if chat_count > 0:
        builder.row(
            InlineKeyboardButton(text="🗑 Удалить чат", callback_data="chat:remove")
        )
    builder.row(
        InlineKeyboardButton(text="🔙 Назад", callback_data="admin:back_to_main")
    )
    logger.debug("Создана клавиатура: chat_list | Count: {count}", count=chat_count)
    return builder.as_markup()


def get_keyword_list_keyboard(keyword_count: int = 0) -> InlineKeyboardMarkup:
    """Клавиатура списка ключевых слов."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="➕ Добавить слово", callback_data="keyword:add")
    )
    if keyword_count > 0:
        builder.row(
            InlineKeyboardButton(text="🗑 Удалить слово", callback_data="keyword:remove")
        )
    builder.row(
        InlineKeyboardButton(text="🔙 Назад", callback_data="admin:back_to_main")
    )
    logger.debug("Создана клавиатура: keyword_list | Count: {count}", count=keyword_count)
    return builder.as_markup()


def get_message_list_keyboard(has_next: bool = False, has_prev: bool = False, 
                               page: int = 1, message_id: int = None) -> InlineKeyboardMarkup:
    """Клавиатура списка сообщений."""
    builder = InlineKeyboardBuilder()
    
    if message_id:
        builder.row(
            InlineKeyboardButton(
                text="🔗 Открыть в чате",
                callback_data=f"message:open:{message_id}"
            )
        )
    
    nav_buttons = []
    if has_prev:
        nav_buttons.append(InlineKeyboardButton(
            text="⬅️ Пред.", callback_data=f"messages:page:{page-1}"
        ))
    if has_next:
        nav_buttons.append(InlineKeyboardButton(
            text="➡️ След.", callback_data=f"messages:page:{page+1}"
        ))
    
    if nav_buttons:
        builder.row(*nav_buttons)
    
    builder.row(
        InlineKeyboardButton(text="🔙 Назад", callback_data="admin:back_to_main")
    )
    
    logger.debug("Создана клавиатура: message_list | Page: {page}", page=page)
    return builder.as_markup()


def get_back_to_admin_keyboard() -> InlineKeyboardMarkup:
    """Кнопка 'Назад' в админку."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🔙 В админ-панель", callback_data="admin:back_to_main")
    )
    logger.debug("Создана клавиатура: back_to_admin")
    return builder.as_markup()


def get_settings_keyboard(monitoring_active: bool = False) -> InlineKeyboardMarkup:
    """Клавиатура настроек."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📈 Статистика", callback_data="settings:stats")
    )
    builder.row(
        InlineKeyboardButton(text="🤖 Userbot", callback_data="userbot:status")
    )
    builder.row(
        InlineKeyboardButton(text="🧹 Очистить кеш", callback_data="settings:clear_cache")
    )
    builder.row(
        InlineKeyboardButton(
            text="⏹️ Остановить мониторинг" if monitoring_active else "▶️ Запустить мониторинг",
            callback_data="settings:toggle_monitor"
        )
    )
    builder.row(
        InlineKeyboardButton(text="🔙 Назад", callback_data="admin:back_to_main")
    )
    logger.debug("Создана клавиатура: settings | Monitoring: {mon}", mon=monitoring_active)
    return builder.as_markup()
