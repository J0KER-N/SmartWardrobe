"""
统一异常定义与错误响应模块

这个文件定义了整个项目的错误处理体系，分为三个层次：
1. 错误分类（ErrorCategory）—— 决定"谁来处理这个错误"
2. 错误码（ErrorCode）—— 决定"具体是什么问题"
3. 异常类 —— 在代码中抛出，FastAPI 自动转成 HTTP 响应返回给前端
"""

# ============================================================================
# 第一部分：导入依赖
# ============================================================================
# enum 是 Python 标准库，用来定义"一组固定的可选值"
# 比如一周七天、四种花色，这里用来定义错误类别和错误码
from enum import Enum

# FastAPI 的 HTTPException 是抛出 HTTP 错误的基类
# status 是 HTTP 状态码常量（如 200 OK, 404 Not Found）
from fastapi import HTTPException, status

# Optional 表示"这个值可以是某个类型，也可以是 None"
# 比如 Optional[str] 表示可以是字符串或者空
from typing import Optional

# Pydantic 的 BaseModel，用来定义数据结构（类似 TypeScript 的 interface）
from pydantic import BaseModel


# ============================================================================
# 第二部分：错误分类枚举（ErrorCategory）
# ============================================================================
# Enum 语法：class 类名(Enum): 成员名 = 值
# 使用时：ErrorCategory.BUSINESS → "BUSINESS"
#
# 三个分类的含义：
# - BUSINESS：   用户操作相关（输入错误、资源不存在、权限不足）
#                前端直接展示给用户，引导用户修正
# - AI_GATEWAY： 外部 AI API 问题（超时、限流、服务挂了）
#                中间件触发重试，前端显示降级提示
# - INFRA：      自己的基础设施问题（数据库、存储崩了）
#                记录日志 + 运维告警，前端显示通用错误
class ErrorCategory(str, Enum):
    BUSINESS = "BUSINESS"        # 业务逻辑错误
    AI_GATEWAY = "AI_GATEWAY"    # AI 网关/外部服务错误
    INFRA = "INFRA"              # 基础设施错误


# ============================================================================
# 第三部分：错误码枚举（ErrorCode）
# ============================================================================
# 每个错误码有两个属性：
#   - code: 错误码字符串（前端用来判断逻辑）
#   - category: 属于哪个分类
#
# 命名规范：ERR_<领域>_<具体问题>
# 例如 ERR_AI_TIMEOUT = "A001"  → AI 领域的超时问题
#
# 编码规则（方便一眼看出类别）：
#   - B 开头 = BUSINESS
#   - A 开头 = AI_GATEWAY
#   - I 开头 = INFRA
class ErrorCode(str, Enum):
    # ── BUSINESS 业务逻辑错误 ──
    ERR_RESOURCE_NOT_FOUND      = ("B001", ErrorCategory.BUSINESS)   # 资源不存在
    ERR_RESOURCE_ALREADY_EXISTS = ("B002", ErrorCategory.BUSINESS)   # 资源已存在
    ERR_INVALID_CREDENTIALS     = ("B003", ErrorCategory.BUSINESS)   # 凭证无效
    ERR_INVALID_INPUT           = ("B004", ErrorCategory.BUSINESS)   # 输入参数错误
    ERR_EMPTY_WARDROBE          = ("B005", ErrorCategory.BUSINESS)   # 衣橱为空
    ERR_PERMISSION_DENIED       = ("B006", ErrorCategory.BUSINESS)   # 权限不足

    # ── AI_GATEWAY AI 网关错误 ──
    ERR_AI_TIMEOUT              = ("A001", ErrorCategory.AI_GATEWAY)  # AI 服务超时
    ERR_AI_RATE_LIMITED         = ("A002", ErrorCategory.AI_GATEWAY)  # AI 服务限流
    ERR_AI_UNAVAILABLE          = ("A003", ErrorCategory.AI_GATEWAY)  # AI 服务不可用 (502/503/504)
    ERR_AI_CONNECTION_FAILED    = ("A004", ErrorCategory.AI_GATEWAY)  # 无法连接 AI 服务
    ERR_AI_NOT_CONFIGURED       = ("A005", ErrorCategory.AI_GATEWAY)  # AI 服务未配置
    ERR_AI_INVALID_RESPONSE     = ("A006", ErrorCategory.AI_GATEWAY)  # AI 返回格式异常

    # ── INFRA 基础设施错误 ──
    ERR_DATABASE_FAILURE        = ("I001", ErrorCategory.INFRA)        # 数据库操作失败
    ERR_STORAGE_FAILURE         = ("I002", ErrorCategory.INFRA)        # 文件/图片存储失败
    ERR_EXTERNAL_SERVICE        = ("I003", ErrorCategory.INFRA)        # 外部非AI服务失败

    # ── 以下两个方法是 Python Enum 的固定写法，用来把上面的元组拆开使用 ──
    #
    # __new__ 魔术方法：Python 创建枚举成员时自动调用
    # 这里我们告诉 Python：第一个值是 code，第二个值是 category
    def __new__(cls, code: str, category: ErrorCategory):
        obj = str.__new__(cls, code)          # 枚举成员本身的值 = code（如 "A001"）
        obj._value_ = code                    # 确保 value 属性也是 code
        obj.category = category               # 附加 category 属性
        return obj


