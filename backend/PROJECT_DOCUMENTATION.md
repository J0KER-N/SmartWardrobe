# 智能衣橱系统 后端 — 项目说明与运行指南

## 一、项目概述
这是一个基于 FastAPI + SQLAlchemy 的智能衣橱后端服务，提供用户注册/登录、衣物管理、虚拟试穿、穿搭推荐、试穿收藏等功能。项目通过可插拔的 AI 客户端（如 Leffa、FashionCLIP、百川）支持图片标签识别、试穿生成与穿搭文案生成。

主要技术栈：
- Python 3.8+
- FastAPI
- SQLAlchemy 2.x
- Alembic（迁移管理）
- httpx（外部 AI 服务调用）
- Pillow（图片处理）

代码结构（关键目录/文件）：
- `app/`：应用源码
  - `main.py`：FastAPI 应用启动与生命周期管理
  - `config.py`：配置与环境变量读取
  - `database.py`：SQLAlchemy 引擎、Session、`Base` 与 `init_db()`
  - `models.py`：ORM 模型定义（User、Garment、TryonRecord、Favorite）
  - `schemas.py`：Pydantic 请求/响应模型
  - `security.py`：密码哈希与 JWT 生成/验证
  - `routers/`：各功能路由（认证、衣橱、试穿、推荐、记录、个人中心）
  - `services/`：AI 客户端、图片存储、标签识别、穿搭逻辑等
- `migrations/` & `alembic.ini`：Alembic 配置与迁移脚本
- `requirements.txt`：Python 依赖
- `.env` / `.env.example`：环境变量示例

## 二、环境准备
1. 克隆/下载项目，并进入后端目录：
```powershell
cd C:\Users\23708\Desktop\smart-wardrobe-system-test\backend
```
2. 创建并激活虚拟环境（推荐）：
```powershell
python -m venv .venv
.\.venv\Scripts\activate
```
或者（conda）：
```powershell
conda create -n wardrobe python=3.10 -y
conda activate wardrobe
```
3. 安装依赖：
```powershell
pip install -r requirements.txt
```
4. 配置环境变量：复制 `.env.example` 到 `.env` 并修改必要值（尤其是 `JWT_SECRET_KEY`、`DATABASE_URL`、AI 服务配置等）。

## 三、本地运行
直接使用 Uvicorn 启动（开发模式）：
```powershell
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
或者：
```powershell
python -m uvicorn app.main:app --reload
```

健康检查：
- 基本：GET `/health`
- 详细：GET `/health/detailed`

## 四、数据库初始化（两种方式）
1. 直接在代码中创建表（快速）：
```powershell
python init_db.py
```
该脚本会读取 `.env` 中的 `DATABASE_URL` 并使用 SQLAlchemy 的 `Base.metadata.create_all()` 创建表（适用于开发、测试）。

2. 使用 Alembic 迁移（推荐在生产）：
```powershell
alembic upgrade head
```
注意：运行 Alembic 前请确认 `alembic.ini` 中的 `sqlalchemy.url` 配置或环境变量 `DATABASE_URL` 指向正确的数据库，并确保对应数据库驱动（如 `psycopg2-binary`）已安装。

## 五、常见问题与快速排查
- 报错 `ModuleNotFoundError: No module named 'dotenv'`：请安装 `python-dotenv`（已列在 `requirements.txt`）：
  ```powershell
  pip install python-dotenv
  ```
- Alembic 报 `Can't load plugin: sqlalchemy.dialects:driver`：检查 `alembic.ini` 中的 `sqlalchemy.url` 或环境变量 `DATABASE_URL`，确保它是像 `sqlite:///./smartwardrobe.db` 或 `postgresql+psycopg2://user:pass@host/db` 这样的合法 URL，并安装对应 DB 驱动。
- 上传文件相关异常：确保上传使用 `multipart/form-data`，并在接收端正确使用 `UploadFile` 与 `Form`/`Depends` 来解析表单字段（见“改进建议”）。

## 六、安全与生产注意事项
- 绝对不要在生产环境使用默认 `JWT_SECRET_KEY`。使用 `openssl rand -hex 32` 生成强密钥。
- 在生产中建议禁用 `Base.metadata.create_all()`；使用 Alembic 管理数据库迁移。启动脚本不应自动创建表。
- 为敏感日志（如异常堆栈）设置合适的日志等级与日志输出目标，不要在生产日志中泄露密钥或用户密码。
- 对上传的文件路径和文件名做严格校验，防止路径遍历或恶意文件写入。

## 七、代码问题与优化建议（按优先级）

高优先级（需修复）
- `app/services/image_storage.py` 中 `save_tryon_image` 使用 `BytesIO` 但未导入 `io.BytesIO`（会导致 NameError）。建议在文件头部添加 `from io import BytesIO`。
- 接口接收文件与表单数据的实现不够稳健。例如 `wardrobe.create_garment` 采用 `garment_data: GarmentCreate = Depends()` 同时接收 `UploadFile`，在实际 `multipart/form-data` 场景下通常需要把表单字段声明为 `Form(...)`，或在依赖中明确使用 `Form`。否则 FastAPI 可能无法正确解析。建议修改为显式参数：
  ```python
  from fastapi import Form
  def create_garment(name: str = Form(...), category: str = Form(...), file: UploadFile = File(...)):
      ...
  ```
- `ai_clients.extract_garment_tags` 将二进制转换为 `image_data.hex()` 发送请求，导致请求体长度暴增。建议用 Base64（`base64.b64encode(image_data).decode()`）或直接以 multipart 上传。

中等优先级（改进能提升可靠性或可维护性）
- `config.py` 中 `field_validator` 用法需确认与 Pydantic v2 的期望签名一致。建议使用 `model_validator` 或在配置加载后进行显式验证，保证在 production 环境 `JWT_SECRET_KEY` 被强制更改。
- 推荐把 Pydantic 模型中的可变默认如 `manual_tags: List[str] = Field(default=list)` 改为 `default_factory=list`，避免共享可变默认的问题（虽然在很多使用场景下表现正常，但更安全）。
- `security.py` 建议使用 `passlib` 的 `bcrypt` 上下文以便更好地管理密码哈希算法与升级策略。
- 考虑把关键 I/O（对 AI 服务的调用、文件 I/O）改为异步实现以提升吞吐（需要把对应路由改为 async）。

低优先级（建议采纳以提高质量）
- 增加单元测试与集成测试（使用 pytest），自动化 CI（如 GitHub Actions）以在 PR 时运行 lint 与测试。
- 添加 `requirements-dev.txt`，包含 `black`、`ruff`、`pytest`、`pre-commit` 等开发工具。
- 增加 API 文档示例（在 `docs/` 或 Swagger 示例）与 Postman/Insomnia 集合。

## 八、后续我可以帮你做的工作（选项）
1. 立即修复高优先级问题（例如补 `BytesIO` 导入、改造 `create_garment` 接口）。
2. 将 `init_db.py` 改为优先使用 Alembic 升级（fallback 到 create_all）。
3. 添加 CI 配置和基本测试用例。
4. 对整个代码库运行静态分析并生成逐文件的问题列表（更深入的审查）。

请告诉我你希望我先做哪一项（例如 `修复 Bug` 或 `生成更详细的逐文件审查`）。我会据此继续。
