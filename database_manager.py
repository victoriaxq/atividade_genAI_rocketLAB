import sqlite3
import re
from pathlib import Path
from typing import Any


DB_PATH = Path(__file__).parent / "banco.db"
ALLOWED_STATEMENT = re.compile(r"^\s*SELECT\b", re.IGNORECASE)


class DatabaseManager:
    """Manages the SQLite connection and query execution."""

    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self._validate_path()

    def _validate_path(self) -> None:
        if not self.db_path.exists():
            raise FileNotFoundError(
                f"Database not found at '{self.db_path}'. "
                "Please place 'banco.db' in the project root."
            )

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def get_schema_ddl(self) -> str:
        """Returns the CREATE TABLE DDL for all user tables."""
        with self.get_connection() as conn:
            cursor = conn.execute(
                "SELECT name, sql FROM sqlite_master "
                "WHERE type='table' AND name NOT LIKE 'sqlite_%' "
                "ORDER BY name;"
            )
            rows = cursor.fetchall()

        if not rows:
            return "No tables found in the database."

        return "\n\n".join(f"-- Table: {row['name']}\n{row['sql']};" for row in rows)

    def list_tables(self) -> list[str]:
        """Returns a list of all table names."""
        with self.get_connection() as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type='table' AND name NOT LIKE 'sqlite_%' "
                "ORDER BY name;"
            )
            return [row["name"] for row in cursor.fetchall()]

    def execute_query(self, sql: str) -> dict[str, Any]:
        """
        Executes a SELECT query safely. Returns rows and column names.
        Raises ValueError on non-SELECT statements.
        """
        if not ALLOWED_STATEMENT.match(sql):
            raise ValueError(
                "Only SELECT statements are permitted. "
                f"Received: '{sql[:80]}...'"
            )

        with self.get_connection() as conn:
            try:
                cursor = conn.execute(sql)
                columns = [desc[0] for desc in cursor.description]
                rows = [dict(row) for row in cursor.fetchmany(30)]
                return {"columns": columns, "rows": rows, "count": len(rows)}
            except sqlite3.Error as exc:
                raise RuntimeError(f"SQL execution error: {exc}") from exc
