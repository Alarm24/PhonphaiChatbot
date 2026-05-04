from uuid import UUID

from psycopg_pool import ConnectionPool

from db.base import AbstractChatHistoryStore, AbstractUserStore, ChatTurnRecord, UserRecord

_SCHEMA_SQL = """
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS auth_users (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  username      TEXT NOT NULL,
  password_hash TEXT NOT NULL,
  role          TEXT NOT NULL CHECK (role IN ('admin', 'user')),
  staff_id      INTEGER,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS auth_users_username_uniq ON auth_users (username);
"""

_SELECT_COLUMNS = (
    "id::text AS user_id, username, password_hash, role, staff_id, created_at"
)


class PostgresUserStore(AbstractUserStore):
    """Postgres-backed store for auth user accounts."""

    def __init__(self, dsn: str):
        if not dsn:
            raise ValueError(
                "POSTGRES_USER_DSN is empty. Set it when USER_DB_BACKEND=postgres."
            )
        self.pool = ConnectionPool(conninfo=dsn, min_size=1, max_size=5, open=True)
        with self.pool.connection() as conn:
            conn.execute(_SCHEMA_SQL)

    def find_by_username(self, username: str) -> UserRecord | None:
        with self.pool.connection() as conn:
            row = conn.execute(
                f"SELECT {_SELECT_COLUMNS} FROM auth_users WHERE username = %s",
                (username,),
                prepare=True,
            ).fetchone()
        return self._to_record(row) if row else None

    def find_by_id(self, user_id: str) -> UserRecord | None:
        try:
            uid = UUID(user_id)
        except (ValueError, TypeError):
            return None
        with self.pool.connection() as conn:
            row = conn.execute(
                f"SELECT {_SELECT_COLUMNS} FROM auth_users WHERE id = %s",
                (uid,),
                prepare=True,
            ).fetchone()
        return self._to_record(row) if row else None

    def admin_exists(self) -> bool:
        with self.pool.connection() as conn:
            row = conn.execute(
                "SELECT 1 FROM auth_users WHERE role = 'admin' LIMIT 1"
            ).fetchone()
        return row is not None

    def create_user(
        self,
        username: str,
        password_hash: str,
        role: str,
        staff_id: int | None,
    ) -> str:
        with self.pool.connection() as conn:
            row = conn.execute(
                "INSERT INTO auth_users (username, password_hash, role, staff_id) "
                "VALUES (%s, %s, %s, %s) RETURNING id::text",
                (username, password_hash, role, staff_id),
            ).fetchone()
        return row[0]

    @staticmethod
    def _to_record(row) -> UserRecord:
        # psycopg returns tuples by default; columns are positional per _SELECT_COLUMNS.
        return {
            "user_id": row[0],
            "username": row[1],
            "password_hash": row[2],
            "role": row[3],
            "staff_id": row[4],
            "created_at": row[5],
        }


_CHAT_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS chat_messages (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id  TEXT NOT NULL,
  user_id     TEXT NOT NULL,
  role        TEXT NOT NULL CHECK (role IN ('user','assistant')),
  content     TEXT NOT NULL,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS chat_messages_session_idx
  ON chat_messages (session_id, created_at);
CREATE INDEX IF NOT EXISTS chat_messages_user_idx
  ON chat_messages (user_id);
"""


class PostgresChatHistoryStore(AbstractChatHistoryStore):
    """Postgres-backed store for conversation history."""

    def __init__(self, dsn: str):
        if not dsn:
            raise ValueError(
                "POSTGRES_USER_DSN is empty. Set it when CHAT_HISTORY_BACKEND=postgres."
            )
        self.pool = ConnectionPool(conninfo=dsn, min_size=1, max_size=5, open=True)
        with self.pool.connection() as conn:
            conn.execute(_CHAT_SCHEMA_SQL)

    def append(self, session_id: str, user_id: str, role: str, content: str) -> None:
        with self.pool.connection() as conn:
            conn.execute(
                "INSERT INTO chat_messages (session_id, user_id, role, content) "
                "VALUES (%s, %s, %s, %s)",
                (session_id, user_id, role, content),
            )

    def load_recent(self, session_id: str, limit: int) -> list[ChatTurnRecord]:
        with self.pool.connection() as conn:
            rows = conn.execute(
                "SELECT role, content, created_at FROM ("
                "  SELECT role, content, created_at"
                "  FROM chat_messages WHERE session_id = %s"
                "  ORDER BY created_at DESC LIMIT %s"
                ") sub ORDER BY created_at ASC",
                (session_id, limit),
            ).fetchall()
        return [
            ChatTurnRecord(role=row[0], content=row[1], created_at=row[2])
            for row in rows
        ]

    def delete_for_user(self, user_id: str) -> int:
        with self.pool.connection() as conn:
            result = conn.execute(
                "DELETE FROM chat_messages WHERE user_id = %s",
                (user_id,),
            )
        return result.rowcount
