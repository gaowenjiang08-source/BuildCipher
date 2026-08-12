"""
速率限制器
Rate limiting for API calls and user requests
"""

import time
from collections import deque
from threading import Lock
from typing import Optional


class RateLimiter:
    """
    简单的滑动窗口速率限制器
    Token bucket rate limiter implementation
    """

    def __init__(self, max_requests: int = 30, window_seconds: int = 60):
        """
        初始化速率限制器

        Args:
            max_requests: 时间窗口内的最大请求数
            window_seconds: 时间窗口大小（秒）
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = deque()
        self.lock = Lock()

    def is_allowed(self, client_id: Optional[str] = None) -> bool:
        """
        检查是否允许请求

        Args:
            client_id: 客户端标识（可选，用于分客户端限流）

        Returns:
            是否允许请求
        """
        with self.lock:
            now = time.time()

            # 移除超出时间窗口的请求
            while self.requests and self.requests[0] < now - self.window_seconds:
                self.requests.popleft()

            # 检查是否超过限制
            if len(self.requests) >= self.max_requests:
                return False

            # 记录新请求
            self.requests.append(now)
            return True

    def wait_if_needed(self, client_id: Optional[str] = None, timeout: float = 30.0):
        """
        等待直到允许请求

        Args:
            client_id: 客户端标识
            timeout: 最大等待时间（秒）

        Raises:
            TimeoutError: 等待超时
        """
        start_time = time.time()

        while not self.is_allowed(client_id):
            if time.time() - start_time > timeout:
                raise TimeoutError(f"Rate limit timeout after {timeout}s")

            time.sleep(0.1)

    def get_remaining(self) -> int:
        """获取剩余可用请求数"""
        with self.lock:
            now = time.time()

            # 移除过期请求
            while self.requests and self.requests[0] < now - self.window_seconds:
                self.requests.popleft()

            return max(0, self.max_requests - len(self.requests))

    def reset(self):
        """重置限流器"""
        with self.lock:
            self.requests.clear()


# 全局速率限制器
_global_limiter = RateLimiter(max_requests=30, window_seconds=60)


def get_rate_limiter() -> RateLimiter:
    """获取全局速率限制器"""
    return _global_limiter


def check_rate_limit() -> bool:
    """检查是否在速率限制内"""
    return _global_limiter.is_allowed()
