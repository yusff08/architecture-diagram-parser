import sqlite3
import os
import json
from contextlib import contextmanager
from typing import Generator

DB_FILE = os.getenv("DATABASE_PATH", "uml_analyzer.db")

def get_connection(db_path: str = None) -> sqlite3.Connection:
    """
    Retourne une connexion SQLite configurée avec les clés étrangères
    et le retour des lignes sous forme de dictionnaires (sqlite3.Row).
    """
    path = db_path or os.getenv("DATABASE_PATH", DB_FILE)
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

@contextmanager
def get_db(db_path: str = None) -> Generator[sqlite3.Connection, None, None]:
    """
    Gestionnaire de contexte pour obtenir une connexion avec commit/rollback automatique.
    """
    conn = get_connection(db_path)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def init_db(db_path: str = None) -> None:
    """
    Initialise les tables du module Gestion des Tests avec contraintes CHECK strictes.
    Idempotent et non-destructif pour les autres modules de l'application.
    """
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        
        # Table test_cases
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
        
        # Table test_runs
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

# Initialisation automatique au chargement du module
init_db()
