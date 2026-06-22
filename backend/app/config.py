import os
from typing import List, Optional
from functools import lru_cache
from pydantic import BaseModel, field_validator
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseModel):
    # ── 应用基础配置 ──
    app_name: str = os.getenv("APP_NAME", "SmartWardrobe")
    environment: str = os.getenv("ENVIRONMENT", "development")
    debug: bool = os.getenv("DEBUG", "True").lower() == "true"

    # ── 日志配置 ──
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    log_file: Optional[str] = os.getenv("LOG_FILE")

    # ── 数据库配置 ──
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./smartwardrobe.db")
    database_echo: bool = os.getenv("DATABASE_ECHO", "False").lower() == "true"
    database_pool_size: int = int(os.getenv("DATABASE_POOL_SIZE", 5))

    # ── JWT 配置（生产环境必须通过环境变量注入密钥） ──
    jwt_secret_key: str = os.getenv("JWT_SECRET_KEY", "")
    jwt_access_token_expire_minutes: int = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", 15))
    jwt_refresh_token_expire_days: int = int(os.getenv("JWT_REFRESH_TOKEN_EXPIRE_DAYS", 7))
    jwt_clock_skew_seconds: int = int(os.getenv("JWT_CLOCK_SKEW_SECONDS", 60))

    # ── CORS 配置 ──
    frontend_origin: str = os.getenv(
        "FRONTEND_ORIGIN",
        "http://localhost:8080,http://127.0.0.1:8080",
    )

    # ── AI 服务配置 ──
    leffa_endpoint: Optional[str] = os.getenv("LEFFA_ENDPOINT")
    leffa_virtual_tryon_url: Optional[str] = os.getenv("LEFFA_VIRTUAL_TRYON_URL")
    huggingface_api_key: Optional[str] = os.getenv("HUGGINGFACE_API_KEY")
    huggingface_leffa_model: str = os.getenv("HUGGINGFACE_LEFFA_MODEL", "facebook/leffa")
    modelscope_model: Optional[str] = os.getenv("MODELSCOPE_MODEL")
    modelscope_api_key: Optional[str] = os.getenv("MODELSCOPE_API_KEY")

    kemi_gateway_base_url: str = os.getenv("KEMI_GATEWAY_BASE_URL", "https://token.xinhankr.com").rstrip("/")
    kemi_gateway_api_key: Optional[str] = os.getenv("KEMI_GATEWAY_API_KEY")
    kemi_tryon_image_model: str = os.getenv("KEMI_TRYON_IMAGE_MODEL", "")
    kemi_tryon_prompt: str = os.getenv(
        "KEMI_TRYON_PROMPT",
        "虚拟试衣：尝试自然穿搭效果，保持人物体型、姿态与参考图一致。",
    )
    kemi_tryon_n: int = int(os.getenv("KEMI_TRYON_N", "1"))
    kemi_tryon_resolution: str = os.getenv("KEMI_TRYON_RESOLUTION", "720p")
    kemi_tryon_aspect_ratio: str = os.getenv("KEMI_TRYON_ASPECT_RATIO", "1:1")
    kemi_tryon_negative_prompt: Optional[str] = os.getenv("KEMI_TRYON_NEGATIVE_PROMPT")
    kemi_tryon_image_fidelity: Optional[str] = os.getenv("KEMI_TRYON_IMAGE_FIDELITY")
    kemi_tryon_callback_url: Optional[str] = os.getenv("KEMI_TRYON_CALLBACK_URL")
    kemi_tryon_duration: int = int(os.getenv("KEMI_TRYON_DURATION", "5"))
    kemi_tryon_images_path: str = os.getenv("KEMI_TRYON_IMAGES_PATH", "/api/v3/images/generations").strip() or "/api/v3/images/generations"
    kemi_tryon_poll_interval_sec: float = float(os.getenv("KEMI_TRYON_POLL_INTERVAL_SEC", "2.0"))
    kemi_tryon_poll_timeout_sec: int = int(os.getenv("KEMI_TRYON_POLL_TIMEOUT_SEC", "300"))
    fashionclip_endpoint: Optional[str] = os.getenv("FASHIONCLIP_ENDPOINT")
    baichuan_api_key: Optional[str] = os.getenv("BAICHUAN_API_KEY")
    baichuan_endpoint: str = os.getenv("BAICHUAN_ENDPOINT", "https://api.baichuan-ai.com/v1/chat/completions")
    baichuan_model: str = os.getenv("BAICHUAN_MODEL", "baichuan2-7b-chat")

    # ── 图片存储配置 ──
    object_storage_type: str = os.getenv("OBJECT_STORAGE_TYPE", "local")
    image_storage_path: str = os.getenv("IMAGE_STORAGE_PATH", "./uploads")
    image_max_size: int = int(os.getenv("IMAGE_MAX_SIZE", 5242880))
    tryon_image_max_size: int = int(os.getenv("TRYON_IMAGE_MAX_SIZE", 20971520))
    image_quality: int = int(os.getenv("IMAGE_QUALITY", 85))

    # ── 天气服务配置 ──
    weather_api_key: Optional[str] = os.getenv("WEATHER_API_KEY")
    weather_endpoint: str = os.getenv("WEATHER_ENDPOINT", "https://api.weatherapi.com/v1/current.json")

    # ── 功能开关 ──
    enable_tryon: bool = os.getenv("ENABLE_TRYON", "False").lower() == "true"
    enable_recommendations: bool = os.getenv("ENABLE_RECOMMENDATIONS", "False").lower() == "true"

    @field_validator("jwt_secret_key")
    def validate_jwt_secret(cls, v: str) -> str:
        if not v or v.strip() == "":
            raise ValueError(
                "JWT_SECRET_KEY 未设置。请通过环境变量注入，"
                "例如：export JWT_SECRET_KEY=$(openssl rand -hex 32)"
            )
        placeholders = [
            "your-secret-key-here",
            "default-test-key-change-in-production",
            "replace-with-your-secret-key-using-openssl-rand-hex-32",
        ]
        if any(p in v.lower() for p in placeholders):
            raise ValueError(
                f"JWT_SECRET_KEY 仍是占位符 '{v[:20]}...'，"
                "请生成真正的密钥并设置环境变量 JWT_SECRET_KEY"
            )
        return v

    def get_cors_origins(self) -> List[str]:
        if not self.frontend_origin:
            return []
        return [origin.strip() for origin in self.frontend_origin.split(",")]

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"

    model_config = {"arbitrary_types_allowed": True}


@lru_cache
def get_settings() -> Settings:
    """获取全局配置实例（带缓存）。"""
    return Settings()
