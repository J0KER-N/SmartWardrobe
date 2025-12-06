# metadata 字段冲突修复

## 问题描述

在运行 `alembic revision --autogenerate` 时遇到错误：
```
sqlalchemy.exc.InvalidRequestError: Attribute name 'metadata' is reserved when using the Declarative API.
```

## 原因

在 SQLAlchemy 的 Declarative API 中，`metadata` 是一个保留属性名，用于存储表的元数据信息（`Base.metadata`）。当模型类中定义名为 `metadata` 的列时，会与这个保留属性冲突。

## 解决方案

将 `TryOnRecord` 模型中的 `metadata` 字段重命名为 `meta_data`。

### 修改的文件

1. **app/models.py**
   - 将 `metadata = Column(JSON, ...)` 改为 `meta_data = Column(JSON, ...)`

2. **app/routers/tryon.py**
   - 将 `record.metadata = {...}` 改为 `record.meta_data = {...}`

## 验证

修复后，可以正常运行：

```bash
# 创建迁移
alembic revision --autogenerate -m "Initial migration"

# 执行迁移
alembic upgrade head
```

或者运行测试脚本：

```bash
python test_db_init.py
```

## 注意事项

- `Base.metadata` 是 SQLAlchemy 的正确用法，用于表的元数据，不需要修改
- 如果将来需要在 API 响应中包含这个字段，确保使用 `meta_data` 而不是 `metadata`
- 数据库迁移会自动处理字段重命名

