import os

import psycopg2
from flask import current_app, g


def get_db():
    """Devuelve una conexion activa a PostgreSQL para el contexto actual."""
    if "db" not in g:
        database_url = os.getenv("DATABASE_URL") or current_app.config.get("DATABASE_URL")
        if not database_url:
            raise RuntimeError("DATABASE_URL no esta configurada.")

        g.db = psycopg2.connect(database_url)

    return g.db


def close_db(_e=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_app(app):
    app.teardown_appcontext(close_db)