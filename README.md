# 智能衣橱系统 (Smart Wardrobe System)

一个基于 AI 的智能衣橱管理系统，提供虚拟试穿、智能穿搭推荐、衣物管理等功能。

## 📋 项目简介

智能衣橱系统是一个全栈 Web 应用，帮助用户管理个人衣橱，通过 AI 技术实现虚拟试穿和个性化穿搭推荐。系统集成了 Hugging Face 的虚拟试穿模型和百川大模型，为用户提供智能化的衣橱管理体验。

### 核心功能

- 👔 **衣物管理**：添加、编辑、删除衣物，支持分类、标签、季节等属性管理
- 🎨 **虚拟试穿**：基于 AI 模型生成虚拟试穿效果图
- 💡 **智能推荐**：根据天气、个人衣橱和风格偏好生成穿搭推荐
- 🏷️ **自动标签**：AI 自动识别衣物特征并生成标签
- 📊 **历史记录**：查看虚拟试穿历史和推荐记录
- ⭐ **收藏功能**：收藏喜欢的试穿效果和推荐搭配
- 🌤️ **天气适配**：根据实时天气信息推荐合适的穿搭

## 🛠️ 技术栈

### 后端
- **框架**：FastAPI 0.104.1
- **数据库**：SQLite (SQLAlchemy 2.0)
- **认证**：JWT (python-jose)
- **AI 服务**：
  - Hugging Face API (虚拟试穿)
  - 百川大模型 (标签识别、推荐理由生成)
- **其他**：httpx, Pillow, bcrypt

### 前端
- **框架**：Vue.js 3 (CDN)
- **UI 组件**：Vant UI
- **HTTP 客户端**：原生 Fetch API
- **样式**：Tailwind CSS (内联)

## 📁 项目结构

```
smart-wardrobe-system-test/
├── backend/                 # 后端服务
│   ├── app/
│   │   ├── main.py         # FastAPI 应用入口
│   │   ├── config.py       # 配置管理
│   │   ├── database.py     # 数据库配置
│   │   ├── models.py       # ORM 模型
│   │   ├── schemas.py      # Pydantic 模型
│   │   ├── security.py     # JWT 认证
│   │   ├── routers/        # API 路由
│   │   │   ├── auth.py     # 认证相关
│   │   │   ├── wardrobe.py # 衣橱管理
│   │   │   ├── tryon.py    # 虚拟试穿
│   │   │   ├── recommendations.py # 穿搭推荐
│   │   │   ├── records.py  # 历史记录
│   │   │   └── profile.py  # 用户信息
│   │   └── services/       # 业务逻辑
│   │       ├── ai_clients.py      # AI 服务客户端
│   │       ├── image_storage.py   # 图片存储
│   │       ├── tagging.py         # 标签识别
│   │       ├── outfit_logic.py    # 穿搭逻辑
│   │       └── weather.py         # 天气服务
│   ├── requirements.txt    # Python 依赖
│   ├── README.md           # 后端文档
│   └── .env                # 环境变量配置
│
├── front/                  # 前端应用
│   ├── index.html         # 主页面（单页应用）
│   ├── api.js             # API 客户端
│   ├── wardrobe-icon.png  # 应用图标
│   └── README.md          # 前端文档
│
└── README.md              # 项目总文档（本文件）
```

## 🚀 快速开始

### 环境要求

- **Python**: 3.8+
- **Node.js**: 不需要（前端使用 CDN）
- **浏览器**: Chrome/Firefox/Safari/Edge (现代浏览器)

### 1. 克隆项目

```bash
git clone <repository-url>
cd smart-wardrobe-system-test
```

### 2. 后端配置

#### 2.1 安装依赖

```bash
cd backend

# 创建虚拟环境（推荐）
python -m venv .venv

# 激活虚拟环境
# Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# Windows CMD:
.venv\Scripts\activate.bat
# Linux/Mac:
source .venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

#### 2.2 配置环境变量

在 `backend/` 目录下创建 `.env` 文件：

```env
# 数据库配置
DATABASE_URL=sqlite:///./smartwardrobe.db

# JWT 配置（生产环境请使用：openssl rand -hex 32 生成）
JWT_SECRET_KEY=your-secret-key-here
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7
JWT_CLOCK_SKEW_SECONDS=60

# 前端地址（CORS）
FRONTEND_ORIGIN=http://localhost:8080

# ========== AI 服务配置（必需）==========

# 1. Hugging Face API Key（虚拟试穿功能）
# 获取方式：访问 https://huggingface.co/settings/tokens
# 创建新 Token，选择 "Read" 权限
HUGGINGFACE_API_KEY=your-huggingface-api-key-here
HUGGINGFACE_LEFFA_MODEL=facebook/leffa

