import asyncio
from pathlib import Path
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.client.session.aiohttp import AiohttpSession
from app.config import settings
from app.core.logging_config import setup_logging, get_logger
from app.core.cache import cache_manager
from app.database.engine import db_manager
from app.database.models import Base
from app.middlewares.logging import LoggingMiddleware
from app.middlewares.database import DatabaseSessionMiddleware
from app.handlers import start, admin
from app.services.parser import ParserService
from app.services.notification import NotificationService
from app.services.chat_monitor import ChatMonitorService
from app.services.userbot import UserbotService
from app.handlers import userbot_handler

logger = get_logger("main")

# Глобальный сервис мониторинга
chat_monitor = None
userbot = None


async def on_startup(bot: Bot):
    """Действия при запуске бота."""
    global chat_monitor, userbot
    
    logger.info("Бот запускается | Bot: @{username}", username=(await bot.get_me()).username)
    
    # Инициализация БД
    await db_manager.init_db()
    
    # Создаём таблицы (в продакшене используем alembic)
    async with db_manager.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("БД инициализирована")
    
    # Инициализация L2 Cache
    await cache_manager.init_l2()
    
    # Инициализация Userbot (Pyrogram)
    userbot = UserbotService(list(settings.get_admin_ids()))
    
    if settings.api_id and settings.api_hash:
        userbot_success = await userbot.start()
        if userbot_success:
            logger.info("✅ Userbot запущен — реальный парсинг чатов активен!")
            # Отключаем старый мониторинг (теперь userbot обрабатывает)
            chat_monitor = None
        else:
            logger.warning("⚠️ Userbot не авторизован. Запуск fallback мониторинга.")
            chat_monitor = ChatMonitorService(bot, list(settings.get_admin_ids()))
            async with db_manager.get_session() as session:
                await chat_monitor.load_last_message_ids(session)
            asyncio.create_task(chat_monitor.start_monitoring())
    else:
        logger.warning("⚠️ API ID/Hash не настроены. Userbot отключен.")
        chat_monitor = ChatMonitorService(bot, list(settings.get_admin_ids()))
        async with db_manager.get_session() as session:
            await chat_monitor.load_last_message_ids(session)
        asyncio.create_task(chat_monitor.start_monitoring())


async def on_shutdown(bot: Bot):
    """Действия при остановке бота."""
    global chat_monitor, userbot
    
    logger.info("Бот останавливается")
    
    # Останавливаем userbot
    if userbot:
        await userbot.stop()
    
    # Останавливаем мониторинг
    if chat_monitor:
        chat_monitor.stop_monitoring()
    
    await cache_manager.close()
    await db_manager.close_db()
    await bot.session.close()
    
    logger.info("Бот остановлен")


async def main():
    """Главная функция."""
    setup_logging()
    logger.info("=" * 50)
    logger.info("Telegram Chat Parser Bot запускается")
    logger.info("=" * 50)
    
    # Создаём директорию для данных
    Path("data").mkdir(exist_ok=True)
    Path("logs").mkdir(exist_ok=True)
    
    # Bot
    session = AiohttpSession()
    if settings.proxy_url:
        session.proxy = settings.proxy_url
        logger.info("Прокси настроен | URL: {url}", url=settings.proxy_url)
    
    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        session=session
    )
    
    # FSM Storage (Redis)
    try:
        redis = RedisStorage.from_url(settings.redis_url)
        logger.info("Redis FSM Storage подключен")
    except Exception as e:
        logger.warning("Redis не доступен, используем MemoryStorage: {error}", error=str(e))
        from aiogram.fsm.storage.memory import MemoryStorage
        redis = MemoryStorage()
    
    # Dispatcher
    dp = Dispatcher(storage=redis)
    
    # Middleware
    dp.message.middleware(LoggingMiddleware())
    dp.message.middleware(DatabaseSessionMiddleware())
    dp.callback_query.middleware(LoggingMiddleware())
    dp.callback_query.middleware(DatabaseSessionMiddleware())
    
    # Роутеры
    dp.include_router(start.router)
    dp.include_router(admin.router)
    dp.include_router(userbot_handler.router)
    
    # Handlers
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    
    # Запускаем
    logger.info("Бот готов к работе. Long Polling запущен.")
    
    try:
        await dp.start_polling(bot)
    except KeyboardInterrupt:
        logger.info("Получен сигнал остановки")
    except Exception as e:
        logger.critical("Критическая ошибка: {error}", error=str(e))
        raise
    finally:
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем")
    except Exception as e:
        logger.critical("Бот упал с ошибкой: {error}", error=str(e))
