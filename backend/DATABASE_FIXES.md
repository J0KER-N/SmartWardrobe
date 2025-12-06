# 数据库初始化问题修复说明

## 修复的问题

### 1. Enum 类型定义
**问题**：`TryOnStatus` 使用了 `str, Enum`，但在 SQLAlchemy 中需要正确的枚举类型。

**修复**：
- 导入 `from enum import Enum as PyEnum`
- 将 `TryOnStatus` 定义为 `class TryOnStatus(str, PyEnum)`
- 在 SQLAlchemy Column 中使用 `Enum(TryOnStatus, native_enum=False, length=20)`

### 2. 默认值问题
**问题**：`default=dict` 和 `default=datetime.utcnow` 在某些情况下可能有问题。

**修复**：
- 为所有带默认值的字段添加 `nullable=False`
- `default=dict` 保持原样（SQLAlchemy 会正确处理）
- `default=datetime.utcnow` 保持原样（函数引用会自动调用）

### 3. SQLite 连接参数
**问题**：SQLite 在多线程环境下需要 `check_same_thread=False`。

**修复**：
- 在 `app/database.py` 中为 SQLite 添加 `connect_args={"check_same_thread": False}`

### 4. Pydantic 验证器
**问题**：Pydantic v2 中 `field_validator` 的 `info.data` 访问方式改变。

**修复**：
- 将验证器改为 `@classmethod`
- 将生产环境 JWT 密钥检查移到 `get_settings()` 函数中

## 测试数据库初始化

运行测试脚本：

```bash
python test_db_init.py
```

或者直接使用 Alembic：

```bash
# 创建初始迁移
alembic revision --autogenerate -m "Initial migration"

# 执行迁移
alembic upgrade head
```

## 常见错误及解决方案

### 错误 1: "Enum type not supported"
**原因**：SQLAlchemy 需要明确指定枚举类型。

**解决**：使用 `Enum(TryOnStatus, native_enum=False, length=20)`

### 错误 2: "SQLite objects created in a thread can only be used in that same thread"
**原因**：SQLite 默认不支持多线程。

**解决**：添加 `connect_args={"check_same_thread": False}`

### 错误 3: "ValidationInfo has no attribute 'data'"
**原因**：Pydantic v2 API 变化。

**解决**：将验证逻辑移到模型实例化后，在 `get_settings()` 中检查。

### 错误 4: "default=dict is mutable"
**原因**：虽然技术上可以，但最好使用不可变默认值。

**解决**：当前实现可以工作，SQLAlchemy 会正确处理。如需更安全，可以使用 `default_factory=dict`。

## 验证步骤

1. **检查模型定义**：
   ```python
   from app.models import Base, TryOnStatus
   print(TryOnStatus.pending.value)  # 应该输出 "pending"
   ```

2. **检查数据库连接**：
   ```python
   from app.database import engine
   from sqlalchemy import text
   with engine.connect() as conn:
       conn.execute(text("SELECT 1"))
   ```

3. **检查表创建**：
   ```python
   from app.models import Base
   from app.database import engine
   Base.metadata.create_all(bind=engine)
   ```

4. **使用 Alembic**：
   ```bash
   alembic revision --autogenerate -m "Initial migration"
   alembic upgrade head
   ```

## 下一步

如果仍有问题，请检查：

1. 依赖是否正确安装：`pip install -r requirements.txt`
2. 环境变量是否正确配置：检查 `.env` 文件
3. 数据库 URL 是否正确：`DATABASE_URL` 格式
4. 查看完整错误信息：运行 `python test_db_init.py` 查看详细错误

