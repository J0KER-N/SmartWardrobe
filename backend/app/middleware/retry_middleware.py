"""
重试中间件模块

提供可配置的 AI 调用重试机制：
- RetryDecision   — 判断是否应该重试、计算退避延迟
- retry_on_ai_failure — 装饰器，给函数加上自动重试能力
"""

import logging
import random
import time
from functools import wraps
from typing import Callable

from ..config import get_settings
from ..exceptions import AIContentValidationError, AIRateLimitError, InvalidInputError

# ── Logger ──
logger = logging.getLogger(__name__)


class RetryDecision:
    """
    重试决策器，负责两件事：
    1. should_retry() — 判断一个错误是否应该重试
    2. calculate_delay() — 计算下次重试前等多久（指数退避+随机抖动）
    """

    def __init__(self):
        # 使用全局配置单例，而不是每次新建 Settings()
        settings = get_settings()
        self.max_retries = settings.ai_max_retries
        self.base_delay = settings.ai_retry_base_delay
        self.max_delay = settings.ai_retry_max_delay
        self.backoff_multiplier = settings.ai_retry_backoff_multiplier
        self.jitter = settings.ai_retry_jitter

    def calculate_delay(self, attempt: int) -> float:
        """
        计算第 attempt 次重试的等待时间。

        公式：delay = base * multiplier^attempt，然后加随机抖动，最后不超过 max_delay。

        示例（base=1, multiplier=2, max=60）：
            第 1 次重试 → 1 × 2^0 = 1s  → 抖动后约 0~1s
            第 2 次重试 → 1 × 2^1 = 2s  → 抖动后约 0~2s
            第 3 次重试 → 1 × 2^2 = 4s  → 抖动后约 0~4s
        """
        delay = self.base_delay * (self.backoff_multiplier ** attempt)

        if self.jitter:
            # 抖动：在 0 到 delay 之间随机取一个值
            # 防止多个请求同时重试造成"惊群效应"
            delay = random.uniform(0, delay)

        return min(delay, self.max_delay)

    def should_retry(self, attempt: int, exception: Exception) -> bool:
        """
        判断是否应该重试。

        不重试的情况：
            - 已达到最大重试次数
            - 是不可恢复的错误（参数错误、限流等）
        """
        if attempt >= self.max_retries:
            return False
        if self._is_unrecoverable_error(exception):
            return False
        return True

    def _is_unrecoverable_error(self, exception: Exception) -> bool:
        """
        判断是否为不可恢复的错误（重试也没用，直接报错）。

        不可恢复的情况：
            - 参数错误 (HTTP 400)      → 改了也还是错的
            - 限流 (HTTP 429)          → 需要等更久，不是简单重试能解决的
        """
        # 1. 通过异常类型名称判断（兼容 exceptions.py 和 ai_clients.py 两套命名）
        exc_name = type(exception).__name__
        if any(keyword in exc_name for keyword in (
            "RateLimit", "InvalidRequest", "InvalidInput",
        )):
            return True

        # 2. 通过 HTTP 状态码判断（httpx 原生异常可能带有 status_code）
        status_code = getattr(exception, "status_code", None)
        if status_code in (400, 429):
            return True

        return False


def retry_on_ai_failure():
    """
    装饰器：给同步 AI 调用函数加上自动重试。

    使用方式：
        @retry_on_ai_failure()
        def call_baichuan_api(prompt):
            ...

    重试流程：
        1. 调用函数
        2. 如果成功 → 直接返回结果
        3. 如果失败 → RetryDecision 判断是否重试
            - 可重试：等退避延迟 → 重试
            - 不可重试：直接抛出异常
    """
    decision = RetryDecision()

    def decorator(func: Callable):
        @wraps(func)  # 保留原函数的名称和文档字符串
        def wrapper(*args, **kwargs):
            attempt = 0

            while True:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if decision.should_retry(attempt, e):
                        delay = decision.calculate_delay(attempt)

                        # ── Step 4-2：内容验证失败 → 下次调用启用 mask 模式 ──
                        mask_flag = False
                        if isinstance(e, AIContentValidationError):
                            kwargs["_second_pass_mask"] = True
                            mask_flag = True

                        logger.warning(
                            "AI调用失败，准备重试 | "
                            f"func={func.__name__} "
                            f"attempt={attempt + 1}/{decision.max_retries} "
                            f"delay={delay:.2f}s "
                            f"mask_used={mask_flag} "
                            f"error={type(e).__name__}: {e}"
                        )
                        time.sleep(delay)
                        attempt += 1
                    else:
                        if attempt >= decision.max_retries:
                            logger.error(
                                "AI调用失败，已达最大重试次数 | "
                                f"func={func.__name__} "
                                f"total_attempts={attempt} "
                                f"error={type(e).__name__}: {e}"
                            )
                        else:
                            logger.error(
                                "AI调用失败，不可恢复的错误（不重试） | "
                                f"func={func.__name__} "
                                f"error={type(e).__name__}: {e}"
                            )
                        raise

        return wrapper

    return decorator
