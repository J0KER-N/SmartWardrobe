import secrets
from functools import lru_cache
from pydantic import HttpUrl, field_validator  # 注意：validator 改为 field_validator
from pydantic_settings import BaseSettings  # 从 pydantic-settings 导入 BaseSettings
from pydantic import ValidationInfo

class Settings(BaseSettings):
    app_name: str = "Smart Wardrobe Backend"
    environment: str = "development"  # development, production, testing
    frontend_origin: HttpUrl | None = None
    debug: bool = False

    # Database configuration
    database_url: str = "sqlite:///./smartwardrobe.db"
    database_pool_size: int = 5
    database_max_overflow: int = 10
    database_pool_timeout: int = 30
    database_echo: bool = False  # SQLAlchemy query logging

    # Redis configuration (for async tasks and caching)
    redis_url: str | None = None
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: str | None = None

    # JWT configuration
    jwt_secret_key: str = "change-me-in-production-use-openssl-rand-hex-32"
    jwt_algorithm: str = "HS256"
    access_token_exp_minutes: int = 60 * 24  # 24 hours
    refresh_token_exp_days: int = 30  # 30 days
    jwt_refresh_secret_key: str | None = None  # Optional separate key for refresh tokens

    # AI Service endpoints
    leffa_endpoint: HttpUrl | None = None
    leffa_timeout: int = 120  # seconds
    fashionclip_endpoint: HttpUrl | None = None
    fashionclip_timeout: int = 60
    baichuan_api_url: HttpUrl | None = None
    baichuan_api_key: str | None = None
    baichuan_model: str = "baichuan-fashion-expert"
    baichuan_timeout: int = 60

    # Weather API
    weather_api_url: HttpUrl | None = None
    weather_api_key: str | None = None
    weather_api_provider: str = "openweathermap"  # openweathermap, qweather, etc.

    # Object Storage configuration
    object_storage_type: str = "local"  # local, s3, oss, qiniu
    object_storage_endpoint: HttpUrl | None = None
    object_storage_bucket: str | None = None
    object_storage_access_key: str | None = None
    object_storage_secret_key: str | None = None
    object_storage_region: str | None = None
    media_root: str = "./media"  # Local storage path

    # Image processing
    max_image_size_mb: int = 10
    allowed_image_formats: list[str] = ["jpg", "jpeg", "png", "webp"]
    image_quality: int = 85  # JPEG quality (1-100)
    image_max_dimension: int = 2048  # Max width/height in pixels

    # Security
    password_min_length: int = 8
    password_require_uppercase: bool = True
    password_require_lowercase: bool = True
    password_require_digits: bool = True
    cors_allow_origins: list[str] = []  # If empty, uses frontend_origin

    # Logging
    log_level: str = "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    log_file: str | None = None  # If None, logs to console
    log_rotation: str = "midnight"  # daily, midnight, etc.
    log_retention_days: int = 30

    # Pagination defaults
    default_page_size: int = 20
    max_page_size: int = 100

    @field_validator("jwt_secret_key")
    @classmethod
    def validate_jwt_secret(cls, v: str, info: ValidationInfo) -> str:
        # Check if environment is production (access from validation context if available)
        # Note: In Pydantic v2, we need to check the model instance after creation
        # For now, we'll just check the length and warn about default value
        if v == "change-me-in-production-use-openssl-rand-hex-32":
            # This will be caught during model instantiation if environment is production
            pass
        if len(v) < 32:
            raise ValueError("JWT secret key must be at least 32 characters long")
        return v

    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        if v not in ["development", "production", "testing"]:
            raise ValueError("environment must be one of: development, production, testing")
        return v

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def is_development(self) -> bool:
        return self.environment == "development"

    def get_cors_origins(self) -> list[str]:
        """Get CORS allowed origins based on configuration."""
        if self.cors_allow_origins:
            return self.cors_allow_origins
        if self.frontend_origin:
            return [str(self.frontend_origin)]
        return []

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
    }


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    # Additional validation after instantiation
    if settings.is_production and settings.jwt_secret_key == "change-me-in-production-use-openssl-rand-hex-32":
        raise ValueError("JWT secret key must be changed in production environment")
    return settings

