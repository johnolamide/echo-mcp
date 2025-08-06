from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    PROJECT_NAME: str = "Echo MCP"
    VERSION: str = "1.0.0"
    
    # Database
    DATABASE_URL: str = "sqlite:///./echo_mcp.db"
    
    # Security
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # CORS
    ALLOWED_HOSTS: List[str] = ["*"]
    
    # External APIs (to be configured later)
    FOOD_API_BASE_URL: str = ""
    FOOD_API_KEY: str = ""
    RIDE_API_BASE_URL: str = ""
    RIDE_API_KEY: str = ""
    
    # Redis Configuration
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: str = ""
    REDIS_ENABLED: bool = True
    
    # Cache Configuration
    CACHE_TTL_SECONDS: int = 3600  # 1 hour default TTL
    CHAT_CACHE_TTL_SECONDS: int = 300  # 5 minutes for chat data
    SESSION_CACHE_TTL_SECONDS: int = 1800  # 30 minutes for sessions
    USER_CACHE_TTL_SECONDS: int = 600  # 10 minutes for user data
    
    # Email settings (for auth)
    EMAIL_HOST: str = ""
    EMAIL_PORT: int = 587
    EMAIL_USERNAME: str = ""
    EMAIL_PASSWORD: str = ""
    EMAIL_FROM: str = ""
    
    class Config:
        env_file = ".env"


settings = Settings()
