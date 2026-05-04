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

    # MongoDB (used when CHAT_HISTORY_BACKEND="mongo")
    MONGO_URI: str = "mongodb://mongo:27017"
    MONGO_DB: str = "rag_db"

    # Chat history
    CHAT_HISTORY_ENABLED: bool = False
    CHAT_HISTORY_BACKEND: str = "mongo"   # "mongo" | "postgres"
    CHAT_HISTORY_WINDOW: int = 10         # max turns per load_conversation_history call
    # Override Postgres DSN for chat history (defaults to constructing from POSTGRES_* vars)
    POSTGRES_CHAT_DSN: str = ""

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
