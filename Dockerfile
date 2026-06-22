# ======================================================
# SmartWardrobe 后端 Docker 镜像
# ======================================================
FROM python:3.13-slim AS builder

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ─── Runtime 阶段 ───
FROM python:3.13-slim AS runtime

WORKDIR /app

# 仅复制运行时所需的系统库
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# 从 builder 阶段复制 Python 包
COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# 复制应用代码
COPY backend/ /app/backend/
COPY config/ /app/config/

# 创建上传目录
RUN mkdir -p /app/backend/uploads /app/backend/data

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
