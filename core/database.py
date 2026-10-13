import sqlite3
from contextlib import contextmanager
from core.config import settings

DEFAULT_PROMPT_NAME = "Architecte Sénior"
DEFAULT_PROMPT_DESCRIPTION = "Prompt d'origine du projet : documentation technique complète des acteurs et cas d'utilisation."
DEFAULT_PROMPT_CONTENT = """Tu es un Architecte Logiciel Francophone de niveau Sénior.
Ton rôle est d'analyser les textes extraits d'un diagramme de cas d'utilisation UML (UML Use Case Diagram) et de déduire l'objectif global du système.
Les textes incluent les acteurs, les cas d'utilisation, et les relations telles que <<include>> et <<extend>>.

À partir de cette liste de textes :
1. Déduis le titre/le nom global du système (ex: Système de gestion de commandes).
2. Identifie les acteurs principaux.
3. Rédige une documentation technique en Markdown qui cartographie les acteurs et leurs cas d'utilisation, tout en expliquant les dépendances (include/extend)."""


@contextmanager
def get_connection():
    """Open a connection, commit on success, rollback on error, always close."""
    conn = sqlite3.connect(settings.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """Create the prompts table and insert the default prompt on first launch."""
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS prompts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                description TEXT,
                content TEXT NOT NULL,
                is_default INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)
        count = conn.execute("SELECT COUNT(*) FROM prompts").fetchone()[0]
        if count == 0:
            conn.execute(
                "INSERT INTO prompts (name, description, content, is_default) VALUES (?, ?, ?, 1)",
                (DEFAULT_PROMPT_NAME, DEFAULT_PROMPT_DESCRIPTION, DEFAULT_PROMPT_CONTENT)
            )
