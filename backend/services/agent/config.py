from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "Phonphai Agent Service"
    PORT: int = 50052
    MAX_TOOL_CALL_ROUNDS: int = 3

    # Upstream Services
    RETRIEVER_HOST: str = "retriever:50051"
    POSTGRES_HOST: str = "postgres"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "phonphai"
    POSTGRES_USER: str = "phonphai"
    POSTGRES_PASSWORD: str = "phonphai"

    # LangSmith Tracing Configuration
    LANGCHAIN_TRACING_V2: str = "true"
    LANGCHAIN_ENDPOINT: str = "https://api.smith.langchain.com"
    LANGCHAIN_API_KEY: str = ""
    LANGCHAIN_PROJECT: str = "phonphai-agent"

    # API Keys
    OPENROUTER_API_KEY: str

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
