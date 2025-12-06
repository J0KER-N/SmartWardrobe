# Smart Wardrobe Backend

FastAPI 后端服务，面向"智能衣橱系统"提供：

- 手机号注册 / 登录与 JWT 鉴权（支持刷新令牌）
- 衣物数字化：图片上传、自动标签识别、手动维护
- 智能试穿：联动 Leffa、FashionCLIP、百川大模型
- 每日穿搭推荐：结合天气与衣物标签
- 搭配记录与收藏（支持分页查询）
- 衣物可视化筛选、批量操作（多维度筛选）
- 个人中心（资料、收藏、账户设置）

## ✨ 主要特性

- 🔒 **安全增强**：密码强度验证、JWT 刷新令牌、输入校验、CORS 配置
- 🖼️ **图片处理**：自动压缩、格式校验、大小限制、对象存储支持
- 🤖 **AI 集成**：完善的错误处理、重试机制、超时配置
- 📊 **数据库**：连接池配置、Alembic 迁移支持
- 📝 **日志监控**：结构化日志、健康检查接口
- 🧪 **测试覆盖**：单元测试和集成测试框架
- 📄 **分页查询**：所有列表接口支持分页

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

复制 `.env.example` 为 `.env` 并填写配置：

```bash
cp .env.example .env
# 编辑 .env 文件
```

**重要**：生产环境必须修改 `JWT_SECRET_KEY`（使用 `openssl rand -hex 32` 生成）

### 3. 初始化数据库

```bash
# 创建迁移
alembic revision --autogenerate -m "Initial migration"
# 执行迁移
alembic upgrade head
```

### 4. 运行服务

**开发环境：**
```bash
uvicorn app.main:app --reload
```

**生产环境：**
```bash
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### 5. 访问 API 文档

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- 健康检查: http://localhost:8000/health

## 📁 目录结构

```
smart-wardrobe-system/
├── app/
│   ├── config.py          # 配置管理（环境变量、验证）
│   ├── database.py         # 数据库连接和会话
│   ├── models.py           # SQLAlchemy 数据模型
│   ├── schemas.py          # Pydantic 数据验证
│   ├── security.py         # 安全工具（密码、JWT、验证）
│   ├── dependencies.py     # FastAPI 依赖注入
│   ├── main.py             # 应用入口（日志、CORS、路由）
│   ├── services/           # 业务服务层
│   │   ├── ai_clients.py   # AI 服务客户端（Leffa、FashionCLIP、百川）
│   │   ├── image_storage.py # 图片存储（本地/对象存储）
│   │   ├── tagging.py      # 标签识别服务
│   │   ├── weather.py       # 天气服务
│   │   └── outfit_logic.py # 穿搭推荐逻辑
│   └── routers/            # API 路由
│       ├── auth.py         # 认证（注册、登录、刷新令牌）
│       ├── wardrobe.py     # 衣橱管理（CRUD、筛选、分页）
│       ├── tryon.py        # 试穿生成
│       ├── recommendations.py # 推荐
│       ├── records.py      # 记录和收藏
│       └── profile.py      # 个人中心
├── alembic/                # 数据库迁移
│   ├── env.py
│   └── versions/
├── tests/                 # 测试
│   ├── conftest.py
│   ├── test_auth.py
│   ├── test_security.py
│   └── test_wardrobe.py
├── requirements.txt        # 依赖版本锁定
├── pyproject.toml          # 项目配置
├── CONFIGURATION.md        # 详细配置说明
└── IMPROVEMENTS.md         # 改进清单
```

## 🤖 AI 模型接入

### 已配置的模型

- **Leffa**：虚拟试穿生成（已部署在云端）
  - 配置：`LEFFA_ENDPOINT`
  - 超时：`LEFFA_TIMEOUT`（默认 120 秒）

- **FashionCLIP**：衣物标签识别（已部署在云端）
  - 配置：`FASHIONCLIP_ENDPOINT`
  - 超时：`FASHIONCLIP_TIMEOUT`（默认 60 秒）

- **百川大模型**：穿搭描述生成（API 调用）
  - 配置：`BAICHUAN_API_URL`, `BAICHUAN_API_KEY`
  - 模型：`BAICHUAN_MODEL`（默认 baichuan-fashion-expert）

### 需要根据实际情况调整

AI 服务接口封装在 `app/services/ai_clients.py` 中，请根据实际 API 文档调整：
- 请求参数格式
- 响应数据格式
- 错误处理逻辑

## 🔧 配置说明

详细配置说明请参考 [CONFIGURATION.md](CONFIGURATION.md)

### 核心配置项

- **数据库**：`DATABASE_URL`（支持 SQLite/PostgreSQL）
- **JWT**：`JWT_SECRET_KEY`（生产环境必须修改）
- **AI 服务**：`LEFFA_ENDPOINT`, `FASHIONCLIP_ENDPOINT`, `BAICHUAN_API_KEY`
- **对象存储**：`OBJECT_STORAGE_TYPE`（local/s3/oss）
- **日志**：`LOG_LEVEL`, `LOG_FILE`

## 🧪 测试

运行测试套件：

```bash
# 所有测试
pytest

# 特定测试文件
pytest tests/test_auth.py

# 带覆盖率
pytest --cov=app tests/
```

## 📋 改进清单

所有已完成的系统改进请参考 [IMPROVEMENTS.md](IMPROVEMENTS.md)

主要改进包括：
- ✅ 配置项完善（连接池、刷新令牌、图片处理等）
- ✅ 图片存储优化（校验、压缩、对象存储支持）
- ✅ AI 服务集成增强（错误处理、重试、超时）
- ✅ 数据库迁移支持（Alembic）
- ✅ 安全增强（密码验证、输入校验、CORS）
- ✅ 业务逻辑优化（分页、筛选）
- ✅ 日志与监控（结构化日志、健康检查）
- ✅ 测试覆盖（单元测试、集成测试）
- ✅ 依赖版本锁定

## 📚 相关文档

- [配置说明](CONFIGURATION.md) - 详细的环境配置和部署指南
- [改进清单](IMPROVEMENTS.md) - 所有系统改进的详细说明

## ⚠️ 部署前检查

- [ ] 修改 `JWT_SECRET_KEY`（生产环境必须）
- [ ] 配置实际的 AI 服务端点
- [ ] 设置 `ENVIRONMENT=production`
- [ ] 配置数据库（推荐 PostgreSQL）
- [ ] 配置对象存储（生产环境推荐）
- [ ] 执行数据库迁移
- [ ] 配置 CORS 允许的域名

