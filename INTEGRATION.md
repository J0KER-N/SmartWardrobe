# 稳定性与容错模块 — 集成说明

> 成员 D 交付物 | 2026-05

---

## 一、概览

本模块包含三个独立组件，可分别在其他服务中接入：

| 组件 | 文件 | 作用 | 依赖 |
|------|------|------|------|
| 错误分级体系 | `app/exceptions.py` | 统一错误码、分类、响应格式 | 无 |
| 结构化日志 | `app/logging/` | JSON 格式日志，含 task_id/latency_ms 等字段 | 无 |
| 重试中间件 | `app/middleware/` | AI 调用自动重试 + 指数退避 + Second-Pass | 前两者 |

---

## 二、错误分级体系

### 接入方式

```python
from backend.app.exceptions import (
    # 业务错误
    ResourceNotFoundError, InvalidInputError, EmptyWardrobeError,
    # AI 网关错误
    AITimeoutError, AIRateLimitError, AIUnavailableError,
    # 基础设施错误
    DatabaseError, StorageError,
    # 内容验证错误（Second-Pass 触发）
    AIContentValidationError,
    # 工具函数
    ErrorCode, error_response,
)
```

### 在路由中使用

```python
from backend.app.exceptions import AITimeoutError

@app.get("/tryon")
def do_tryon():
    try:
        result = call_ai_api()
    except Exception:
        raise AITimeoutError("试穿服务超时")
    return result
```

前端收到的响应：
```json
{
  "success": false,
  "error": {
    "code": "A001",
    "category": "AI_GATEWAY",
    "message": "试穿服务超时"
  }
}
```

### 错误码速查

| code | category | 说明 | HTTP 状态码 |
|------|----------|------|-------------|
| B001 | BUSINESS | 资源不存在 | 404 |
| B002 | BUSINESS | 资源已存在 | 400 |
| B003 | BUSINESS | 凭证无效 | 401 |
| B004 | BUSINESS | 输入参数错误 | 400 |
| B005 | BUSINESS | 衣橱为空 | 400 |
| A001 | AI_GATEWAY | AI 服务超时 | 504 |
| A002 | AI_GATEWAY | AI 服务限流 | 429 |
| A003 | AI_GATEWAY | AI 服务不可用 | 502 |
| A004 | AI_GATEWAY | 连接 AI 失败 | 502 |
| A005 | AI_GATEWAY | AI 服务未配置 | 500 |
| A006 | AI_GATEWAY | AI 返回异常 | 500 |
| I001 | INFRA | 数据库失败 | 500 |
| I002 | INFRA | 存储失败 | 500 |
| I003 | INFRA | 外部服务失败 | 500 |

---

## 三、结构化日志

### 接入方式

```python
from backend.app.logging import get_structured_logger, AICallContext

logger = get_structured_logger(__name__)
```

### 使用场景

#### 3.1 追踪 AI 调用（推荐）

```python
with AICallContext(
    logger,
    task_id="abc123",           # 不传自动生成
    service="baichuan",         # AI 服务名
    model="Baichuan4-Air",      # 模型名
    extras={                    # 可选扩展字段
        "prompt_version": "v2",
        "target_garment": "g_001",
    },
):
    result = call_ai_api()
    # with 块结束 → 自动记录 latency_ms、status="success"
```

#### 3.2 手动日志

```python
logger.info("操作完成", extra={"service": "weather", "latency_ms": 350})
logger.error("调用失败", extra={"error_code": "A001", "retry_count": 2})
```

### 输出示例

```json
{
  "timestamp": "2026-05-25T11:09:05+00:00",
  "level": "INFO",
  "logger": "app.services.ai_clients",
  "message": "AI调用完成 | service=baichuan model=Baichuan4-Air latency=1234ms status=success",
  "task_id": "abc123",
  "service": "baichuan",
  "model": "Baichuan4-Air",
  "status": "success",
  "latency_ms": 1234,
  "retry_count": 1
}
```

### 切换为 JSON 输出

在 `.env` 中设置：
```
LOG_FORMAT_TYPE=json
```

---

## 四、重试中间件

### 接入方式

```python
from backend.app.middleware import retry_on_ai_failure

@retry_on_ai_failure()
def my_ai_function():
    # AI 调用逻辑，遇到可重试错误自动重试
    pass
```

### 重试策略

| 场景 | 行为 | 退避 |
|------|------|------|
| 超时 / 502 / 503 / 504 | 重试（最多 N 次） | 指数退避 + 随机抖动 |
| 连接失败 | 重试 | 指数退避 |
| 400 参数错误 | 不重试，直接报错 | — |
| 429 限流 | 不重试，直接报错 | — |

### 配置（.env）

```
AI_MAX_RETRIES=3          # 最大重试次数
AI_RETRY_BASE_DELAY=1.0   # 首次等待秒数
AI_RETRY_MAX_DELAY=60.0   # 最大等待秒数
AI_RETRY_BACKOFF_MULTIPLIER=2.0  # 退避倍数
AI_RETRY_JITTER=True      # 是否加随机抖动
```

退避示例（base=1, multiplier=2, jitter=True）：
- 第 1 次重试：0~1s
- 第 2 次重试：0~2s
- 第 3 次重试：0~4s

---

## 五、Second-Pass Mask 模式

### 触发方式

当 AI 返回结果"看起来正常"但内容不合规时：

```python
from backend.app.exceptions import AIContentValidationError

if not validate_response(result):
    raise AIContentValidationError(
        "检测到非目标部位被修改",
        raw_response=str(result)
    )
```

### 自动行为

```
AIContentValidationError 被抛出
  → 重试中间件捕获
  → 下轮调用自动添加 mask=True
  → AI 以 mask 模式重新生成
  → 重试日志自动记录 mask_used=True
```

### 已在 `_sync_post_json` 中内置支持

装饰器注入 `_second_pass_mask=True` → `_sync_post_json` 自动追加 `mask: True` 到 payload。

---

## 六、完整链路示例

```python
from backend.app.logging import get_structured_logger, AICallContext
from backend.app.middleware import retry_on_ai_failure
from backend.app.exceptions import AIContentValidationError

logger = get_structured_logger(__name__)

@retry_on_ai_failure()
def generate_tryon_image(garment_id: str, user_photo: str):
    with AICallContext(
        logger, service="leffa", model="viton_hd",
        extras={"target_garment": garment_id}
    ):
        result = call_leffa_api(garment_id, user_photo)

        # 约束检测
        if garment_detection_failed(result):
            raise AIContentValidationError("非目标部位被修改")

        return result
```
