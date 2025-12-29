# 智能衣橱系统 - 后端

## 快速启动
### 1. 环境准备
- Python 3.8+
- 安装依赖：`pip install -r requirements.txt`

### 2. 配置环境变量
复制 `.env.example` 为 `.env`，修改以下关键配置：
```env
# 数据库
DATABASE_URL=sqlite:///./smartwardrobe.db

# JWT密钥（生产环境用：openssl rand -hex 32 生成）
JWT_SECRET_KEY=your-secret-key

# 前端地址（跨域）
FRONTEND_ORIGIN=http://localhost:8080

# AI服务配置（根据实际地址修改）
LEFFA_ENDPOINT=https://leffa-api.example.com/generate
FASHIONCLIP_ENDPOINT=https://fashionclip-api.example.com/tag
BAICHUAN_API_KEY=your-baichuan-api-key