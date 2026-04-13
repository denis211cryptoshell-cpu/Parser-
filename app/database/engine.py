from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from app.config import settings
from app.core.logging_config import get_logger

logger = get_logger("database.engine")


class Base(DeclarativeBase):
    """Базовый класс для моделей."""
    pass


class DatabaseManager:
    """Менеджер подключения к БД."""
    
    def __init__(self):
        self.engine = None
        self.async_session = None
    
    async def init_db(self):
        """Инициализация подключения к БД."""
        logger.info("Инициализация БД | URL: {url}", url=settings.database_url)
        
        self.engine = create_async_engine(
            settings.database_url,
            echo=settings.log_level == "DEBUG",
            pool_pre_ping=True
        )
        
        self.async_session = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
        
        logger.info("БД инициализирована успешно")
    
    async def close_db(self):
        """Закрытие подключения к БД."""
        if self.engine:
            await self.engine.dispose()
            logger.info("Подключение к БД закрыто")
    
    def get_session(self) -> AsyncSession:
        """Получить сессию БД."""
        return self.async_session()


db_manager = DatabaseManager()
