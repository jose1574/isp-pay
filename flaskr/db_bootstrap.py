from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any

from flask import current_app
from sqlalchemy import text


@dataclass(frozen=True)
class MigrationFile:
    key: str
    checksum: str
    sql: str


def _read_schema_sql() -> str:
    schema_path = Path(__file__).with_name("schema.sql")
    return schema_path.read_text(encoding="utf-8")


def _run_sql_script(db: Any, sql_script: str) -> None:
    # Use a DB-API cursor to execute multi-statement scripts (DO $$ blocks included).
    raw_conn = db.engine.raw_connection()
    try:
        with raw_conn.cursor() as cursor:
            cursor.execute(sql_script)
        raw_conn.commit()
    except Exception:
        raw_conn.rollback()
        raise
    finally:
        raw_conn.close()


def apply_schema_sql(db: Any) -> None:
    schema_sql = _read_schema_sql()
    _run_sql_script(db, schema_sql)


def _ensure_migrations_table(db: Any) -> None:
    db.session.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS genius.schema_migrations (
                id BIGSERIAL PRIMARY KEY,
                migration_key VARCHAR(255) NOT NULL UNIQUE,
                checksum CHAR(64) NOT NULL,
                applied_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
            )
            """
        )
    )
    db.session.commit()


def _load_migration_files(migrations_dir: Path) -> list[MigrationFile]:
    migration_files: list[MigrationFile] = []

    if not migrations_dir.exists():
        return migration_files

    for file_path in sorted(migrations_dir.glob("V*.sql")):
        sql = file_path.read_text(encoding="utf-8")
        migration_files.append(
            MigrationFile(
                key=file_path.name,
                checksum=sha256(sql.encode("utf-8")).hexdigest(),
                sql=sql,
            )
        )

    return migration_files


def apply_pending_migrations(db: Any, migrations_dir: Path) -> dict[str, int]:
    _ensure_migrations_table(db)

    pending = 0
    already_applied = 0

    for migration in _load_migration_files(migrations_dir):
        row = db.session.execute(
            text(
                """
                SELECT checksum
                FROM genius.schema_migrations
                WHERE migration_key = :migration_key
                """
            ),
            {"migration_key": migration.key},
        ).first()

        if row:
            if row.checksum != migration.checksum:
                raise RuntimeError(
                    f"La migracion {migration.key} ya fue aplicada con otro contenido."
                )
            already_applied += 1
            continue

        _run_sql_script(db, migration.sql)
        db.session.execute(
            text(
                """
                INSERT INTO genius.schema_migrations (migration_key, checksum)
                VALUES (:migration_key, :checksum)
                """
            ),
            {
                "migration_key": migration.key,
                "checksum": migration.checksum,
            },
        )
        db.session.commit()
        pending += 1

    return {
        "applied": pending,
        "already_applied": already_applied,
    }


def bootstrap_database(db: Any) -> dict[str, int]:
    apply_schema_sql(db)

    migrations_dir = Path(
        current_app.config.get(
            "DB_MIGRATIONS_DIR",
            str(Path(__file__).parent / "migrations" / "sql"),
        )
    )
    return apply_pending_migrations(db, migrations_dir)
