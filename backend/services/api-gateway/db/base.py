import datetime
from abc import ABC, abstractmethod
from typing import TypedDict


class UserRecord(TypedDict):
    user_id: str
    username: str
    password_hash: str
    role: str
    staff_id: int | None
    created_at: datetime.datetime


class ChatTurnRecord(TypedDict):
    role: str           # 'user' | 'assistant'
    content: str
    created_at: datetime.datetime


class AbstractChatHistoryStore(ABC):
    """Backend-agnostic store for per-user conversation history."""

    @abstractmethod
    def append(self, session_id: str, user_id: str, role: str, content: str) -> None: ...

    @abstractmethod
    def load_recent(self, session_id: str, limit: int) -> list[ChatTurnRecord]: ...

    @abstractmethod
    def delete_for_user(self, user_id: str) -> int: ...


class AbstractUserStore(ABC):
    """Backend-agnostic store for auth user accounts.

    Implementations must return records keyed by ``user_id`` (string), never
    by a backend-specific identifier like Mongo's ``_id`` or Postgres' ``id``.
    """

    @abstractmethod
    def find_by_username(self, username: str) -> UserRecord | None: ...

    @abstractmethod
    def find_by_id(self, user_id: str) -> UserRecord | None: ...

    @abstractmethod
    def admin_exists(self) -> bool: ...

    @abstractmethod
    def create_user(
        self,
        username: str,
        password_hash: str,
        role: str,
        staff_id: int | None,
    ) -> str: ...
