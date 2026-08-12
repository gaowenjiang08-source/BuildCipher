"""LLM response caching system for improved stability and performance"""

import hashlib
import json
import time
from pathlib import Path
from typing import Optional, Any, Dict
from datetime import datetime, timedelta

from cipher_genius.utils.logger import get_logger

logger = get_logger(__name__)


class LLMCache:
    """
    Simple file-based cache for LLM responses.

    Features:
    - Hash-based key generation
    - TTL (Time-To-Live) support
    - JSON serialization
    - Automatic cleanup
    """

    def __init__(
        self,
        cache_dir: Optional[Path] = None,
        ttl_hours: int = 24,
        max_cache_size: int = 1000
    ):
        """
        Initialize LLM cache.

        Args:
            cache_dir: Directory for cache files (default: .cache/llm)
            ttl_hours: Time-to-live in hours (default: 24)
            max_cache_size: Maximum number of cache entries (default: 1000)
        """
        if cache_dir is None:
            # Default to .cache/llm in project root
            cache_dir = Path.cwd() / ".cache" / "llm"

        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.ttl = timedelta(hours=ttl_hours)
        self.max_cache_size = max_cache_size

        # Stats
        self.hits = 0
        self.misses = 0

        logger.info(f"LLM Cache initialized: {self.cache_dir}")

    def _generate_key(self, prompt: str, system_prompt: str, **kwargs) -> str:
        """
        Generate cache key from prompt and parameters.

        Args:
            prompt: User prompt
            system_prompt: System prompt
            **kwargs: Additional parameters (temperature, etc.)

        Returns:
            MD5 hash of the input
        """
        # Combine all inputs
        cache_input = {
            "prompt": prompt,
            "system_prompt": system_prompt,
            "kwargs": kwargs
        }

        # Serialize to JSON (sorted keys for consistency)
        json_str = json.dumps(cache_input, sort_keys=True)

        # Generate MD5 hash
        hash_obj = hashlib.md5(json_str.encode('utf-8'))
        return hash_obj.hexdigest()

    def _get_cache_path(self, key: str) -> Path:
        """Get cache file path for a key"""
        return self.cache_dir / f"{key}.json"

    def get(
        self,
        prompt: str,
        system_prompt: str,
        **kwargs
    ) -> Optional[Dict[str, Any]]:
        """
        Get cached response if available and not expired.

        Args:
            prompt: User prompt
            system_prompt: System prompt
            **kwargs: Additional parameters

        Returns:
            Cached response or None
        """
        key = self._generate_key(prompt, system_prompt, **kwargs)
        cache_path = self._get_cache_path(key)

        if not cache_path.exists():
            self.misses += 1
            logger.debug(f"Cache MISS: {key[:8]}...")
            return None

        try:
            # Read cache file
            with open(cache_path, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)

            # Check expiration
            cached_time = datetime.fromisoformat(cache_data['timestamp'])
            if datetime.now() - cached_time > self.ttl:
                logger.debug(f"Cache EXPIRED: {key[:8]}...")
                cache_path.unlink()  # Delete expired cache
                self.misses += 1
                return None

            # Cache hit!
            self.hits += 1
            logger.debug(f"Cache HIT: {key[:8]}... (age: {datetime.now() - cached_time})")
            return cache_data['response']

        except Exception as e:
            logger.warning(f"Error reading cache {key[:8]}: {e}")
            self.misses += 1
            return None

    def set(
        self,
        prompt: str,
        system_prompt: str,
        response: Dict[str, Any],
        **kwargs
    ) -> None:
        """
        Cache LLM response.

        Args:
            prompt: User prompt
            system_prompt: System prompt
            response: LLM response to cache
            **kwargs: Additional parameters
        """
        key = self._generate_key(prompt, system_prompt, **kwargs)
        cache_path = self._get_cache_path(key)

        cache_data = {
            'timestamp': datetime.now().isoformat(),
            'prompt': prompt[:100],  # Store truncated prompt for debugging
            'response': response
        }

        try:
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=2, ensure_ascii=False)

            logger.debug(f"Cache SET: {key[:8]}...")

            # Cleanup if cache is too large
            self._cleanup_if_needed()

        except Exception as e:
            logger.warning(f"Error writing cache {key[:8]}: {e}")

    def _cleanup_if_needed(self) -> None:
        """Remove oldest cache files if cache size exceeds limit"""
        cache_files = list(self.cache_dir.glob("*.json"))

        if len(cache_files) <= self.max_cache_size:
            return

        # Sort by modification time (oldest first)
        cache_files.sort(key=lambda p: p.stat().st_mtime)

        # Remove oldest files
        to_remove = len(cache_files) - self.max_cache_size
        for cache_file in cache_files[:to_remove]:
            cache_file.unlink()
            logger.debug(f"Removed old cache: {cache_file.name}")

    def clear(self) -> int:
        """
        Clear all cache files.

        Returns:
            Number of files deleted
        """
        cache_files = list(self.cache_dir.glob("*.json"))
        count = len(cache_files)

        for cache_file in cache_files:
            cache_file.unlink()

        logger.info(f"Cleared {count} cache files")
        return count

    def stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        cache_files = list(self.cache_dir.glob("*.json"))
        total_size = sum(f.stat().st_size for f in cache_files)

        hit_rate = (
            self.hits / (self.hits + self.misses) * 100
            if (self.hits + self.misses) > 0
            else 0
        )

        return {
            'hits': self.hits,
            'misses': self.misses,
            'hit_rate': f"{hit_rate:.1f}%",
            'total_entries': len(cache_files),
            'total_size_mb': total_size / 1024 / 1024,
            'cache_dir': str(self.cache_dir)
        }


# Global cache instance
_global_cache: Optional[LLMCache] = None


def get_cache(
    cache_dir: Optional[Path] = None,
    ttl_hours: int = 24,
    max_cache_size: int = 1000
) -> LLMCache:
    """
    Get or create global cache instance.

    Args:
        cache_dir: Cache directory
        ttl_hours: Time-to-live in hours
        max_cache_size: Maximum cache entries

    Returns:
        Global LLMCache instance
    """
    global _global_cache

    if _global_cache is None:
        _global_cache = LLMCache(
            cache_dir=cache_dir,
            ttl_hours=ttl_hours,
            max_cache_size=max_cache_size
        )

    return _global_cache
