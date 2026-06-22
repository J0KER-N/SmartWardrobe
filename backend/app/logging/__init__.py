"""
logging 包 — 结构化日志模块

对外暴露：
    - get_structured_logger()  创建结构化日志记录器
    - AICallContext             AI调用上下文管理器（自动记录耗时和状态）
    - StructuredFormatter      JSON 格式的日志输出格式化器
    - init_structured_logging() 初始化全局结构化日志配置
"""

from .structured_logger import (
    StructuredFormatter,
    AICallContext,
    get_structured_logger,
    init_structured_logging,
)

__all__ = [
    "StructuredFormatter",
    "AICallContext",
    "get_structured_logger",
    "init_structured_logging",
]
