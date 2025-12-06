from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from .config import get_settings

settings = get_settings()

# Create engine with connection pool configuration
engine_kwargs = {
    "echo": settings.database_echo,
    "pool_size": settings.database_pool_size,
    "max_overflow": settings.database_max_overflow,
    "pool_timeout": settings.database_pool_timeout,
    "pool_pre_ping": True,  # Verify connections before using
}

# For SQLite, remove pool settings (not supported) and add check_same_thread
if settings.database_url.startswith("sqlite"):
    engine_kwargs.pop("pool_size", None)
    engine_kwargs.pop("max_overflow", None)
    engine_kwargs.pop("pool_timeout", None)
    # SQLite requires check_same_thread=False for multi-threaded use
    engine_kwargs["connect_args"] = {"check_same_thread": False}

engine = create_engine(settings.database_url, **engine_kwargs)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)