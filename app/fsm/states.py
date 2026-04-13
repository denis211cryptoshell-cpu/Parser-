from aiogram.fsm.state import State, StatesGroup
from app.core.logging_config import get_logger

logger = get_logger("fsm.states")


class AdminStates(StatesGroup):
    """Состояния для админ-панели."""
    
    # Главное меню
    main_menu = State()
    
    # Управление чатами
    chat_list = State()
    chat_add = State()
    chat_remove = State()
    
    # Управление ключевыми словами
    keyword_list = State()
    keyword_add = State()
    keyword_remove = State()
    
    # Просмотр сообщений
    message_list = State()
    message_detail = State()
    
    # Настройки
    settings_menu = State()


logger.info("FSM состояния загружены: AdminStates")
