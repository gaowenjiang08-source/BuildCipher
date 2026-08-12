"""Unit tests for Redis client."""

import pytest
from cipher_genius.utils.redis_client import RedisClient


@pytest.fixture
def redis_client():
    """Create Redis client for testing."""
    client = RedisClient()
    yield client
    client.close()


def test_redis_set_get(redis_client):
    """Test basic set/get operations."""
    if not redis_client.is_available():
        pytest.skip("Redis not available")

    key = "test:key"
    value = {"data": "test_value", "count": 42}

    # Set value
    assert redis_client.set(key, value, ttl=60)

    # Get value
    retrieved = redis_client.get(key)
    assert retrieved == value

    # Cleanup
    redis_client.delete(key)


def test_redis_json_operations(redis_client):
    """Test JSON-specific operations."""
    if not redis_client.is_available():
        pytest.skip("Redis not available")

    key = "test:json"
    value = {"name": "AES-GCM", "key_size": 256}

    # Set JSON
    assert redis_client.set_json(key, value, ttl=60)

    # Get JSON
    retrieved = redis_client.get_json(key)
    assert retrieved == value

    # Cleanup
    redis_client.delete(key)


def test_redis_expiration(redis_client):
    """Test key expiration."""
    if not redis_client.is_available():
        pytest.skip("Redis not available")

    key = "test:expire"
    value = "test"

    redis_client.set(key, value, ttl=1)
    assert redis_client.exists(key)

    # Wait for expiration
    import time
    time.sleep(2)

    assert not redis_client.exists(key)


def test_redis_disabled():
    """Test behavior when Redis is disabled."""
    from cipher_genius.utils.config import get_settings
    settings = get_settings()

    # Temporarily disable Redis
    original = settings.redis_enabled
    settings.redis_enabled = False

    client = RedisClient()
    assert not client.is_available()
    assert client.get("any_key") is None
    assert not client.set("any_key", "value")

    # Restore
    settings.redis_enabled = original
