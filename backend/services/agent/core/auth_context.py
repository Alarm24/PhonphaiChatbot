from contextvars import ContextVar
from dataclasses import dataclass


@dataclass
class RequestAuth:
    role: str  # "admin" | "user" | ""  (empty == anonymous)
    staff_id: int | None
    username: str

    @property
    def is_anonymous(self) -> bool:
        return not self.role

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"


_current_auth: ContextVar[RequestAuth] = ContextVar(
    "current_auth",
    default=RequestAuth(role="", staff_id=None, username=""),
)


def set_current_auth(auth: RequestAuth) -> None:
    _current_auth.set(auth)


def get_current_auth() -> RequestAuth:
    return _current_auth.get()
