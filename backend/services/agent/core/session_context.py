from contextvars import ContextVar

_current_session_id: ContextVar[str] = ContextVar("current_session_id", default="")


def set_current_session_id(session_id: str) -> None:
    _current_session_id.set(session_id)


def get_current_session_id() -> str:
    return _current_session_id.get()
