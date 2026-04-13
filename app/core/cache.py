import time
import json
from typing import Any, Optional
from collections import OrderedDict
import redis.asyncio as redis
from app.config import settings
from app.core.logging_config import get_logger

logger = get_logger("core.cache")


class L1Cache:
    """L1 Cache - in-memory (RAM) с LRU стратегией."""
    
    def __init__(self, max_size: int = 1000):
        self.cache: OrderedDict = OrderedDict()
        self.max_size = max_size
        self.ttl_map: dict = {}
        logger.info("L1 Cache инициализирован | Max size: {size}", size=max_size)
    
    def get(self, key: str) -> Optional[Any]:
        """Получить значение из кеша."""
        if key in self.cache:
            # Проверяем TTL
            if key in self.ttl_map and time.time() > self.ttl_map[key]:
                self.delete(key)
                logger.debug("L1 Cache miss (TTL expired) | Key: {key}", key=key)
                return None
            
            self.cache.move_to_end(key)
            logger.debug("L1 Cache hit | Key: {key}", key=key)
            return self.cache[key]
        
        logger.debug("L1 Cache miss | Key: {key}", key=key)
        return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Установить значение в кеш."""
        if key in self.cache:
            self.cache.move_to_end(key)
        else:
            if len(self.cache) >= self.max_size:
                self.cache.popitem(last=False)
        
        self.cache[key] = value
        
        if ttl:
            self.ttl_map[key] = time.time() + ttl
        
        logger.debug("L1 Cache set | Key: {key} | TTL: {ttl}", key=key, ttl=ttl)
    
    def delete(self, key: str) -> bool:
        """Удалить значение из кеша."""
        if key in self.cache:
            del self.cache[key]
            if key in self.ttl_map:
                del self.ttl_map[key]
            logger.debug("L1 Cache delete | Key: {key}", key=key)
            return True
        return False
    
    def clear(self) -> None:
        """Очистить весь кеш."""
        self.cache.clear()
        self.ttl_map.clear()
        logger.info("L1 Cache очищен")


class CacheManager:
    """Менеджер кеширования L1 + L2."""
    
    def __init__(self):
        self.l1_cache = L1Cache()
        self.l2_redis: Optional[redis.Redis] = None
        logger.info("Cache Manager инициализирован (L1 + L2)")
    
    async def init_l2(self):
        """Инициализация L2 cache (Redis)."""
        try:
            self.l2_redis = redis.from_url(
                settings.redis_url,
                decode_responses=True,
                encoding="utf-8"
            )
            await self.l2_redis.ping()
            logger.info("L2 Cache (Redis) подключен | URL: {url}", url=settings.redis_url)
        except Exception as e:
            logger.warning("L2 Cache (Redis) не доступен: {error}. Работаем только с L1.", error=str(e))
            self.l2_redis = None
    
    async def get(self, key: str) -> Optional[Any]:
        """Получить значение (L1 → L2)."""
        # L1 Cache
        value = self.l1_cache.get(key)
        if value is not None:
            return value
        
        # L2 Cache - десериализуем из JSON
        if self.l2_redis:
            try:
                value = await self.l2_redis.get(key)
                if value is not None:
                    # Десериализуем JSON
                    try:
                        value = json.loads(value)
                    except json.JSONDecodeError:
                        pass  # Если не JSON — возвращаем как есть
                    
                    # Сохраняем в L1
                    self.l1_cache.set(key, value, settings.cache_ttl_l1)
                    logger.debug("L2 Cache hit | Key: {key}", key=key)
                    return value
            except Exception as e:
                logger.error("L2 Cache get error: {error}", error=str(e))
        
        logger.debug("Cache miss (L1+L2) | Key: {key}", key=key)
        return None
    
    async def set(self, key: str, value: Any, ttl_l1: Optional[int] = None, ttl_l2: Optional[int] = None) -> None:
        """Установить значение (L1 + L2)."""
        ttl_l1 = ttl_l1 or settings.cache_ttl_l1
        ttl_l2 = ttl_l2 or settings.cache_ttl_l2
        
        # L1 Cache
        self.l1_cache.set(key, value, ttl_l1)
        
        # L2 Cache - сериализуем в JSON
        if self.l2_redis:
            try:
                serialized = json.dumps(value, ensure_ascii=False, default=str)
                await self.l2_redis.set(key, serialized, ex=ttl_l2)
                logger.debug("L2 Cache set | Key: {key} | TTL: {ttl}", key=key, ttl=ttl_l2)
            except Exception as e:
                logger.error("L2 Cache set error: {error}", error=str(e))
    
    async def delete(self, key: str) -> None:
        """Удалить значение (L1 + L2)."""
        self.l1_cache.delete(key)
        
        if self.l2_redis:
            try:
                await self.l2_redis.delete(key)
            except Exception as e:
                logger.error("L2 Cache delete error: {error}", error=str(e))
    
    async def close(self):
        """Закрытие соединений."""
        if self.l2_redis:
            await self.l2_redis.close()
            logger.info("L2 Cache (Redis) отключен")


cache_manager = CacheManager()
