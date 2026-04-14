"""
tqf_system/migrations/runner.py
Versioned migration runner for TQF System

Strategy:
- Reads .sql files from this directory in alphabetical order (001_*, 002_*, ...)
- Tracks applied migrations in `schema_migrations` table
- Auto-backups the DB before applying any new migrations
- On legacy upgrade: if schema_migrations doesn't exist, marks 001_baseline as
  already applied (init_db() already ran equivalent DDL), then continues from 002+
"""

import os
import re
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

MIGRATIONS_DIR = Path(__file__).parent

# Migrations that existed before this runner was introduced.
# They are pre-applied on legacy DBs that already have the baseline schema.
LEGACY_MIGRATIONS = {"001_baseline"}


def _backup_db(db_path: str) -> str:
    """Copy DB to backups/ subfolder. Returns backup path."""
    db_file = Path(db_path)
    backup_dir = db_file.parent / "backups"
    backup_dir.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_path = backup_dir / f"{db_file.stem}_{ts}.db"
    shutil.copy2(db_path, backup_path)
    return str(backup_path)


def _get_applied(conn: sqlite3.Connection) -> set[str]:
    rows = conn.execute("SELECT version FROM schema_migrations").fetchall()
    return {r[0] for r in rows}


def _mark_applied(conn: sqlite3.Connection, version: str) -> None:
    conn.execute(
        "INSERT OR IGNORE INTO schema_migrations (version) VALUES (?)",
        (version,),
    )


def _is_legacy_db(conn: sqlite3.Connection) -> bool:
    """True if this looks like an existing DB (curricula table exists)."""
    tables = {
        r[0]
        for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    return "curricula" in tables


def _split_statements(sql: str) -> list[str]:
    """Split SQL file into individual statements, stripping comments."""
    statements = []
    current: list[str] = []
    for line in sql.splitlines():
        stripped = line.strip()
        if stripped.startswith("--"):
            continue
        current.append(line)
        if stripped.endswith(";"):
            stmt = "\n".join(current).strip()
            if stmt:
                statements.append(stmt)
            current = []
    return statements


def _execute_migration(conn: sqlite3.Connection, sql: str) -> None:
    """Execute a migration SQL file statement-by-statement.

    ALTER TABLE ADD COLUMN raises OperationalError('duplicate column name: ...')
    when the column already exists (can happen if a migration was partially applied
    and retried). We skip that specific error so the migration can be safely re-run.
    """
    for stmt in _split_statements(sql):
        try:
            conn.execute(stmt)
        except sqlite3.OperationalError as exc:
            msg = str(exc).lower()
            if "duplicate column name" in msg:
                # Column was already added (partial re-run) — skip safely
                print(f"[migrations]   skip (already exists): {stmt[:60].strip()}")
            else:
                raise


def _list_pending(conn: sqlite3.Connection) -> list[tuple[str, Path]]:
    """Return list of (version, sql_path) for migrations not yet applied."""
    applied = _get_applied(conn)
    pending = []
    for sql_file in sorted(MIGRATIONS_DIR.glob("*.sql")):
        version = sql_file.stem  # e.g. "001_baseline"
        if version not in applied:
            pending.append((version, sql_file))
    return pending


def run_migrations(db_path: str) -> None:
    """
    Apply all pending migrations to the given SQLite DB.
    Safe to call on every startup — already-applied migrations are skipped.
    """
    conn = sqlite3.connect(db_path, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=OFF")  # allow table rebuilds during migrations

    try:
        # Bootstrap: create schema_migrations if it doesn't exist yet
        first_run = False
        tables = {
            r[0]
            for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        if "schema_migrations" not in tables:
            first_run = True
            conn.execute("""
                CREATE TABLE schema_migrations (
                    version    TEXT PRIMARY KEY,
                    applied_at TEXT DEFAULT (datetime('now','localtime'))
                )
            """)
            conn.commit()

            # Legacy upgrade: pre-apply baseline for existing DBs
            if _is_legacy_db(conn):
                for legacy in LEGACY_MIGRATIONS:
                    _mark_applied(conn, legacy)
                conn.commit()
                print("[migrations] Legacy DB detected — baseline marked as applied")

        pending = _list_pending(conn)

        if not pending:
            return  # nothing to do

        # Backup before touching anything
        backup_path = _backup_db(db_path)
        print(f"[migrations] Backup created: {backup_path}")

        for version, sql_file in pending:
            sql = sql_file.read_text(encoding="utf-8")
            print(f"[migrations] Applying {version} ...")
            try:
                _execute_migration(conn, sql)
                _mark_applied(conn, version)
                conn.commit()
                print(f"[migrations] OK {version}")
            except Exception as exc:
                conn.rollback()
                raise RuntimeError(
                    f"Migration {version} failed: {exc}\n"
                    f"DB restored from backup at {backup_path}"
                ) from exc

    finally:
        conn.execute("PRAGMA foreign_keys=ON")
        conn.close()
