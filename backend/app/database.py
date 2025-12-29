from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

from .config import get_settings

settings = get_settings()

# 创建数据库引擎
engine = create_engine(
    settings.database_url,
    echo=settings.database_echo,
    pool_size=settings.database_pool_size,
    pool_recycle=3600,  # 1小时回收连接
    # SQLite专用配置（避免多线程问题）
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {}
)

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 模型基类
Base = declarative_base()

def get_db() -> Session:
    """依赖注入：获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db(engine_override=None) -> None:
    """初始化数据库：导入模型并在目标引擎上创建所有表。

    参数:
        engine_override: 可选的 SQLAlchemy 引擎，用于覆盖模块级 `engine`。
    """
    # 延迟导入所有模型，确保它们在 Base.metadata 中注册
    try:
        from . import models  # noqa: F401
    except Exception:
        # 如果导入失败，不要中断——模型可能已经在别处被导入
        pass

    bind_engine = engine_override or engine
    Base.metadata.create_all(bind=bind_engine)