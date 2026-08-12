"""
应用监控和指标收集
Performance monitoring and metrics collection
"""

import time
import functools
from typing import Callable, Any, Dict
from datetime import datetime
import json
from pathlib import Path


class MetricsCollector:
    """收集和记录应用性能指标"""

    def __init__(self):
        self.metrics: Dict[str, Any] = {
            "requests": {
                "total": 0,
                "successful": 0,
                "failed": 0,
            },
            "llm_calls": {
                "total": 0,
                "cache_hits": 0,
                "cache_misses": 0,
            },
            "schemes_generated": {
                "total": 0,
                "by_type": {},
            },
            "performance": {
                "parse_time": [],
                "generation_time": [],
                "validation_time": [],
                "code_generation_time": [],
            },
            "errors": [],
            "start_time": datetime.now().isoformat(),
        }

    def increment(self, metric_path: str, amount: int = 1):
        """增加计数器"""
        keys = metric_path.split('.')
        current = self.metrics

        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]

        final_key = keys[-1]
        if final_key not in current:
            current[final_key] = 0
        current[final_key] += amount

    def record_time(self, metric_path: str, duration: float):
        """记录执行时间"""
        keys = metric_path.split('.')
        current = self.metrics

        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]

        final_key = keys[-1]
        if final_key not in current:
            current[final_key] = []
        current[final_key].append(duration)

    def record_error(self, error: Exception, context: str = ""):
        """记录错误"""
        self.metrics["errors"].append({
            "type": type(error).__name__,
            "message": str(error),
            "context": context,
            "timestamp": datetime.now().isoformat(),
        })

    def get_summary(self) -> Dict[str, Any]:
        """获取指标摘要"""
        summary = {
            "uptime": str(datetime.now() - datetime.fromisoformat(self.metrics["start_time"])),
            "total_requests": self.metrics["requests"]["total"],
            "success_rate": (
                self.metrics["requests"]["successful"] / self.metrics["requests"]["total"] * 100
                if self.metrics["requests"]["total"] > 0
                else 0
            ),
            "cache_hit_rate": (
                self.metrics["llm_calls"]["cache_hits"] / self.metrics["llm_calls"]["total"] * 100
                if self.metrics["llm_calls"]["total"] > 0
                else 0
            ),
            "total_schemes_generated": self.metrics["schemes_generated"]["total"],
            "total_errors": len(self.metrics["errors"]),
        }

        # 计算平均时间
        for perf_key, times in self.metrics["performance"].items():
            if times:
                summary[f"avg_{perf_key}"] = sum(times) / len(times)

        return summary

    def save_to_file(self, filepath: str = "metrics.json"):
        """保存指标到文件"""
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, 'w') as f:
            json.dump(self.metrics, f, indent=2)

    def load_from_file(self, filepath: str = "metrics.json"):
        """从文件加载指标"""
        if Path(filepath).exists():
            with open(filepath, 'r') as f:
                self.metrics = json.load(f)


# 全局指标收集器
_metrics_collector = MetricsCollector()


def get_metrics_collector() -> MetricsCollector:
    """获取全局指标收集器"""
    return _metrics_collector


def monitor_performance(metric_name: str):
    """性能监控装饰器"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            collector = get_metrics_collector()
            start_time = time.time()

            try:
                result = func(*args, **kwargs)
                collector.increment("requests.successful")
                return result
            except Exception as e:
                collector.increment("requests.failed")
                collector.record_error(e, context=func.__name__)
                raise
            finally:
                duration = time.time() - start_time
                collector.record_time(f"performance.{metric_name}", duration)
                collector.increment("requests.total")

        return wrapper
    return decorator


def track_llm_call(cache_hit: bool = False):
    """追踪LLM调用"""
    collector = get_metrics_collector()
    collector.increment("llm_calls.total")

    if cache_hit:
        collector.increment("llm_calls.cache_hits")
    else:
        collector.increment("llm_calls.cache_misses")


def track_scheme_generation(scheme_type: str):
    """追踪方案生成"""
    collector = get_metrics_collector()
    collector.increment("schemes_generated.total")

    # 按类型统计
    type_path = f"schemes_generated.by_type.{scheme_type}"
    collector.increment(type_path)
