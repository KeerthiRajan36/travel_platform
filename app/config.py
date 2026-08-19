from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):

    APP_NAME: str = "Travel & Tour Operations Management Platform"
    ENV: str = "development"
    DEBUG: bool = True

    DATABASE_URL: str = "sqlite:///./travel.db"


    SECRET_KEY: str = "SECRETKEY@321"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    CORS_ORIGINS: str = "*"


    REDIS_URL: str | None = None
    DASHBOARD_CACHE_TTL_SECONDS: int = 30


    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW_SECONDS: int = 60

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