# ============================================================================
# 第四部分：统一错误响应模型（ErrorResponse）
# ============================================================================
# Pydantic BaseModel：定义数据结构，自动校验类型
# 这个类规定了错误返回给前端时的 JSON 格式
#
# 前端收到的 JSON 示例：
# {
#     "success": false,
#     "error": {
#         "code": "A001",
#         "category": "AI_GATEWAY",
#         "message": "AI 服务请求超时"
#     }
# }
class ErrorResponse(BaseModel):
    success: bool = False
    error: dict   # 包含 code, category, message


# ============================================================================
# 第五部分：错误响应生成器（error_response 函数）
# ============================================================================
# 这个函数的作用：根据错误码和自定义消息，生成统一格式的响应字典
#
# 参数说明：
#   code: ErrorCode     → 错误码枚举成员，如 ErrorCode.ERR_AI_TIMEOUT
#   message: str = None → 自定义错误消息，不传则使用默认的友好提示
#   details: str = None → 可选的详细错误信息（调试用）
#
# 返回值：一个字典，可以直接传给 JSONResponse
def error_response(
    code: ErrorCode,
    message: Optional[str] = None,
    details: Optional[str] = None,
) -> dict:
    """
    生成统一格式的错误响应。

    使用方式：
        # 使用默认消息
        error_response(ErrorCode.ERR_AI_TIMEOUT)

        # 自定义消息
        error_response(ErrorCode.ERR_RESOURCE_NOT_FOUND, message="用户不存在")
    """
    # 如果没有传自定义消息，使用错误码对应的默认友好提示
    if message is None:
        message = _default_message(code)

    response = {
        "success": False,
        "error": {
            "code": code.value,              # 错误码字符串，如 "A001"
            "category": code.category.value, # 分类，如 "AI_GATEWAY"
            "message": message,              # 友好提示
        }
    }

    # 如果有详细调试信息，额外附加（生产环境不传）
    if details:
        response["error"]["details"] = details

    return response


