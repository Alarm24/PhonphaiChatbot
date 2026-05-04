import datetime
from abc import ABC, abstractmethod
from typing import TypedDict


class ChatTurnRecord(TypedDict):
    role: str           # 'user' | 'assistant'
    content: str
    created_at: datetime.datetime


class AbstractChatHistoryStore(ABC):
    """Backend-agnostic read interface for conversation history (agent-side)."""

    @abstractmethod
    def load_recent(self, session_id: str, limit: int) -> list[ChatTurnRecord]: ...

    @abstractmethod
    def delete_for_user(self, user_id: str) -> int: ...


class MongoChatHistoryStore(AbstractChatHistoryStore):
    """MongoDB-backed read store for conversation history."""

    def __init__(self, uri: str, db_name: str):
        from pymongo import ASCENDING, DESCENDING, MongoClient
        self._col = MongoClient(uri)[db_name]["chat_messages"]
        self._col.create_index([("session_id", ASCENDING), ("created_at", ASCENDING)])

    def load_recent(self, session_id: str, limit: int) -> list[ChatTurnRecord]:
        docs = list(
            self._col.find({"session_id": session_id})
            .sort("created_at", -1)
            .limit(limit)
        )
        docs.reverse()
        return [
            ChatTurnRecord(role=d["role"], content=d["content"], created_at=d["created_at"])
            for d in docs
        ]

    def delete_for_user(self, user_id: str) -> int:
        result = self._col.delete_many({"user_id": user_id})
        return result.deleted_count


class PostgresChatHistoryStore(AbstractChatHistoryStore):
    """Postgres-backed read store for conversation history."""

    def __init__(self, dsn: str):
        if not dsn:
            raise ValueError(
                "Chat history Postgres DSN is empty. Set POSTGRES_CHAT_DSN or "
                "POSTGRES_* variables when CHAT_HISTORY_BACKEND=postgres."
            )
        self._dsn = dsn

    def load_recent(self, session_id: str, limit: int) -> list[ChatTurnRecord]:
        from psycopg import connect
        with connect(self._dsn) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT role, content, created_at FROM ("
                    "  SELECT role, content, created_at"
                    "  FROM chat_messages WHERE session_id = %s"
                    "  ORDER BY created_at DESC LIMIT %s"
                    ") sub ORDER BY created_at ASC",
                    (session_id, limit),
                )
                rows = cur.fetchall()
        return [
            ChatTurnRecord(role=row[0], content=row[1], created_at=row[2])
            for row in rows
        ]

    def delete_for_user(self, user_id: str) -> int:
        from psycopg import connect
        with connect(self._dsn) as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM chat_messages WHERE user_id = %s", (user_id,))
                return cur.rowcount


def make_chat_history_store(settings) -> AbstractChatHistoryStore:
    backend = settings.CHAT_HISTORY_BACKEND.strip().lower()
    if backend == "mongo":
        return MongoChatHistoryStore(uri=settings.MONGO_URI, db_name=settings.MONGO_DB)
    if backend == "postgres":
        dsn = settings.POSTGRES_CHAT_DSN or (
            f"postgresql://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}"
            f"@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"
        )
        return PostgresChatHistoryStore(dsn=dsn)
    raise ValueError(
        f"Unsupported CHAT_HISTORY_BACKEND: {settings.CHAT_HISTORY_BACKEND!r}. "
        "Supported values: 'mongo', 'postgres'."
    )
