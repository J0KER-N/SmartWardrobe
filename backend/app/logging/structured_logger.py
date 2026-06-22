"""
结构化日志模块

提供三个核心能力：
1. StructuredFormatter  —— 将日志格式化为 JSON 输出
2. get_structured_logger —— 创建附带任务上下文的 logger
3. AICallContext         —— 上下文管理器，自动记录 AI 调用的开始/结束/耗时/状态

───────────────────────── 日志字段说明 ─────────────────────────
必填字段（每条日志都会带）：
    timestamp    时间戳
    level        日志级别 (DEBUG/INFO/WARNING/ERROR)
    logger       模块名称
    message      日志消息
    task_id      任务ID（追踪一次完整请求）

AI调用相关字段（成功/失败时自动填充）：
    service      调用的 AI 服务名 (baichuan/huggingface/leffa/modelscope)
    model        使用的模型名
    status       调用结果 (success/error/timeout)
    latency_ms   调用耗时（毫秒）
    error_code   错误码（失败时）
    retry_count  重试次数

可选扩展字段：
    prompt_version   提示词版本号
    target_garment   目标衣物ID
    mask_used        是否使用了 mask 模式
───────────────────────────────────────────────────────────────
"""

import json
import logging
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Dict, Optional

# ============================================================================
# 第一部分：JSON 格式化器（StructuredFormatter）
# ============================================================================
#
# Python 日志系统中，Formatter 负责把一条日志记录格式化成最终输出的字符串。
# logging.Formatter 是内置基类，我们继承它并重写 format() 方法，
# 让它输出 JSON 而不是普通文本。
#
# 工作原理：
#   handler（输出到哪里）→ formatter（长什么样）→ logger（谁在写）
#
# 一个 logger 可以配多个 handler：
#   logger → StreamHandler（终端输出，用 JSON 格式）
#         → FileHandler（文件输出，用 JSON 格式）


class StructuredFormatter(logging.Formatter):
    """
    JSON 格式的日志格式化器。

    每个日志事件包含以下固定字段：
        timestamp, level, logger, message, task_id

    使用方式：
        handler = logging.StreamHandler()
        handler.setFormatter(StructuredFormatter())
        logger.addHandler(handler)
    """

    def format(self, record: logging.LogRecord) -> str:
        """
        核心方法：把一条日志记录 LogRecord 转成 JSON 字符串。

        record 参数是 Python 日志系统自动传入的，包含：
            - record.created    创建时间（秒级时间戳）
            - record.levelname  日志级别名称，如 "INFO"
            - record.name       logger 名称，如 "app.services.ai_clients"
            - record.getMessage()  日志消息文本
            - record.__dict__   所有通过 extra= 传入的额外字段
        """
        # 1. 构建基础字段字典
        log_entry: Dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(
                record.created, tz=timezone.utc
            ).isoformat(),                              # ISO 8601 格式，如 "2026-05-25T11:00:00+00:00"
            "level": record.levelname,                  # INFO / ERROR / WARNING
            "logger": record.name,                      # 例如 "app.services.ai_clients"
            "message": record.getMessage(),             # 日志内容
            "task_id": getattr(record, "task_id", None),# 从 extra= 中获取 task_id
        }

        # 2. 把 extra= 传入的扩展字段追加到日志中
        #    遍历 record.__dict__，过滤掉 Python 内置属性
        _SKIP_KEYS = {
            "args", "asctime", "created", "exc_info", "exc_text",
            "filename", "funcName", "levelname", "levelno",
            "lineno", "module", "msecs", "msg", "name",
            "pathname", "process", "processName", "relativeCreated",
            "stack_info", "thread", "threadName", "taskName",
            # 已在上方显式处理的字段
            "task_id",
        }

        for key, value in record.__dict__.items():
            if key not in _SKIP_KEYS and not key.startswith("_"):
                # 跳过已经是基础字段的（避免重复）
                if key not in log_entry:
                    log_entry[key] = value

        # 3. 转成单行 JSON（方便日志聚合工具按行解析）
        #    ensure_ascii=False  → 中文不转义
        #    default=str         → 遇到不可序列化的值转成字符串，避免崩溃
        return json.dumps(log_entry, ensure_ascii=False, default=str)


# ============================================================================
# 第二部分：Logger 工厂函数（get_structured_logger）
# ============================================================================
#
# 为什么不用 logging.getLogger() 直接创建？
#   因为我们需要一个地方统一配置 JSON formatter。
#   这个函数返回的 logger，默认就带上 JSON 格式的 handler。
#
# 使用方式：
#   logger = get_structured_logger(__name__)
#   logger.info("AI调用完成", extra={"service": "baichuan", "latency_ms": 1200})


