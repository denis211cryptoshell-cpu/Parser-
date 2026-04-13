from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator
from typing import Set
from pathlib import Path
import os


# Очищаем системные переменные чтобы не конфликтовали с .env
for key in ["BOT_TOKEN", "REDIS_URL", "DATABASE_URL", "ADMIN_IDS", "LOG_LEVEL", "LOG_FILE", "PROXY_URL", "MONITORING_INTERVAL", "API_ID", "API_HASH", "USERBOT_SESSION"]:
    if key in os.environ:
        del os.environ[key]


class Settings(BaseSettings):
    """Настройки приложения из переменных окружения."""
    
    model_config = SettingsConfigDict(
        env_file=Path(__file__).parent.parent / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # Bot
    bot_token: str
    
    # Redis
    redis_url: str = "redis://localhost:6379/0"
    
    # Database
    database_url: str = "sqlite+aiosqlite:///./data/bot.db"
    
    # Admin IDs (через запятую)
    admin_ids: str = "123456789"
    
    # Logging
    log_level: str = "DEBUG"
    log_file: str = "logs/bot.log"
    
    # Parsing
    parsing_limit: int = 100
    cache_ttl_l1: int = 300  # 5 минут
    cache_ttl_l2: int = 600  # 10 минут
    
    # Proxy
    proxy_url: str = ""
    
    # Monitoring
    monitoring_interval: int = 10
    
    # Pyrogram Userbot (получить на my.telegram.org)
    api_id: int = 0
    api_hash: str = ""
    userbot_session: str = "userbot.session"
    
    @field_validator("admin_ids", mode="before")
    @classmethod
    def validate_admin_ids(cls, v) -> str:
        """Валидация admin_ids - должны быть числами через запятую."""
        ids = [id.strip() for id in v.split(",")]
        for id_str in ids:
            if not id_str.isdigit():
                raise ValueError(f"Admin ID должен быть числом, получено: {id_str}")
        return v
    
    def get_admin_ids(self) -> Set[int]:
        """Получить set admin ID."""
        return {int(id_str) for id_str in self.admin_ids.split(",")}


settings = Settings()