# 2. 百川大模型 API Key（标签识别和推荐功能）
# 获取方式：访问百川大模型官网注册并获取 API Key
BAICHUAN_API_KEY=your-baichuan-api-key-here
BAICHUAN_ENDPOINT=https://api.baichuan-ai.com/v1/chat/completions
BAICHUAN_MODEL=Baichuan4-Air
```

> 💡 **提示**：详细的 API Key 配置指南请参考 `backend/API_KEYS_SETUP.md`

#### 2.3 初始化数据库

数据库会在首次启动时自动创建。如需手动初始化：

```bash
python init_db.py
```

#### 2.4 启动后端服务

```bash
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
```

后端服务将在 `http://localhost:8001` 启动。

### 3. 前端配置

#### 3.1 启动前端服务

```bash
cd front
python -m http.server 8080
```

前端应用将在 `http://localhost:8080` 启动。

> ⚠️ **注意**：前端必须通过 HTTP 服务器访问，不能直接打开 HTML 文件。

### 4. 访问应用

打开浏览器访问：`http://localhost:8080`

## 📖 使用指南

### 用户注册与登录

1. 首次使用需要注册账号（使用手机号）
2. 登录后可以修改个人信息和头像

### 添加衣物

1. 进入"衣橱"页面
2. 点击"添加衣物"按钮
3. 上传衣物图片
4. 填写衣物信息（名称、分类、颜色、季节等）
5. 可选择添加自定义标签
6. 系统会自动识别并添加 AI 标签

### 虚拟试穿

1. 在"衣橱"页面选择一件衣物
2. 点击"虚拟试穿"按钮
3. 上传个人照片或使用已有照片
4. 等待 AI 生成试穿效果图
5. 可以收藏喜欢的试穿效果

### 获取穿搭推荐

1. 在"推荐"页面查看自动生成的每日推荐
2. 或进入"智能衣橱"页面，选择风格、场景、季节等条件
3. 系统会根据天气和你的衣橱生成个性化推荐
4. 推荐理由包含天气、风格、颜色等信息

### 查看历史记录

1. 进入"历史"页面
2. 切换"虚拟试穿记录"和"推荐记录"标签
3. 点击记录可查看详细信息

## 🔧 开发指南

### API 文档

启动后端服务后，访问以下地址查看 API 文档：

- Swagger UI: `http://localhost:8001/docs`
- ReDoc: `http://localhost:8001/redoc`

### 数据库迁移

项目使用 Alembic 进行数据库迁移管理：

```bash
cd backend

# 创建迁移
alembic revision --autogenerate -m "描述信息"

# 应用迁移
alembic upgrade head
```

### 日志

后端日志文件：`backend/smartwardrobe.log`

日志级别可通过环境变量 `LOG_LEVEL` 配置（默认：INFO）

## 🐛 故障排除

### 常见问题

1. **虚拟试穿失败**
   - 检查 Hugging Face API Key 是否正确配置
   - 确认网络连接正常
   - 查看后端日志了解详细错误信息

2. **标签识别失败**
   - 检查百川大模型 API Key 是否正确配置
   - 确认 API 额度是否充足

3. **前端无法连接后端**
   - 确认后端服务已启动（`http://localhost:8001`）
   - 检查 `FRONTEND_ORIGIN` 配置是否正确
   - 查看浏览器控制台的错误信息

4. **图片上传失败**
   - 确认 `uploads/` 目录存在且有写权限
   - 检查图片格式是否支持（JPG、PNG、WEBP）

### 调试工具

后端提供了多个调试脚本（位于 `backend/scripts/`）：

```bash
# 测试百川 API
python scripts/test_baichuan.py

# 测试 Hugging Face API
python scripts/test_huggingface_leffa.py

# 检查配置
python scripts/check_baichuan.py
```

## 📝 环境变量说明

### 必需配置

- `JWT_SECRET_KEY`: JWT 密钥（生产环境必须更改）
- `HUGGINGFACE_API_KEY`: Hugging Face API Key（虚拟试穿功能）
- `BAICHUAN_API_KEY`: 百川大模型 API Key（标签识别和推荐功能）

### 可选配置

- `DATABASE_URL`: 数据库连接字符串（默认：SQLite）
- `FRONTEND_ORIGIN`: 前端地址（CORS，默认：http://localhost:8080）
- `LOG_LEVEL`: 日志级别（默认：INFO）
- `LOG_FILE`: 日志文件路径（默认：smartwardrobe.log）

完整配置说明请参考 `backend/README.md`

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

本项目采用 MIT 许可证。

## 📞 联系方式

如有问题或建议，请通过 Issue 反馈。

## 🙏 致谢

- [FastAPI](https://fastapi.tiangolo.com/) - 现代、快速的 Web 框架
- [Vue.js](https://vuejs.org/) - 渐进式 JavaScript 框架
- [Vant](https://vant-ui.github.io/vant/) - 轻量、可靠的移动端组件库
- [Hugging Face](https://huggingface.co/) - AI 模型平台
- [百川大模型](https://www.baichuan-ai.com/) - 大语言模型服务

---

**享受智能衣橱管理体验！** 🎉



