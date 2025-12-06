# 智能衣橱系统

一个基于 Vue 3 + FastAPI 的智能衣橱管理系统，支持衣物数字化存储、智能试穿、每日推荐等功能。

## 项目结构

```
smart-wardrobe-system/
├── backend/              # 后端服务（FastAPI）
│   ├── app/             # 应用主目录
│   │   ├── routers/     # API 路由
│   │   ├── services/    # 业务服务层
│   │   ├── models.py   # 数据模型
│   │   └── main.py     # 应用入口
│   ├── alembic/        # 数据库迁移
│   ├── tests/          # 测试文件
│   └── requirements.txt # Python 依赖
├── front/              # 前端应用（Vue 3 + Vant）
│   ├── index.html      # 主页面
│   └── api.js          # API 服务封装
└── README.md           # 项目说明
```

## 快速开始

### 后端启动

1. **进入后端目录**
   ```bash
   cd backend
   ```

2. **安装依赖**
   ```bash
   pip install -r requirements.txt
   ```

3. **配置环境变量**
   
   创建 `.env` 文件（参考 `CONFIGURATION.md`）：
   ```env
   DATABASE_URL=sqlite:///./smartwardrobe.db
   JWT_SECRET_KEY=your-secret-key-here
   FRONTEND_ORIGIN=http://localhost:8080
   ```

4. **初始化数据库**
   ```bash
   alembic upgrade head
   ```

5. **启动服务**
   ```bash
   uvicorn app.main:app --reload
   ```

   后端服务将在 `http://127.0.0.1:8000` 启动

### 前端启动

1. **使用本地服务器**

   由于前端使用 ES6 模块，需要通过 HTTP 服务器访问，不能直接打开 HTML 文件。

   **方法一：使用 Python 简单服务器**
   ```bash
   cd front
   python -m http.server 8080
   ```

   **方法二：使用 Node.js http-server**
   ```bash
   npm install -g http-server
   cd front
   http-server -p 8080
   ```

   **方法三：使用 VS Code Live Server 插件**

2. **访问应用**
   
   打开浏览器访问 `http://localhost:8080`

## 功能模块

### 后端 API

- **认证模块** (`/auth`)
  - 用户注册
  - 用户登录（密码/验证码）
  - Token 刷新

- **衣橱模块** (`/wardrobe`)
  - 衣物列表（支持筛选、分页）
  - 添加衣物（支持图片上传、自动标签识别）
  - 更新衣物信息
  - 删除衣物

- **试穿模块** (`/tryon`)
  - 生成虚拟试穿效果

- **推荐模块** (`/recommendations`)
  - 每日穿搭推荐（基于天气）

- **记录模块** (`/records`)
  - 试穿历史记录
  - 收藏管理

- **个人中心** (`/profile`)
  - 用户信息管理
  - 密码修改

### 前端功能

- 用户登录/注册
- 衣物管理（添加、查看、编辑、删除）
- 智能试穿
- 每日推荐
- 历史记录查看
- 收藏管理
- 个人中心

## API 文档

启动后端服务后，访问以下地址查看 API 文档：

- Swagger UI: http://127.0.0.1:8000/docs
- ReDoc: http://127.0.0.1:8000/redoc

## 配置说明

详细配置说明请参考 `backend/CONFIGURATION.md`

### 重要配置项

- `JWT_SECRET_KEY`: JWT 密钥（生产环境必须修改）
- `FRONTEND_ORIGIN`: 前端地址（用于 CORS）
- `DATABASE_URL`: 数据库连接字符串
- AI 服务端点（Leffa、FashionCLIP、百川）

## 开发说明

### 前端 API 调用

前端通过 `front/api.js` 统一管理所有 API 调用：

```javascript
import { authAPI, wardrobeAPI } from './api.js';

// 登录
await authAPI.login(phone, password);

// 获取衣物列表
const garments = await wardrobeAPI.getGarments({ category: 'top' });
```

### 后端开发

- 路由定义在 `backend/app/routers/` 目录
- 业务逻辑在 `backend/app/services/` 目录
- 数据模型在 `backend/app/models.py`

## 常见问题

### 1. CORS 错误

确保后端 `.env` 中配置了 `FRONTEND_ORIGIN`：
```env
FRONTEND_ORIGIN=http://localhost:8080
```

### 2. 前端无法访问后端

检查：
- 后端服务是否启动（`http://127.0.0.1:8000`）
- `front/api.js` 中的 `API_BASE_URL` 是否正确
- 浏览器控制台是否有错误信息

### 3. 数据库迁移失败

```bash
cd backend
alembic revision --autogenerate -m "描述"
alembic upgrade head
```

## 技术栈

### 后端
- FastAPI
- SQLAlchemy
- Alembic
- Pydantic
- JWT 认证

### 前端
- Vue 3
- Vant UI
- Tailwind CSS
- Fetch API

## 许可证

MIT License

