# 配置说明文档

本文档说明如何配置和部署智能衣橱系统后端。

## 1. 环境变量配置

复制 `.env.example` 为 `.env` 并填写实际配置值：

```bash
cp .env.example .env
```

### 核心配置项

#### JWT 密钥（必须修改）

**生产环境必须修改！** 使用以下命令生成安全的密钥：

```bash
openssl rand -hex 32
```

将生成的密钥填入 `JWT_SECRET_KEY` 和 `JWT_REFRESH_SECRET_KEY`。

#### 数据库配置

**开发环境（SQLite）：**
```env
DATABASE_URL=sqlite:///./smartwardrobe.db
```

**生产环境（PostgreSQL）：**
```env
DATABASE_URL=postgresql://user:password@localhost:5432/smartwardrobe
DATABASE_POOL_SIZE=10
DATABASE_MAX_OVERFLOW=20
```

#### AI 服务端点

配置你已部署的 AI 服务：

```env
# Leffa 试穿模型（已部署在云端）
LEFFA_ENDPOINT=https://your-leffa-service.com/api/tryon
LEFFA_TIMEOUT=120

# FashionCLIP 标签识别（已部署在云端）
FASHIONCLIP_ENDPOINT=https://your-fashionclip-service.com/api/tag
FASHIONCLIP_TIMEOUT=60

# 百川大模型 API
BAICHUAN_API_URL=https://api.baichuan-ai.com/v1/chat/completions
BAICHUAN_API_KEY=your-baichuan-api-key
BAICHUAN_MODEL=baichuan-fashion-expert
```

#### 对象存储配置

**本地存储（开发环境）：**
```env
OBJECT_STORAGE_TYPE=local
MEDIA_ROOT=./media
```

**生产环境（推荐使用云存储）：**
```env
# AWS S3 示例
OBJECT_STORAGE_TYPE=s3
OBJECT_STORAGE_ENDPOINT=https://s3.amazonaws.com
OBJECT_STORAGE_BUCKET=your-bucket-name
OBJECT_STORAGE_ACCESS_KEY=your-access-key
OBJECT_STORAGE_SECRET_KEY=your-secret-key
OBJECT_STORAGE_REGION=us-east-1
```

## 2. 数据库迁移

使用 Alembic 管理数据库迁移：

```bash
# 初始化迁移（首次运行）
alembic init alembic

# 创建迁移文件
alembic revision --autogenerate -m "Initial migration"

# 执行迁移
alembic upgrade head

# 回滚迁移
alembic downgrade -1
```

## 3. 安装依赖

```bash
# 使用 pip
pip install -r requirements.txt

# 或使用 pip install -e . 安装开发版本
pip install -e .
```

## 4. 运行服务

### 开发环境

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 生产环境

使用 Gunicorn + Uvicorn workers：

```bash
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

## 5. 健康检查

访问以下端点检查服务状态：

- 基础健康检查：`GET /health`
- 详细健康检查：`GET /health/detailed`

## 6. 安全建议

### 生产环境检查清单

- [ ] 修改 `JWT_SECRET_KEY` 为强随机字符串
- [ ] 设置 `ENVIRONMENT=production`
- [ ] 配置正确的 `FRONTEND_ORIGIN` 或 `CORS_ALLOW_ORIGINS`
- [ ] 使用 PostgreSQL 替代 SQLite
- [ ] 配置对象存储（S3/OSS）替代本地存储
- [ ] 启用 HTTPS
- [ ] 配置日志文件路径
- [ ] 设置合理的数据库连接池大小
- [ ] 配置 Redis（如使用异步任务）

## 7. 测试

运行测试套件：

```bash
# 运行所有测试
pytest

# 运行特定测试文件
pytest tests/test_auth.py

# 查看覆盖率
pytest --cov=app tests/
```

## 8. 日志配置

日志级别通过 `LOG_LEVEL` 环境变量控制：

- `DEBUG`: 详细调试信息
- `INFO`: 一般信息（推荐开发环境）
- `WARNING`: 警告信息（推荐生产环境）
- `ERROR`: 仅错误信息

设置 `LOG_FILE` 路径可将日志写入文件。

## 9. API 文档

启动服务后访问：

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## 10. 常见问题

### Q: JWT 密钥验证失败

A: 确保生产环境的 `JWT_SECRET_KEY` 长度至少 32 字符，且不是默认值。

### Q: 数据库连接失败

A: 检查 `DATABASE_URL` 格式是否正确，PostgreSQL 需要安装 `psycopg2`。

### Q: AI 服务调用超时

A: 根据实际服务响应时间调整 `LEFFA_TIMEOUT` 和 `FASHIONCLIP_TIMEOUT`。

### Q: 图片上传失败

A: 检查 `MEDIA_ROOT` 目录权限，确保应用有写入权限。

## 11. 性能优化建议

1. **数据库索引**：已为常用查询字段添加索引（`owner_id`, `phone` 等）
2. **连接池**：根据并发量调整 `DATABASE_POOL_SIZE`
3. **图片压缩**：已启用自动压缩，可通过 `IMAGE_QUALITY` 调整质量
4. **分页查询**：所有列表接口支持分页，避免一次性加载大量数据
5. **异步任务**：试穿生成等耗时操作建议使用 Celery + Redis 异步处理

