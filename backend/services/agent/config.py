from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "Phonphai Agent Service"
    PORT: int = 50052

    # Upstream Services
    RETRIEVER_HOST: str = "retriever:50051"

    # API Keys
    GEMINI_API_KEY: str

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
