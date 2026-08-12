"""Redis client for caching and task queue management."""

from __future__ import annotations

import json
import pickle
from typing import Any, Optional
from datetime import timedelta

import redis
from redis.exceptions import RedisError

from cipher_genius.utils.config import get_settings
from cipher_genius.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()


class RedisClient:
    """Redis client wrapper for caching and queue operations."""

    def __init__(self) -> None:
        """Initialize Redis client."""
        self._client: Optional[redis.Redis] = None
        self._enabled = settings.redis_enabled

    @property
    def client(self) -> redis.Redis:
        """Get or create Redis client."""
        if not self._enabled:
            raise RuntimeError("Redis is disabled in settings")

        if self._client is None:
            self._client = redis.Redis(
                host=settings.redis_host,
                port=settings.redis_port,
                db=settings.redis_db,
                password=settings.redis_password or None,
                decode_responses=False,
                socket_connect_timeout=5,
                socket_timeout=5,
            )
            # Test connection
            try:
                self._client.ping()
                logger.info(f"Redis connected: {settings.redis_host}:{settings.redis_port}")
            except RedisError as exc:
                logger.error(f"Redis connection failed: {exc}")
                self._client = None
                raise

        return self._client

    def is_available(self) -> bool:
        """Check if Redis is available."""
        if not self._enabled:
            return False
        try:
            return self.client.ping()
        except Exception:
            return False

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        if not self._enabled:
            return None
        try:
            data = self.client.get(key)
            if data is None:
                return None
            return pickle.loads(data)
        except Exception as exc:
            logger.warning(f"Redis get failed for key {key}: {exc}")
            return None

    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
    ) -> bool:
        """Set value in cache with optional TTL (seconds)."""
        if not self._enabled:
            return False
        try:
            data = pickle.dumps(value)
            if ttl:
                return bool(self.client.setex(key, ttl, data))
            return bool(self.client.set(key, data))
        except Exception as exc:
            logger.warning(f"Redis set failed for key {key}: {exc}")
            return False

    def delete(self, key: str) -> bool:
        """Delete key from cache."""
        if not self._enabled:
            return False
        try:
            return bool(self.client.delete(key))
        except Exception as exc:
            logger.warning(f"Redis delete failed for key {key}: {exc}")
            return False

    def exists(self, key: str) -> bool:
        """Check if key exists."""
        if not self._enabled:
            return False
        try:
            return bool(self.client.exists(key))
        except Exception as exc:
            logger.warning(f"Redis exists check failed for key {key}: {exc}")
            return False

    def expire(self, key: str, ttl: int) -> bool:
        """Set expiration time for key (seconds)."""
        if not self._enabled:
            return False
        try:
            return bool(self.client.expire(key, ttl))
        except Exception as exc:
            logger.warning(f"Redis expire failed for key {key}: {exc}")
            return False

    def get_json(self, key: str) -> Optional[dict]:
        """Get JSON value from cache."""
        if not self._enabled:
            return None
        try:
            data = self.client.get(key)
            if data is None:
                return None
            return json.loads(data)
        except Exception as exc:
            logger.warning(f"Redis get_json failed for key {key}: {exc}")
            return None

    def set_json(
        self,
        key: str,
        value: dict,
        ttl: Optional[int] = None,
    ) -> bool:
        """Set JSON value in cache with optional TTL (seconds)."""
        if not self._enabled:
            return False
        try:
            data = json.dumps(value, ensure_ascii=False)
            if ttl:
                return bool(self.client.setex(key, ttl, data))
            return bool(self.client.set(key, data))
        except Exception as exc:
            logger.warning(f"Redis set_json failed for key {key}: {exc}")
            return False

    def close(self) -> None:
        """Close Redis connection."""
        if self._client:
            self._client.close()
            self._client = None


# Global Redis client instance
_redis_client: Optional[RedisClient] = None


def get_redis_client() -> RedisClient:
    """Get global Redis client instance."""
    global _redis_client
    if _redis_client is None:
        _redis_client = RedisClient()
    return _redis_client
