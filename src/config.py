import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database configuration
    database_url: str = "sqlite:///./workflows.db"

    # Celery configuration (using filesystem broker and SQLite backend)
    celery_broker_url: str = "filesystem://"
    celery_broker_folder: str = "./celery_broker"
    celery_broker_processed_folder: str = "./celery_broker/processed"
    celery_result_backend: str = "db+sqlite:///./celery_results.db"

    # API configuration
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    secret_key: str = "your-secret-key-here"
    api_key: str = "your-api-key-here"

    class Config:
        env_file = ".env"


settings = Settings()

# Ensure Celery broker directories exist
os.makedirs(settings.celery_broker_folder, exist_ok=True)
os.makedirs(settings.celery_broker_processed_folder, exist_ok=True)
os.makedirs(os.path.join(settings.celery_broker_folder, "out"), exist_ok=True)