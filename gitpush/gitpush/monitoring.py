#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
监控模块
- 封装 Sentry 监控上报
- 提供简单的指标收集接口
"""

import os
import time
from typing import Dict, Optional, Any

# 初始化 metrics 存储
_metrics: Dict[str, Dict[str, Any]] = {}


class SentryConfig:
    """Sentry 配置类"""
    def __init__(self):
        self.dsn = os.environ.get("SENTRY_DSN", "")
        self.environment = os.environ.get("SENTRY_ENVIRONMENT", "production")
        self.enabled = bool(self.dsn)


class Monitoring:
    """监控类，封装 Sentry 和指标收集"""
    
    def __init__(self):
        self.sentry_config = SentryConfig()
        self.sentry_init = False
        self._initialize_sentry()
    
    def _initialize_sentry(self):
        """初始化 Sentry"""
        if self.sentry_config.enabled and not self.sentry_init:
            try:
                import sentry_sdk
                from sentry_sdk.integrations.python import PythonIntegration
                from gitpush.logger import log
                
                sentry_sdk.init(
                    dsn=self.sentry_config.dsn,
                    environment=self.sentry_config.environment,
                    integrations=[
                        PythonIntegration(
                            # 收集局部变量
                            propagate_traces=True,
                            # 收集上下文
                            attach_stacktrace=True,
                        ),
                    ],
                    # 采样率，生产环境可以降低
                    traces_sample_rate=1.0,
                )
                self.sentry_init = True
                log(f"Sentry 初始化成功，环境: {self.sentry_config.environment}")
            except ImportError:
                log("Sentry SDK 未安装，跳过初始化")
            except Exception as e:
                log(f"Sentry 初始化失败: {e}")
    
    def capture_exception(self, exception: Exception, context: Optional[Dict[str, Any]] = None):
        """捕获异常并上报到 Sentry"""
        if self.sentry_init:
            try:
                import sentry_sdk
                with sentry_sdk.push_scope() as scope:
                    if context:
                        for key, value in context.items():
                            scope.set_extra(key, value)
                    sentry_sdk.capture_exception(exception)
            except Exception as e:
                log(f"Sentry 上报异常失败: {e}")
    
    def capture_message(self, message: str, level: str = "info", context: Optional[Dict[str, Any]] = None):
        """捕获消息并上报到 Sentry"""
        if self.sentry_init:
            try:
                import sentry_sdk
                with sentry_sdk.push_scope() as scope:
                    if context:
                        for key, value in context.items():
                            scope.set_extra(key, value)
                    sentry_sdk.capture_message(message, level=level)
            except Exception as e:
                log(f"Sentry 上报消息失败: {e}")


# 创建全局监控实例
monitoring = Monitoring()


def record_metric(name: str, value: float, tags: Optional[Dict[str, str]] = None):
    """记录指标
    
    Args:
        name: 指标名称
        value: 指标值
        tags: 标签字典
    """
    global _metrics
    
    timestamp = time.monotonic()
    
    if name not in _metrics:
        _metrics[name] = {
            "count": 0,
            "sum": 0.0,
            "min": float("inf"),
            "max": float("-inf"),
            "last_value": 0.0,
            "last_timestamp": timestamp,
            "tags": tags or {},
        }
    
    metric = _metrics[name]
    metric["count"] += 1
    metric["sum"] += value
    metric["min"] = min(metric["min"], value)
    metric["max"] = max(metric["max"], value)
    metric["last_value"] = value
    metric["last_timestamp"] = timestamp
    
    # 更新标签
    if tags:
        metric["tags"].update(tags)


def export_metrics():
    """导出当前所有指标，便于测试断言
    
    Returns:
        Dict[str, Dict[str, Any]]: 指标字典
    """
    global _metrics
    return _metrics.copy()


def capture_exception(exception: Exception, context: Optional[Dict[str, Any]] = None):
    """捕获异常的便捷函数"""
    monitoring.capture_exception(exception, context)


def capture_message(message: str, level: str = "info", context: Optional[Dict[str, Any]] = None):
    """捕获消息的便捷函数"""
    monitoring.capture_message(message, level, context)
