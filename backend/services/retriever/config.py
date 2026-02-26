from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "Phonphai Retriever Service"
    PORT: int = 50051
    APP_URL: str = "https://github.com/PhonphaiChatbot"

    # Database URIs
    MONGO_URI: str = "mongodb://mongo:27017"
    CHROMA_HOST: str = "chroma"
    EMBEDDING_MODEL_NAME: str = "intfloat/multilingual-e5-large"
    RERANK_MODEL_NAME: str = "BAAI/bge-reranker-v2-m3"
    HYBRID_SEMANTIC_WEIGHT: float = 0.6
    HYBRID_BM25_WEIGHT: float = 0.4
    RETRIEVAL_K: int = 15
    RERANK_TOP_K: int = 5
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200

    OPENROUTER_API_KEY: str = ""

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
