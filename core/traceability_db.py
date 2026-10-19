"""Tables SQLite de la Gestion 4 (exigences & traçabilité UML).

Elles vivent dans la même base que la Gestion des Prompts (settings.DATABASE_PATH),
préfixées par "tr_". init_traceability_db() ne touche jamais à la table "prompts".
"""
from contextlib import contextmanager
from core.database import get_connection

SCHEMA = """
CREATE TABLE IF NOT EXISTS tr_projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    specification_text TEXT,
    active_document_id INTEGER REFERENCES tr_uml_documents(id) ON DELETE SET NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS tr_requirements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL REFERENCES tr_projects(id) ON DELETE CASCADE,
    reference TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    type TEXT NOT NULL CHECK (type IN ('fonctionnelle', 'non_fonctionnelle')),
    priority TEXT NOT NULL CHECK (priority IN ('haute', 'moyenne', 'basse')),
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (project_id, reference)
);

CREATE TABLE IF NOT EXISTS tr_uml_documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL REFERENCES tr_projects(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    source TEXT NOT NULL CHECK (source IN ('generated', 'import', 'manual')),
    system_title TEXT,
    markdown TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Acteurs et cas d'utilisation identifiés dans un document UML
CREATE TABLE IF NOT EXISTS tr_uml_elements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id INTEGER NOT NULL REFERENCES tr_uml_documents(id) ON DELETE CASCADE,
    kind TEXT NOT NULL CHECK (kind IN ('actor', 'use_case')),
    name TEXT NOT NULL,
    actors TEXT NOT NULL DEFAULT '[]',
    origin TEXT NOT NULL CHECK (origin IN ('ia', 'manuel', 'generation')),
    UNIQUE (document_id, kind, name)
);

-- Couverture d'une exigence vis-à-vis d'un document UML donné
CREATE TABLE IF NOT EXISTS tr_coverage (
    requirement_id INTEGER NOT NULL REFERENCES tr_requirements(id) ON DELETE CASCADE,
    document_id INTEGER NOT NULL REFERENCES tr_uml_documents(id) ON DELETE CASCADE,
    status TEXT NOT NULL CHECK (status IN ('couverte', 'partielle', 'non_couverte', 'a_verifier')),
    justification TEXT NOT NULL,
    recommendation TEXT,
    origin TEXT NOT NULL CHECK (origin IN ('ia', 'manuel')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (requirement_id, document_id)
);

-- Associations exigence <-> cas d'utilisation
CREATE TABLE IF NOT EXISTS tr_links (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    requirement_id INTEGER NOT NULL REFERENCES tr_requirements(id) ON DELETE CASCADE,
    element_id INTEGER NOT NULL REFERENCES tr_uml_elements(id) ON DELETE CASCADE,
    origin TEXT NOT NULL CHECK (origin IN ('ia', 'manuel')),
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (requirement_id, element_id)
);

-- Historique des analyses de traçabilité (instantané des statistiques)
CREATE TABLE IF NOT EXISTS tr_analyses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL REFERENCES tr_projects(id) ON DELETE CASCADE,
    document_id INTEGER REFERENCES tr_uml_documents(id) ON DELETE SET NULL,
    document_name TEXT,
    model TEXT NOT NULL,
    summary TEXT NOT NULL,
    suggestions TEXT NOT NULL DEFAULT '[]',
    stats TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_tr_requirements_project ON tr_requirements(project_id);
CREATE INDEX IF NOT EXISTS idx_tr_documents_project ON tr_uml_documents(project_id);
CREATE INDEX IF NOT EXISTS idx_tr_elements_document ON tr_uml_elements(document_id);
CREATE INDEX IF NOT EXISTS idx_tr_links_requirement ON tr_links(requirement_id);
CREATE INDEX IF NOT EXISTS idx_tr_analyses_project ON tr_analyses(project_id);
"""


@contextmanager
def tr_connection():
    """Connexion partagée avec la Gestion des Prompts, avec les clés étrangères activées."""
    with get_connection() as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        yield conn


def init_traceability_db():
    """Crée les tables tr_* si elles n'existent pas (idempotent, aucune donnée supprimée)."""
    with tr_connection() as conn:
        conn.executescript(SCHEMA)
