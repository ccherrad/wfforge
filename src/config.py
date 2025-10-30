from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "sqlite:///./workflows.db"
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/0"
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    secret_key: str = "your-secret-key-here"
    api_key: str = "your-api-key-here"

    class Config:
        env_file = ".env"


settings = Settings()