# 快速启动指南

## 前置要求

- Python 3.10+
- pip

## 一键启动（Windows）

双击运行 `start.bat` 文件，会自动启动前后端服务。

## 一键启动（Linux/Mac）

```bash
chmod +x start.sh
./start.sh
```

## 手动启动

### 1. 启动后端

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

后端将在 `http://127.0.0.1:8000` 启动

### 2. 启动前端

打开新的终端窗口：

```bash
cd front
python -m http.server 8080
```

前端将在 `http://localhost:8080` 启动

## 首次使用

1. **配置后端环境变量**

   在 `backend/` 目录创建 `.env` 文件（参考 `backend/.env.example`）：
   ```env
   FRONTEND_ORIGIN=http://localhost:8080
   JWT_SECRET_KEY=your-secret-key-here
   ```

2. **初始化数据库**

   ```bash
   cd backend
   alembic upgrade head
   ```

3. **访问应用**

   - 前端：http://localhost:8080
   - API 文档：http://127.0.0.1:8000/docs

## 测试账号

首次使用需要注册账号：
1. 打开前端页面
2. 点击"注册新用户"
3. 输入手机号和密码完成注册
4. 使用注册的账号登录

## 常见问题

### 端口被占用

- 后端端口 8000 被占用：修改 `uvicorn app.main:app --reload --port 8001`
- 前端端口 8080 被占用：修改 `python -m http.server 8081`
- 同时修改 `front/api.js` 中的 `API_BASE_URL`

### CORS 错误

确保 `backend/.env` 中配置了正确的 `FRONTEND_ORIGIN`

### 数据库错误

运行 `alembic upgrade head` 初始化数据库

