from sqlalchemy import Column, Integer, String, Text, DateTime, BigInteger, Boolean, ForeignKey
from sqlalchemy.sql import func
from app.database.engine import Base
from app.core.logging_config import get_logger

logger = get_logger("database.models")


class MonitoredChat(Base):
    """Модель отслеживаемого чата."""
    __tablename__ = "monitored_chats"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    chat_id = Column(BigInteger, unique=True, nullable=False, index=True)
    chat_title = Column(String(255), nullable=True)
    chat_username = Column(String(255), nullable=True, unique=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<MonitoredChat(id={self.id}, chat_id={self.chat_id}, title='{self.chat_title}')>"


class Keyword(Base):
    """Модель ключевого слова для фильтрации."""
    __tablename__ = "keywords"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    word = Column(String(255), unique=True, nullable=False, index=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    def __repr__(self):
        return f"<Keyword(id={self.id}, word='{self.word}')>"


class ParsedMessage(Base):
    """Модель распарсенного сообщения."""
    __tablename__ = "parsed_messages"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    message_id = Column(BigInteger, nullable=False, index=True)
    chat_id = Column(BigInteger, nullable=False, index=True)
    chat_title = Column(String(255), nullable=True)
    user_id = Column(BigInteger, nullable=True, index=True)
    username = Column(String(255), nullable=True)
    text = Column(Text, nullable=True)
    matched_keywords = Column(String(500), nullable=True)
    message_link = Column(String(500), nullable=True)
    parsed_at = Column(DateTime(timezone=True), server_default=func.now())
    is_sent = Column(Boolean, default=False, nullable=False)
    
    def __repr__(self):
        return f"<ParsedMessage(id={self.id}, chat_id={self.chat_id}, user_id={self.user_id})>"


logger.info("Модели БД загружены: MonitoredChat, Keyword, ParsedMessage")
