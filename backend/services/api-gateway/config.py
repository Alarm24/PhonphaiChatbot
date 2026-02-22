from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # App Config
    APP_NAME: str = "Phonphai API Gateway"
    CHUNK_SIZE: int = 1024 * 64  # 64KB

    # Microservice Hosts
    RETRIEVER_HOST: str = "retriever:50051"
    AGENT_HOST: str = "agent:50052"

    class Config:
        env_file = ".env"


# @lru_cache ensures the settings are only computed ONCE when the app starts.
# Every subsequent call returns the cached dictionary instantly.
@lru_cache()
def get_settings() -> Settings:
    return Settings()
