"""
Application Configuration Management
Centralized configuration with validation and environment support
"""
import os
from typing import Optional
from pydantic import BaseSettings, validator, Field
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    """Application settings with validation"""
    
    # Application
    APP_NAME: str = "SkateIQ"
    APP_VERSION: str = "3.0.0"
    ENVIRONMENT: str = Field(default="development", env="ENVIRONMENT")
    DEBUG: bool = Field(default=False, env="DEBUG")
    PORT: int = Field(default=8001, env="PORT")
    
    # Database
    DATABASE_URL: str = Field(..., env="DATABASE_URL")
    DATABASE_POOL_SIZE: int = Field(default=5, env="DATABASE_POOL_SIZE")
    DATABASE_MAX_OVERFLOW: int = Field(default=10, env="DATABASE_MAX_OVERFLOW")
    DATABASE_POOL_TIMEOUT: int = Field(default=30, env="DATABASE_POOL_TIMEOUT")
    
    # Security
    SECRET_KEY: str = Field(..., env="SECRET_KEY")
    JWT_SECRET_KEY: str = Field(..., env="JWT_SECRET_KEY")
    JWT_ALGORITHM: str = Field(default="HS256", env="JWT_ALGORITHM")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=10080, env="ACCESS_TOKEN_EXPIRE_MINUTES")  # 7 days
    
    # OpenAI
    OPENAI_API_KEY: str = Field(..., env="OPENAI_API_KEY")
    OPENAI_MODEL: str = Field(default="gpt-4o", env="OPENAI_MODEL")
    OPENAI_MAX_TOKENS: int = Field(default=1500, env="OPENAI_MAX_TOKENS")
    OPENAI_TEMPERATURE: float = Field(default=0.7, env="OPENAI_TEMPERATURE")
    
    # API Configuration
    NHL_API_BASE: str = Field(default="https://api-web.nhle.com/v1", env="NHL_API_BASE")
    MONEYPUCK_BASE: str = Field(default="https://moneypuck.com", env="MONEYPUCK_BASE")
    API_REQUEST_TIMEOUT: int = Field(default=15, env="API_REQUEST_TIMEOUT")
    API_MAX_RETRIES: int = Field(default=3, env="API_MAX_RETRIES")
    
    # Caching
    CACHE_TTL_HOURS: int = Field(default=6, env="CACHE_TTL_HOURS")
    CACHE_MAX_SIZE: int = Field(default=1000, env="CACHE_MAX_SIZE")
    
    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = Field(default=True, env="RATE_LIMIT_ENABLED")
    RATE_LIMIT_REQUESTS: int = Field(default=100, env="RATE_LIMIT_REQUESTS")
    RATE_LIMIT_WINDOW_SECONDS: int = Field(default=60, env="RATE_LIMIT_WINDOW_SECONDS")
    
    # CORS
    CORS_ORIGINS: list = Field(default=["*"], env="CORS_ORIGINS")
    CORS_ALLOW_CREDENTIALS: bool = Field(default=True, env="CORS_ALLOW_CREDENTIALS")
    
    # Logging
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    LOG_FILE: Optional[str] = Field(default=None, env="LOG_FILE")
    LOG_FORMAT: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        env="LOG_FORMAT"
    )
    
    # Live Scores
    LIVE_SCORE_UPDATE_INTERVAL: int = Field(default=30, env="LIVE_SCORE_UPDATE_INTERVAL")
    LIVE_SCORE_ENABLED: bool = Field(default=True, env="LIVE_SCORE_ENABLED")
    
    # Game Result Scraper
    SCRAPER_RUN_TIME: str = Field(default="02:00", env="SCRAPER_RUN_TIME")
    SCRAPER_ENABLED: bool = Field(default=True, env="SCRAPER_ENABLED")
    
    @validator("DATABASE_URL")
    def validate_database_url(cls, v):
        """Validate and fix database URL format"""
        if v.startswith("postgres://"):
            return v.replace("postgres://", "postgresql://", 1)
        return v
    
    @validator("ENVIRONMENT")
    def validate_environment(cls, v):
        """Validate environment value"""
        allowed = ["development", "staging", "production", "testing"]
        if v not in allowed:
            raise ValueError(f"ENVIRONMENT must be one of {allowed}")
        return v
    
    @validator("LOG_LEVEL")
    def validate_log_level(cls, v):
        """Validate log level"""
        allowed = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        v = v.upper()
        if v not in allowed:
            raise ValueError(f"LOG_LEVEL must be one of {allowed}")
        return v
    
    @property
    def is_production(self) -> bool:
        """Check if running in production"""
        return self.ENVIRONMENT == "production"
    
    @property
    def is_development(self) -> bool:
        """Check if running in development"""
        return self.ENVIRONMENT == "development"
    
    @property
    def is_testing(self) -> bool:
        """Check if running in testing"""
        return self.ENVIRONMENT == "testing"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get application settings"""
    return settings
