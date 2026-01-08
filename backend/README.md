# 智能衣橱系统 - 后端

## 快速启动
### 1. 环境准备
- Python 3.8+
- 安装依赖：`pip install -r requirements.txt`
- 激活虚拟环境： . .\.venv\Scripts\Activate.ps1
- 启动后端；
cd backend
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8001

### 2. 配置环境变量
复制 `.env.example` 为 `.env`，修改以下关键配置：
```env
# 数据库
DATABASE_URL=sqlite:///./smartwardrobe.db

# JWT密钥（生产环境用：openssl rand -hex 32 生成）
JWT_SECRET_KEY=your-secret-key
# JWT Token过期时间配置（可选，默认值如下）
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60  # Access Token过期时间（分钟），默认15分钟，建议60-120分钟
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7     # Refresh Token过期时间（天），默认7天
JWT_CLOCK_SKEW_SECONDS=60           # 时钟偏差容忍（秒），默认60秒

# 前端地址（跨域）
FRONTEND_ORIGIN=http://localhost:8080

# ========== AI服务配置（必需）==========
# 1. Hugging Face API Key（用于虚拟试穿功能 - 必需）
#    获取方式：
#    - 访问 https://huggingface.co/settings/tokens
#    - 点击 "New token" 创建新的 Access Token
#    - 选择 "Read" 权限（或细粒度权限中的 "对无服务器推理 API 进行调用"）
#    - 复制 Token 并粘贴到下方
HUGGINGFACE_API_KEY=your-huggingface-api-key-here
HUGGINGFACE_LEFFA_MODEL=facebook/leffa  # 可选，默认使用 facebook/leffa（支持 Inference API）
# 其他可用模型：levihsu/OOTDiffusion（可能不支持 Inference API）



# 2. 百川大模型 API Key（用于标签识别和推荐穿搭功能 - 必需）
#    获取方式：访问百川大模型官网注册并获取API Key
BAICHUAN_API_KEY=your-baichuan-api-key-here
BAICHUAN_ENDPOINT=https://api.baichuan-ai.com/v1/chat/completions
BAICHUAN_MODEL=Baichuan4-Air  # 可选，默认使用此模型

# ========== 已废弃的配置（保留用于兼容性）==========
LEFFA_ENDPOINT=  # 已废弃，使用 Hugging Face 替代
FASHIONCLIP_ENDPOINT=  # 已废弃，使用百川大模型替代