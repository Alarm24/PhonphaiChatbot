from config import Settings

from db.base import AbstractChatHistoryStore, AbstractUserStore, ChatTurnRecord, UserRecord


def make_user_store(settings: Settings) -> AbstractUserStore:
    backend = settings.USER_DB_BACKEND.strip().lower()
    if backend == "mongo":
        from db.mongo import MongoUserStore

        return MongoUserStore(uri=settings.MONGO_URI, db_name=settings.MONGO_DB)
    if backend == "postgres":
        from db.postgres import PostgresUserStore

        return PostgresUserStore(dsn=settings.POSTGRES_USER_DSN)
    raise ValueError(
        f"Unsupported USER_DB_BACKEND: {settings.USER_DB_BACKEND!r}. "
        "Supported values: 'mongo', 'postgres'."
    )


def make_chat_history_store(settings: Settings) -> AbstractChatHistoryStore:
    backend = settings.CHAT_HISTORY_BACKEND.strip().lower()
    if backend == "mongo":
        from db.mongo import MongoChatHistoryStore

        return MongoChatHistoryStore(uri=settings.MONGO_URI, db_name=settings.MONGO_DB)
    if backend == "postgres":
        from db.postgres import PostgresChatHistoryStore

        return PostgresChatHistoryStore(dsn=settings.POSTGRES_USER_DSN)
    raise ValueError(
        f"Unsupported CHAT_HISTORY_BACKEND: {settings.CHAT_HISTORY_BACKEND!r}. "
        "Supported values: 'mongo', 'postgres'."
    )


__all__ = [
    "AbstractUserStore",
    "UserRecord",
    "make_user_store",
    "AbstractChatHistoryStore",
    "ChatTurnRecord",
    "make_chat_history_store",
]
