import sqlite3
import os
import json
from contextlib import contextmanager
from typing import Generator
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

DB_FILE = getattr(settings, "DATABASE_PATH", os.getenv("DATABASE_PATH", "uml_analyzer.db"))

def get_raw_connection(db_path: str = None) -> sqlite3.Connection:
    """
    Retourne une connexion SQLite configurée avec les clés étrangères
    et le retour des lignes sous forme de dictionnaires (sqlite3.Row).
    """
    path = db_path or getattr(settings, "DATABASE_PATH", os.getenv("DATABASE_PATH", DB_FILE))
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

@contextmanager
def get_connection(db_path: str = None) -> Generator[sqlite3.Connection, None, None]:
    """Open a connection, commit on success, rollback on error, always close."""
    conn = get_raw_connection(db_path)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

# Alias get_db pour la compatibilité avec le module Gestion des Tests
get_db = get_connection

def init_db(db_path: str = None) -> None:
    """
    Initialise les tables de l'application :
    - Table prompts (Gestion des Prompts)
    - Tables test_cases et test_runs (Gestion des Tests & Robustesse)
    """
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        
        # 1. Table prompts (Module Gestion des Prompts)
        cursor.execute("""
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
        cursor.execute("SELECT COUNT(*) FROM prompts")
        if cursor.fetchone()[0] == 0:
            cursor.execute(
                "INSERT INTO prompts (name, description, content, is_default) VALUES (?, ?, ?, 1)",
                (DEFAULT_PROMPT_NAME, DEFAULT_PROMPT_DESCRIPTION, DEFAULT_PROMPT_CONTENT)
            )

        # 2. Table test_cases (Module Gestion des Tests)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS test_cases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            analysis_name TEXT NOT NULL,
            use_case TEXT NOT NULL,
            actor TEXT,
            title TEXT NOT NULL,
            test_type TEXT NOT NULL CHECK(test_type IN ('nominal', 'limite', 'erreur')),
            injection_id TEXT,
            preconditions TEXT,
            steps TEXT NOT NULL DEFAULT '[]',
            expected_result TEXT NOT NULL,
            expected_behavior TEXT NOT NULL CHECK(expected_behavior IN ('erreur_4xx_message_clair', 'mode_secours', 'traitement_normal', 'rejet_propre')),
            priority TEXT NOT NULL CHECK(priority IN ('haute', 'moyenne', 'basse')),
            status TEXT NOT NULL DEFAULT 'a_faire' CHECK(status IN ('a_faire', 'passe', 'echoue')),
            generated_by_llm INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        """)
        
        # 3. Table test_runs (Module Gestion des Tests)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS test_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            test_case_id INTEGER NOT NULL,
            started_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            duration_ms INTEGER NOT NULL,
            status TEXT NOT NULL CHECK(status IN ('passe', 'echoue', 'erreur')),
            actual_behavior TEXT NOT NULL,
            details TEXT NOT NULL DEFAULT '{}',
            injection_id TEXT,
            FOREIGN KEY (test_case_id) REFERENCES test_cases(id) ON DELETE CASCADE
        );
        """)
        
        # Index pour optimiser les requêtes fréquentes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_test_cases_status ON test_cases(status);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_test_cases_type ON test_cases(test_type);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_test_runs_case_id ON test_runs(test_case_id);")

# Initialisation automatique au chargement
init_db()
