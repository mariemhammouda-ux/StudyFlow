import sqlite3
from functools import wraps
from pathlib import Path

from flask import g, redirect, session

BASE_DIR = Path(__file__).resolve().parent
DATABASE = BASE_DIR / "studyflow.db"
SCHEMA = BASE_DIR / "schema.sql"


def get_db():
    """Ouvre une connexion SQLite réutilisée pendant la requête Flask."""
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(_error=None):
    """Ferme la connexion à la fin de la requête."""
    db = g.pop("db", None)
    if db is not None:
        db.close()


def login_required(view):
    """Redirige vers /login si la session n'a pas de user_id."""

    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return view(*args, **kwargs)

    return wrapped_view


def init_db():
    """Crée le fichier SQLite et les tables à partir de schema.sql."""
    connection = sqlite3.connect(DATABASE)
    connection.execute("PRAGMA foreign_keys = ON")
    with SCHEMA.open(encoding="utf-8") as schema_file:
        connection.executescript(schema_file.read())
    connection.commit()
    connection.close()
