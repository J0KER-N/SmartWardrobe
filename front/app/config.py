import os
from typing import List, Optional
from pydantic import BaseModel, field_validator
from dotenv import load_dotenv

# 加载.env文件
load_dotenv()

class Settings(BaseModel):
    # 应用基础配置
    app_name: str = os.getenv("APP_NAME", "SmartWardrobe")
    environment: str = os.getenv("ENVIRONMENT", "development")
    debug: bool = os.getenv("DEBUG", "True").lower() == "true"
    
    # 日志配置
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    log_file: Optional[str] = os.getenv("LOG_FILE")
    
    # 数据库配置
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./smartwardrobe.db")
    database_echo: bool = os.getenv("DATABASE_ECHO", "False").lower() == "true"
    database_pool_size: int = int(os.getenv("DATABASE_POOL_SIZE", 5))
    
    # JWT配置
    jwt_secret_key: str = os.getenv("JWT_SECRET_KEY", "default-test-key-change-in-production")
    jwt_access_token_expire_minutes: int = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", 15))
    jwt_refresh_token_expire_days: int = int(os.getenv("JWT_REFRESH_TOKEN_EXPIRE_DAYS", 7))
    # 时钟偏差（秒），用于在 JWT 验证时允许少量时间同步误差
    jwt_clock_skew_seconds: int = int(os.getenv("JWT_CLOCK_SKEW_SECONDS", 60))
    
    # CORS配置
    frontend_origin: str = os.getenv("FRONTEND_ORIGIN", "http://localhost:8080")
    
    # AI服务配置
    leffa_endpoint: Optional[str] = os.getenv("LEFFA_ENDPOINT")  # 保留用于兼容性
    # 自建 Leffa 虚拟试穿服务（如果配置，则优先使用该服务）
    # 例如：http://your-server:8000/virtual_tryon
    leffa_virtual_tryon_url: Optional[str] = os.getenv("LEFFA_VIRTUAL_TRYON_URL")
    huggingface_api_key: Optional[str] = os.getenv("HUGGINGFACE_API_KEY")  # Hugging Face API Key
    huggingface_leffa_model: str = os.getenv("HUGGINGFACE_LEFFA_MODEL", "facebook/leffa")  # 虚拟试衣模型ID（默认使用 facebook/leffa，支持 Inference API）
    # 魔搭模型配置（国内可用）
    modelscope_model: Optional[str] = os.getenv("MODELSCOPE_MODEL")  # 魔搭模型ID，例如：damo/cv_unet_virtual-try-on-idm-vton
    modelscope_api_key: Optional[str] = os.getenv("MODELSCOPE_API_KEY")  # 魔搭 API Key
    fashionclip_endpoint: Optional[str] = os.getenv("FASHIONCLIP_ENDPOINT")
    baichuan_api_key: Optional[str] = os.getenv("BAICHUAN_API_KEY")
    baichuan_endpoint: str = os.getenv("BAICHUAN_ENDPOINT", "https://api.baichuan-ai.com/v1/chat/completions")
    # Baichuan 模型配置（可在 .env 中设置具体模型名）
    baichuan_model: str = os.getenv("BAICHUAN_MODEL", "baichuan2-7b-chat")
    
    # 图片存储配置
    object_storage_type: str = os.getenv("OBJECT_STORAGE_TYPE", "local")
    image_storage_path: str = os.getenv("IMAGE_STORAGE_PATH", "./uploads")
    image_max_size: int = int(os.getenv("IMAGE_MAX_SIZE", 5242880))  # 5MB（普通图片）
    tryon_image_max_size: int = int(os.getenv("TRYON_IMAGE_MAX_SIZE", 20971520))  # 20MB（试衣用户照片，符合Leffa标准）
    image_quality: int = int(os.getenv("IMAGE_QUALITY", 85))
    
    # 天气服务配置
    weather_api_key: Optional[str] = os.getenv("WEATHER_API_KEY")
    weather_endpoint: str = os.getenv("WEATHER_ENDPOINT", "https://api.weatherapi.com/v1/current.json")
    # 可选功能开关（用于本地运行时关闭依赖外部AI的功能）
    enable_tryon: bool = os.getenv("ENABLE_TRYON", "False").lower() == "true"
    enable_recommendations: bool = os.getenv("ENABLE_RECOMMENDATIONS", "False").lower() == "true"

    @field_validator("jwt_secret_key")
    def validate_jwt_secret(cls, v):
        if v == "default-test-key-change-in-production" and cls.environment == "production":
            raise ValueError("JWT_SECRET_KEY must be changed in production")
        return v

    def get_cors_origins(self) -> List[str]:
        """解析CORS允许的域名列表"""
        if not self.frontend_origin:
            return []
        return [origin.strip() for origin in self.frontend_origin.split(",")]

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"

def get_settings() -> Settings:
    """获取全局配置实例"""
    return Settings()