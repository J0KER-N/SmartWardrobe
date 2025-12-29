import logging
import sys
from contextlib import asynccontextmanager
from typing import Dict

from fastapi import FastAPI, status, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from .config import get_settings
from .database import engine, Base
from .routers import auth, wardrobe, records, profile

# 加载配置
settings = get_settings()

# 配置日志
def setup_logging():
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)
    
    handlers = [logging.StreamHandler(sys.stdout)]
    if settings.log_file:
        from logging.handlers import RotatingFileHandler
        file_handler = RotatingFileHandler(
            settings.log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5
        )
        handlers.append(file_handler)
    
    logging.basicConfig(level=log_level, format=log_format, handlers=handlers)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.WARNING if not settings.database_echo else logging.INFO
    )

setup_logging()
logger = logging.getLogger(__name__)

# 应用生命周期
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时初始化
    logger.info(f"启动 {settings.app_name} | 环境: {settings.environment}")
    # 创建数据库表
    Base.metadata.create_all(bind=engine)
    logger.info("数据库表初始化完成")
    yield
    # 关闭时清理
    logger.info("应用已关闭")

# 创建FastAPI应用
app = FastAPI(
    title=settings.app_name,
    description="智能衣橱系统后端API",
    version="1.0.0",
    lifespan=lifespan,
    debug=settings.debug
)

# 配置CORS
cors_origins = settings.get_cors_origins()
if cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )
    logger.info(f"CORS已启用 | 允许的源: {cors_origins}")

# 注册路由
app.include_router(auth.router)
app.include_router(wardrobe.router)

# 可选路由：仅在配置中开启时导入并注册，避免在本地启动时触发外部调用
if settings.enable_tryon:
    from .routers import tryon as tryon_router
    app.include_router(tryon_router.router)
else:
    logger.info("tryon 路由已禁用（ENABLE_TRYON=False）")

if settings.enable_recommendations:
    from .routers import recommendations as recommendations_router
    app.include_router(recommendations_router.router)
else:
    logger.info("recommendations 路由已禁用（ENABLE_RECOMMENDATIONS=False）")

app.include_router(records.router)
app.include_router(profile.router)

# 健康检查接口
@app.get("/health", tags=["健康检查"])
def health_check() -> Dict[str, str]:
    """基础健康检查"""
    return {"status": "ok", "environment": settings.environment}

@app.get("/health/detailed", tags=["健康检查"])
def detailed_health_check() -> Dict:
    """详细健康检查"""
    health_status = {
        "status": "ok",
        "environment": settings.environment,
        "checks": {
            "database": "unknown",
            "ai_services": {
                "leffa": "未配置" if not settings.leffa_endpoint else "已配置",
                "fashionclip": "未配置" if not settings.fashionclip_endpoint else "已配置"
            }
        }
    }
    
    # 检查数据库
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        health_status["checks"]["database"] = "健康"
    except Exception as e:
        health_status["checks"]["database"] = f"异常: {str(e)}"
        health_status["status"] = "degraded"
    
    return health_status

# 全局异常处理
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """全局异常捕获"""
    logger.error(f"未处理异常: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "message": "服务器内部错误" if settings.is_production else str(exc)
        }
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug
    )