# 已配置过的 logger 缓存，避免重复添加 handler
_structured_loggers: Dict[str, logging.Logger] = {}


def get_structured_logger(name: str, to_file: Optional[str] = None) -> logging.Logger:
    """
    获取一个结构化日志记录器。

    参数：
        name:    logger 名称，通常用 __name__（模块自动变量，值为模块路径字符串）
        to_file: 可选，如果指定则同时输出到该文件路径

    返回：
        配置好 JSON formatter 的 logging.Logger 实例

    示例：
        logger = get_structured_logger(__name__)
        logger.info(
            "调用百川API",
            extra={"service": "baichuan", "model": "Baichuan4-Air"}
        )
    """
    # 如果已经创建过同名的，直接返回缓存
    if name in _structured_loggers:
        return _structured_loggers[name]

    logger = logging.getLogger(name)

    # 避免通过 logging.basicConfig 的根 logger 重复输出
    logger.propagate = False

    # 创建 JSON 格式化器
    json_formatter = StructuredFormatter()

    # 添加控制台输出 handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(json_formatter)
    logger.addHandler(console_handler)

    # 可选：同时输出到文件
    if to_file:
        file_handler = logging.FileHandler(to_file, encoding="utf-8")
        file_handler.setFormatter(json_formatter)
        logger.addHandler(file_handler)

    # 设置日志级别（默认 INFO，可通过 logging 全局配置覆盖）
    logger.setLevel(logging.INFO)

    _structured_loggers[name] = logger
    return logger


# ============================================================================
# 第三部分：AI 调用上下文管理器（AICallContext）
# ============================================================================
#
# 上下文管理器（Context Manager）是 Python 的一个语法特性，
# 用 with 语句包裹一段代码，自动处理"进入"和"退出"时的逻辑。
#
# 基本语法：
#   with A() as x:
#       # 做点什么
#   # 自动执行清理
#
# 常见的 with open("file.txt") as f: 也是上下文管理器。
#
# AICallContext 的作用：
#   - 进入时：记录 "开始调用" 日志 + 开始计时
#   - 退出时：计算耗时，记录 "调用成功" 或 "调用失败" 日志
#   - 如果 with 块内抛异常，自动记录错误码和错误信息