# 错误码 → 默认友好提示的映射表
# 这里的 key 是 ErrorCode 枚举成员，value 是面向用户的提示文字
_DEFAULT_MESSAGES = {
    ErrorCode.ERR_RESOURCE_NOT_FOUND:      "请求的资源不存在",
    ErrorCode.ERR_RESOURCE_ALREADY_EXISTS: "该资源已存在，请勿重复操作",
    ErrorCode.ERR_INVALID_CREDENTIALS:     "用户名或密码错误",
    ErrorCode.ERR_INVALID_INPUT:           "输入参数有误，请检查后重试",
    ErrorCode.ERR_EMPTY_WARDROBE:          "衣橱为空，请先添加衣物",
    ErrorCode.ERR_PERMISSION_DENIED:       "您没有权限执行此操作",

    ErrorCode.ERR_AI_TIMEOUT:              "AI 服务响应超时，请稍后重试",
    ErrorCode.ERR_AI_RATE_LIMITED:         "AI 服务请求过于频繁，请稍后重试",
    ErrorCode.ERR_AI_UNAVAILABLE:          "AI 服务暂时不可用，请稍后重试",
    ErrorCode.ERR_AI_CONNECTION_FAILED:    "无法连接到 AI 服务，请检查网络后重试",
    ErrorCode.ERR_AI_NOT_CONFIGURED:       "AI 服务尚未配置，请联系管理员",
    ErrorCode.ERR_AI_INVALID_RESPONSE:     "AI 服务返回数据异常，请稍后重试",

    ErrorCode.ERR_DATABASE_FAILURE:        "系统数据服务异常，请稍后重试",
    ErrorCode.ERR_STORAGE_FAILURE:         "文件存储服务异常，请稍后重试",
    ErrorCode.ERR_EXTERNAL_SERVICE:        "外部服务调用失败，请稍后重试",
}


def _default_message(code: ErrorCode) -> str:
    """获取错误码对应的默认友好提示"""
    return _DEFAULT_MESSAGES.get(code, "服务器内部错误")


# ============================================================================
# 第六部分：异常类定义
# ============================================================================
# 每个异常类继承 HTTPException，这样 FastAPI 会自动转成 HTTP 响应
#
# 结构：
#   class XxxError(HTTPException):
#       def __init__(self, detail=None):
#           # 调用父类 HTTPException 的构造方法
#           # 传入 HTTP 状态码 和 错误描述
#           super().__init__(status_code=status.HTTP_XXX, detail=detail)
#
# 使用方式（在路由里）：
#   raise ResourceNotFoundError("用户不存在")
#   → 前端收到 HTTP 404，body 里有错误码和分类

# ── 业务异常（保留并增强原有类）──

class ResourceNotFoundError(HTTPException):
    """资源不存在异常 → 对应 ERR_RESOURCE_NOT_FOUND"""
    def __init__(self, detail: str = "资源不存在"):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)
        # 在 HTTP 响应头中附加错误码，方便日志/监控系统识别
        self.error_code = ErrorCode.ERR_RESOURCE_NOT_FOUND
        self.error_category = ErrorCategory.BUSINESS


class ResourceAlreadyExistsError(HTTPException):
    """资源已存在异常 → 对应 ERR_RESOURCE_ALREADY_EXISTS"""
    def __init__(self, detail: str = "资源已存在"):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)
        self.error_code = ErrorCode.ERR_RESOURCE_ALREADY_EXISTS
        self.error_category = ErrorCategory.BUSINESS


class InvalidCredentialsError(HTTPException):
    """无效凭证异常 → 对应 ERR_INVALID_CREDENTIALS"""
    def __init__(self, detail: str = "用户名或密码错误"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )
        self.error_code = ErrorCode.ERR_INVALID_CREDENTIALS
        self.error_category = ErrorCategory.BUSINESS


class InvalidInputError(HTTPException):
    """输入参数错误 → 对应 ERR_INVALID_INPUT"""
    def __init__(self, detail: str = "输入参数有误"):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)
        self.error_code = ErrorCode.ERR_INVALID_INPUT
        self.error_category = ErrorCategory.BUSINESS


class EmptyWardrobeError(HTTPException):
    """衣橱为空异常 → 对应 ERR_EMPTY_WARDROBE"""
    def __init__(self, detail: str = "衣橱为空"):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)
        self.error_code = ErrorCode.ERR_EMPTY_WARDROBE
        self.error_category = ErrorCategory.BUSINESS


# ── AI 网关异常（新增）──

class AIGatewayError(HTTPException):
    """AI 网关异常基类 → 所有 AI 相关错误的父类
    其他 AI 异常都继承它，方便统一捕获"""
    def __init__(
        self,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail: str = "AI 服务调用异常",
        error_code: ErrorCode = ErrorCode.ERR_AI_UNAVAILABLE,
    ):
        super().__init__(status_code=status_code, detail=detail)
        self.error_code = error_code
        self.error_category = ErrorCategory.AI_GATEWAY


