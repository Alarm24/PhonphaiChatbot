from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "Phonphai Retriever Service"
    PORT: int = 50051

    # Database URIs
    MONGO_URI: str = "mongodb://mongo:27017"
    CHROMA_HOST: str = "chroma"

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