class AICallContext:
    """
    AI 调用的上下文管理器，自动记录生命周期日志。

    使用方式：

        logger = get_structured_logger(__name__)

        # 写法1：自动模式（成功/失败都自动记录）
        with AICallContext(
            logger, task_id="abc123", service="baichuan", model="Baichuan4-Air"
        ) as ctx:
            result = call_baichuan_api()
            # 成功 → 退出时自动记录 status="success"

        # 写法2：手动标记（用于中间状态）
        with AICallContext(
            logger, task_id="abc123", service="baichuan", model="Baichuan4-Air"
        ) as ctx:
            try:
                result = call_baichuan_api()
                ctx.set_status("success")
            except Exception as e:
                ctx.set_status("error", error_code="A001", error_msg=str(e))
                raise

        # 写法3：带扩展字段
        with AICallContext(
            logger, task_id="abc123", service="leffa", model="viton_hd",
            extras={"prompt_version": "v2", "mask_used": True, "target_garment": "g_001"}
        ):
            result = generate_tryon()
    """

    def __init__(
        self,
        logger: logging.Logger,
        task_id: Optional[str] = None,
        service: str = "unknown",
        model: str = "unknown",
        extras: Optional[Dict[str, Any]] = None,
    ):
        """
        参数：
            logger:   结构化 logger（通过 get_structured_logger 创建）
            task_id:  任务ID，不传则自动生成 UUID
            service:  AI 服务名，如 "baichuan", "huggingface", "modelscope"
            model:    模型名，如 "Baichuan4-Air", "viton_hd"
            extras:   额外字段字典，如 {"prompt_version": "v2"}
        """
        self.logger = logger
        self.task_id = task_id or str(uuid.uuid4())[:8]  # 自动生成短ID
        self.service = service
        self.model = model
        self.extras = extras or {}

        # 运行时状态，在 __enter__ 和 __exit__ 中填充
        self.start_time: float = 0.0
        self._status: str = "success"       # 默认为 success，出错时覆盖
        self._error_code: Optional[str] = None
        self._error_msg: Optional[str] = None
        self._retry_count: int = 0

    # ── __enter__：进入 with 块时自动调用 ──
    def __enter__(self) -> "AICallContext":
        """记录开始日志，开始计时"""
        self.start_time = time.perf_counter()   # 高精度计时器

        # 构建 extra 字典（所有字段都通过 extra= 传入 logger）
        extra = self._build_extra(status="started")

        self.logger.info(
            f"AI调用开始 | service={self.service} model={self.model}",
            extra=extra,
        )
        return self   # 返回自身，让 with...as ctx 的 ctx 指向它

    # ── __exit__：退出 with 块时自动调用（无论正常/异常） ──
    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        参数解释（Python 自动传入）：
            exc_type: 异常类型，无异常时为 None（如 TimeoutError）
            exc_val:  异常实例，无异常时为 None
            exc_tb:   异常回溯，无异常时为 None
        """
        # 1. 计算耗时
        latency_ms = round((time.perf_counter() - self.start_time) * 1000, 2)

        # 2. 判断状态
        if exc_type is not None:
            # with 块内发生了异常
            self._status = "error"

            # 如果还没有设置 error_code，从异常类型自动推断
            if self._error_code is None:
                self._error_code = self._infer_error_code(exc_val)

            if self._error_msg is None:
                self._error_msg = str(exc_val)

        # 3. 构建 extra 并输出结束日志
        extra = self._build_extra(
            status=self._status,
            latency_ms=latency_ms,
            error_code=self._error_code,
            error_msg=self._error_msg,
        )

        if self._status == "error":
            self.logger.error(
                f"AI调用失败 | service={self.service} model={self.model} "
                f"latency={latency_ms}ms error={self._error_code}",
                extra=extra,
                exc_info=(exc_type, exc_val, exc_tb) if exc_type else False,
            )
        else:
            self.logger.info(
                f"AI调用完成 | service={self.service} model={self.model} "
                f"latency={latency_ms}ms status={self._status}",
                extra=extra,
            )

        # 返回 False，让异常继续向上传播（不吞掉异常）
        return False

    # ── 手动设置状态的方法 ──
    def set_status(
        self,
        status: str,
        error_code: Optional[str] = None,
        error_msg: Optional[str] = None,
    ):
        """手动更新调用状态（用于带 try/except 的场景）"""
        self._status = status
        if error_code:
            self._error_code = error_code
        if error_msg:
            self._error_msg = error_msg

    def set_retry_count(self, count: int):
        """设置重试次数"""
        self._retry_count = count

    # ── 辅助方法 ──
    def _build_extra(self, status: str = "started", **kwargs) -> Dict[str, Any]:
        """构建传给 logger 的 extra 字典"""
        extra = {
            "task_id": self.task_id,
            "service": self.service,
            "model": self.model,
            "status": status,
            "retry_count": self._retry_count,
        }
        # 合并扩展字段（如 prompt_version, mask_used 等）
        extra.update(self.extras)
        # 合并传入的关键字参数（如 latency_ms, error_code 等）
        extra.update(kwargs)
        return extra

    @staticmethod
    def _infer_error_code(exc_val) -> Optional[str]:
        """从异常对象自动推断错误码"""
        try:
            from ..exceptions import ErrorCode
        except ImportError:
            return None

        # 按异常类型映射
        mapping = {
            "AITimeoutError": ErrorCode.ERR_AI_TIMEOUT,
            "AIRateLimitError": ErrorCode.ERR_AI_RATE_LIMITED,
            "AIUnavailableError": ErrorCode.ERR_AI_UNAVAILABLE,
            "AIConnectionFailedError": ErrorCode.ERR_AI_CONNECTION_FAILED,
            "AINotConfiguredError": ErrorCode.ERR_AI_NOT_CONFIGURED,
            "AIInvalidResponseError": ErrorCode.ERR_AI_INVALID_RESPONSE,
            "AIGatewayError": ErrorCode.ERR_AI_UNAVAILABLE,
        }
        class_name = type(exc_val).__name__
        matched = mapping.get(class_name)
        return matched.value if matched else "A_UNKNOWN"


# ============================================================================
# 第四部分：全局初始化函数
# ============================================================================

def init_structured_logging(log_level: int = logging.INFO):
    """
    初始化全局结构化日志配置。

    这个函数用于在 main.py 的 setup_logging 中调用，
    为根 logger 替换为 JSON 格式化器，使所有模块都输出结构化日志。

    参数：
        log_level: 日志级别，如 logging.INFO
    """
    # 获取根 logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # 清除已有 handlers，替换为 JSON 格式化器
    json_formatter = StructuredFormatter()

    for handler in root_logger.handlers:
        handler.setFormatter(json_formatter)
