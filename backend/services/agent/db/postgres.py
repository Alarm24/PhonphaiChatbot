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

    def find_ticket_by_code(
        self,
        ticket_code: str,
        staff_id: int | None = None,
    ) -> list[dict]:
        """Look up ticket by code. If staff_id is given, only return rows owned by that user."""
        normalized_code = ticket_code.strip().upper()
        if not normalized_code:
            return []

        params: dict = {"ticket_code": normalized_code}
        owner_clause = ""
        if staff_id is not None:
            owner_clause = 'AND "user" = %(staff_id)s'
            params["staff_id"] = staff_id

        query = f"""
            SELECT
                code,
                issue_id,
                "user",
                status,
                process_level,
                updated_date
            FROM issue_logs
            WHERE code = %(ticket_code)s
            {owner_clause}
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
                cur.execute(query, params)
                rows = cur.fetchall()

        return [
            {
                **row,
                "updated_date": row["updated_date"].isoformat()
                    if row.get("updated_date")
                    else None,
            }
            for row in rows
        ]

    def find_tickets_by_suffix(
        self,
        ticket_suffix: str,
        staff_id: int | None = None,
    ) -> list[dict]:
        """Look up latest rows for tickets whose last 4 code digits match the suffix."""
        normalized_suffix = ticket_suffix.strip()
        if not normalized_suffix or len(normalized_suffix) != 4 or not normalized_suffix.isdigit():
            return []

        params: dict = {"ticket_suffix": normalized_suffix}
        owner_clause = ""
        if staff_id is not None:
            owner_clause = 'AND "user" = %(staff_id)s'
            params["staff_id"] = staff_id

        query = f"""
            SELECT DISTINCT ON (code)
                code,
                issue_id,
                "user",
                status,
                process_level,
                updated_date
            FROM issue_logs
            WHERE substring(code from '.{{4}}$') = %(ticket_suffix)s
            {owner_clause}
            ORDER BY
                code,
                updated_date DESC NULLS LAST,
                issue_id DESC NULLS LAST,
                "user" DESC NULLS LAST,
                status,
                process_level
        """

        with connect(self._conninfo, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                rows = cur.fetchall()

        return [
            {
                **row,
                "updated_date": row["updated_date"].isoformat()
                    if row.get("updated_date")
                    else None,
            }
            for row in rows
        ]

    def find_tickets_by_year(
        self,
        ticket_year: str,
        staff_id: int | None = None,
    ) -> list[dict]:
        """Look up latest rows for tickets whose BE year segment matches the year."""
        normalized_year = ticket_year.strip()
        if not normalized_year or len(normalized_year) != 4 or not normalized_year.isdigit():
            return []

        params: dict = {"ticket_year": normalized_year}
        owner_clause = ""
        if staff_id is not None:
            owner_clause = 'AND "user" = %(staff_id)s'
            params["staff_id"] = staff_id

        query = f"""
            SELECT DISTINCT ON (code)
                code,
                issue_id,
                "user",
                status,
                process_level,
                updated_date
            FROM issue_logs
            WHERE substring(code from '^[A-Z]{{3}}-([0-9]{{4}})-[0-9]{{4}}$') = %(ticket_year)s
            {owner_clause}
            ORDER BY
                code,
                updated_date DESC NULLS LAST,
                issue_id DESC NULLS LAST,
                "user" DESC NULLS LAST,
                status,
                process_level
        """

        with connect(self._conninfo, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                rows = cur.fetchall()

        return [
            {
                **row,
                "updated_date": row["updated_date"].isoformat()
                    if row.get("updated_date")
                    else None,
            }
            for row in rows
        ]

    def find_tickets_by_year_and_suffix(
        self,
        ticket_year: str,
        ticket_suffix: str,
        staff_id: int | None = None,
    ) -> list[dict]:
        """Look up latest rows for tickets matching BE year and last 4 code digits."""
        normalized_year = ticket_year.strip()
        normalized_suffix = ticket_suffix.strip()
        if not normalized_year or len(normalized_year) != 4 or not normalized_year.isdigit():
            return []
        if not normalized_suffix or len(normalized_suffix) != 4 or not normalized_suffix.isdigit():
            return []

        params: dict = {
            "ticket_year": normalized_year,
            "ticket_suffix": normalized_suffix,
        }
        owner_clause = ""
        if staff_id is not None:
            owner_clause = 'AND "user" = %(staff_id)s'
            params["staff_id"] = staff_id

        query = f"""
            SELECT DISTINCT ON (code)
                code,
                issue_id,
                "user",
                status,
                process_level,
                updated_date
            FROM issue_logs
            WHERE substring(code from '^[A-Z]{{3}}-([0-9]{{4}})-[0-9]{{4}}$') = %(ticket_year)s
            AND substring(code from '.{{4}}$') = %(ticket_suffix)s
            {owner_clause}
            ORDER BY
                code,
                updated_date DESC NULLS LAST,
                issue_id DESC NULLS LAST,
                "user" DESC NULLS LAST,
                status,
                process_level
        """

        with connect(self._conninfo, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                rows = cur.fetchall()

        return [
            {
                **row,
                "updated_date": row["updated_date"].isoformat()
                    if row.get("updated_date")
                    else None,
            }
            for row in rows
        ]

    def list_ticket_codes(self, staff_id: int | None = None) -> list[str]:
        """Return distinct ticket codes. If staff_id is given, only return that user's tickets."""
        params: dict = {}
        owner_clause = ""
        if staff_id is not None:
            owner_clause = 'WHERE "user" = %(staff_id)s'
            params["staff_id"] = staff_id

        query = f"""
            SELECT DISTINCT code
            FROM issue_logs
            {owner_clause}
            ORDER BY code
        """

        with connect(self._conninfo, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                rows = cur.fetchall()

        return [row["code"] for row in rows]