class AITimeoutError(AIGatewayError):
    """AI 服务超时异常 → 对应 ERR_AI_TIMEOUT"""
    def __init__(self, detail: str = "AI 服务请求超时"):
        super().__init__(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=detail,
            error_code=ErrorCode.ERR_AI_TIMEOUT,
        )


class AIRateLimitError(AIGatewayError):
    """AI 服务限流异常 → 对应 ERR_AI_RATE_LIMITED"""
    def __init__(self, detail: str = "AI 服务请求过于频繁"):
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=detail,
            error_code=ErrorCode.ERR_AI_RATE_LIMITED,
        )


class AIUnavailableError(AIGatewayError):
    """AI 服务不可用异常 → 对应 ERR_AI_UNAVAILABLE（502/503/504）"""
    def __init__(self, detail: str = "AI 服务暂时不可用"):
        super().__init__(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=detail,
            error_code=ErrorCode.ERR_AI_UNAVAILABLE,
        )


class AIConnectionFailedError(AIGatewayError):
    """AI 服务连接失败异常 → 对应 ERR_AI_CONNECTION_FAILED"""
    def __init__(self, detail: str = "无法连接到 AI 服务"):
        super().__init__(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=detail,
            error_code=ErrorCode.ERR_AI_CONNECTION_FAILED,
        )


class AINotConfiguredError(AIGatewayError):
    """AI 服务未配置异常 → 对应 ERR_AI_NOT_CONFIGURED"""
    def __init__(self, detail: str = "AI 服务未配置"):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail,
            error_code=ErrorCode.ERR_AI_NOT_CONFIGURED,
        )


class AIInvalidResponseError(AIGatewayError):
    """AI 返回格式异常 → 对应 ERR_AI_INVALID_RESPONSE"""
    def __init__(self, detail: str = "AI 服务返回数据异常"):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail,
            error_code=ErrorCode.ERR_AI_INVALID_RESPONSE,
        )


# ── 保留旧的 AIClientError，兼容现有代码 ──
# ai_clients.py 里还有 AIClientError/AIClientTimeoutError 等定义
# 这里保留一个兼容类，后续 Step 3 做重试中间件时统一迁移
class AIClientError(HTTPException):
    """AI服务调用异常（向后兼容）"""
    def __init__(self, detail: str = "AI服务调用失败"):
        super().__init__(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=detail)
        self.error_code = ErrorCode.ERR_AI_UNAVAILABLE
        self.error_category = ErrorCategory.AI_GATEWAY


# ── 基础设施异常（新增）──

class InfraError(HTTPException):
    """基础设施异常基类"""
    def __init__(
        self,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail: str = "系统基础设施异常",
        error_code: ErrorCode = ErrorCode.ERR_DATABASE_FAILURE,
    ):
        super().__init__(status_code=status_code, detail=detail)
        self.error_code = error_code
        self.error_category = ErrorCategory.INFRA


class DatabaseError(InfraError):
    """数据库操作失败 → 对应 ERR_DATABASE_FAILURE"""
    def __init__(self, detail: str = "数据库操作失败"):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail,
            error_code=ErrorCode.ERR_DATABASE_FAILURE,
        )


class StorageError(InfraError):
    """文件存储失败 → 对应 ERR_STORAGE_FAILURE"""
    def __init__(self, detail: str = "文件存储失败"):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail,
            error_code=ErrorCode.ERR_STORAGE_FAILURE,
        )


class ExternalServiceError(InfraError):
    """外部非AI服务失败 → 对应 ERR_EXTERNAL_SERVICE（如天气API）"""
    def __init__(self, detail: str = "外部服务调用失败"):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail,
            error_code=ErrorCode.ERR_EXTERNAL_SERVICE,
        )
class AIContentValidationError(Exception):
    """当 AI 返回的内容虽然收到了，但不符合约束要求时抛出（如试穿改错了身体部位）。
    
    该异常可重试 — 常用于触发 mask 模式的 second-pass 调用。
    """
    def __init__(self, message: str, raw_response: Optional[str] = None):
        super().__init__(message)
        self.raw_response = raw_response