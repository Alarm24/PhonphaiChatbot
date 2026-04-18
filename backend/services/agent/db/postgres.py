from psycopg import connect
from psycopg.rows import dict_row


class PostgresTicketStore:
    def __init__(
        self,
        host: str,
        port: int,
        database: str,
        user: str,
        password: str,
    ):
        self._conninfo = (
            f"host={host} port={port} dbname={database} user={user} password={password}"
        )

    def ping(self) -> None:
        with connect(self._conninfo) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                cur.fetchone()

    def find_ticket_by_code(self, ticket_code: str) -> list[dict]:
        normalized_code = ticket_code.strip().upper()
        if not normalized_code:
            return []

        query = """
            SELECT DISTINCT
                code,
                issue_id,
                "user",
                status,
                process_level
            FROM issue_logs
            WHERE code = %(ticket_code)s
            ORDER BY
                updated_date DESC NULLS LAST,
                issue_id DESC NULLS LAST,
                "user" DESC NULLS LAST,
                status,
                process_level
            LIMIT 1
        """

        with connect(self._conninfo, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(query, {"ticket_code": normalized_code})
                rows = cur.fetchall()

        return [dict(row) for row in rows]
