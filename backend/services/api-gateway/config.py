from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # App Config
    APP_NAME: str = "Phonphai API Gateway"
    CHUNK_SIZE: int = 1024 * 64  # 64KB

    # Microservice Hosts
    RETRIEVER_HOST: str = "retriever:50051"
    AGENT_HOST: str = "agent:50052"

    # User-data backend selection ("mongo" | "postgres")
    USER_DB_BACKEND: str = "mongo"

    # MongoDB (used when USER_DB_BACKEND="mongo"; shared rag_db, `users` collection)
    MONGO_URI: str = "mongodb://mongo:27017"
    MONGO_DB: str = "rag_db"

    # Postgres (used when USER_DB_BACKEND="postgres")
    # Example: postgresql://user:pass@host:5432/auth_db
    POSTGRES_USER_DSN: str = ""

    # Auth
    JWT_SECRET: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRES_HOURS: int = 24 * 7  # 1 week

    # Bootstrap admin (seeded on startup if no admin exists)
    INITIAL_ADMIN_USERNAME: str = ""
    INITIAL_ADMIN_PASSWORD: str = ""

    # Bootstrap regular user (seeded on startup if username doesn't exist)
    INITIAL_USER_USERNAME: str = ""
    INITIAL_USER_PASSWORD: str = ""
    INITIAL_USER_STAFF_ID: int = 0  # 0 = unset / skip seeding

    class Config:
        env_file = ".env"


# @lru_cache ensures the settings are only computed ONCE when the app starts.
# Every subsequent call returns the cached dictionary instantly.
@lru_cache()
def get_settings() -> Settings:
    return Settings()
