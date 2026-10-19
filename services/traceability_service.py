"""Logique métier de la Gestion 4 : exigences, documents UML, couverture et traçabilité."""
import csv
import io
import json
import re
import sqlite3
from typing import Optional

from core.traceability_db import tr_connection
from schemas.traceability import (
    ProjectPayload, RequirementCreate, RequirementUpdate, RequirementDraft,
    UmlDocumentCreate, UmlElementCreate, CoverageUpdate, AIMappingResponse, AIExtractedElements,
)
from services import traceability_ai
from services.coverage_service import compute_stats, appears_in, normalize

STATUS_LABELS = {
    "couverte": "Couverte",
    "partielle": "Partiellement couverte",
    "non_couverte": "Non couverte",
    "a_verifier": "À vérifier manuellement",
    "non_analysee": "Non analysée",
}
TYPE_LABELS = {"fonctionnelle": "Fonctionnelle", "non_fonctionnelle": "Non fonctionnelle"}


class NotFoundError(Exception):
    pass


class ConflictError(Exception):
    pass


class BusinessRuleError(Exception):
    """Requête valide syntaxiquement mais incohérente avec les règles métier (HTTP 400)."""
    pass


# --- Projets -----------------------------------------------------------------

def list_projects() -> list[dict]:
    with tr_connection() as conn:
        rows = conn.execute("""
            SELECT p.*, (SELECT COUNT(*) FROM tr_requirements r WHERE r.project_id = p.id) AS requirements_count
            FROM tr_projects p ORDER BY p.updated_at DESC, p.id DESC
        """).fetchall()
    return [dict(r) for r in rows]


def get_project(project_id: int) -> dict:
    with tr_connection() as conn:
        row = conn.execute("""
            SELECT p.*, (SELECT COUNT(*) FROM tr_requirements r WHERE r.project_id = p.id) AS requirements_count
            FROM tr_projects p WHERE p.id = ?
        """, (project_id,)).fetchone()
    if row is None:
        raise NotFoundError(f"Projet {project_id} introuvable.")
    return dict(row)


def create_project(data: ProjectPayload) -> dict:
    try:
        with tr_connection() as conn:
            cursor = conn.execute(
                "INSERT INTO tr_projects (name, description, specification_text) VALUES (?, ?, ?)",
                (data.name, data.description, data.specification_text),
            )
            new_id = cursor.lastrowid
    except sqlite3.IntegrityError:
        raise ConflictError(f"Un projet nommé '{data.name}' existe déjà.")
    return get_project(new_id)


def update_project(project_id: int, data: ProjectPayload) -> dict:
    get_project(project_id)
    try:
        with tr_connection() as conn:
            conn.execute(
                "UPDATE tr_projects SET name = ?, description = ?, specification_text = ?, updated_at = datetime('now') WHERE id = ?",
                (data.name, data.description, data.specification_text, project_id),
            )
    except sqlite3.IntegrityError:
        raise ConflictError(f"Un projet nommé '{data.name}' existe déjà.")
    return get_project(project_id)


def delete_project(project_id: int):
    get_project(project_id)
    with tr_connection() as conn:
        conn.execute("DELETE FROM tr_projects WHERE id = ?", (project_id,))


def _touch_project(conn, project_id: int):
    conn.execute("UPDATE tr_projects SET updated_at = datetime('now') WHERE id = ?", (project_id,))


# --- Exigences ---------------------------------------------------------------

def _next_reference(conn, project_id: int) -> str:
    refs = conn.execute("SELECT reference FROM tr_requirements WHERE project_id = ?", (project_id,)).fetchall()
    numbers = [int(m.group(1)) for (ref,) in refs if (m := re.fullmatch(r"REQ-(\d+)", ref))]
    return f"REQ-{(max(numbers) + 1 if numbers else 1):03d}"


def list_requirements(project_id: int) -> list[dict]:
    project = get_project(project_id)
    with tr_connection() as conn:
        rows = conn.execute("""
            SELECT r.*, COALESCE(c.status, 'non_analysee') AS coverage_status
            FROM tr_requirements r
            LEFT JOIN tr_coverage c ON c.requirement_id = r.id AND c.document_id = ?
            WHERE r.project_id = ?
            ORDER BY r.reference
        """, (project["active_document_id"], project_id)).fetchall()
    return [dict(r) for r in rows]


def get_requirement(requirement_id: int) -> dict:
    with tr_connection() as conn:
        row = conn.execute("SELECT * FROM tr_requirements WHERE id = ?", (requirement_id,)).fetchone()
    if row is None:
        raise NotFoundError(f"Exigence {requirement_id} introuvable.")
    return _with_status(dict(row))


def _with_status(req: dict) -> dict:
    project = get_project(req["project_id"])
    with tr_connection() as conn:
        row = conn.execute("SELECT status FROM tr_coverage WHERE requirement_id = ? AND document_id = ?",
                           (req["id"], project["active_document_id"])).fetchone()
    req["coverage_status"] = row["status"] if row else "non_analysee"
    return req


def create_requirement(project_id: int, data: RequirementCreate) -> dict:
    get_project(project_id)
    try:
        with tr_connection() as conn:
            reference = data.reference or _next_reference(conn, project_id)
            cursor = conn.execute(
                "INSERT INTO tr_requirements (project_id, reference, title, description, type, priority) VALUES (?, ?, ?, ?, ?, ?)",
                (project_id, reference, data.title, data.description, data.type, data.priority),
            )
            new_id = cursor.lastrowid
            _touch_project(conn, project_id)
    except sqlite3.IntegrityError:
        raise ConflictError(f"La référence {data.reference} existe déjà dans ce projet.")
    return get_requirement(new_id)


def bulk_create_requirements(project_id: int, drafts: list[RequirementDraft], replace_existing: bool) -> list[dict]:
    """Enregistre en une transaction les exigences validées par l'utilisateur."""
    get_project(project_id)
    with tr_connection() as conn:
        if replace_existing:
            conn.execute("DELETE FROM tr_requirements WHERE project_id = ?", (project_id,))
        for draft in drafts:
            conn.execute(
                "INSERT INTO tr_requirements (project_id, reference, title, description, type, priority) VALUES (?, ?, ?, ?, ?, ?)",
                (project_id, _next_reference(conn, project_id), draft.title, draft.description, draft.type, draft.priority),
            )
        _touch_project(conn, project_id)
    return list_requirements(project_id)


def update_requirement(requirement_id: int, data: RequirementUpdate) -> dict:
    current = get_requirement(requirement_id)
    try:
        with tr_connection() as conn:
            conn.execute(
                """UPDATE tr_requirements SET reference = ?, title = ?, description = ?, type = ?, priority = ?,
                   updated_at = datetime('now') WHERE id = ?""",
                (data.reference, data.title, data.description, data.type, data.priority, requirement_id),
            )
            _touch_project(conn, current["project_id"])
    except sqlite3.IntegrityError:
        raise ConflictError(f"La référence {data.reference} existe déjà dans ce projet.")
    return get_requirement(requirement_id)


def delete_requirement(requirement_id: int):
    """Les couvertures et associations de l'exigence sont supprimées en cascade (clés étrangères)."""
    current = get_requirement(requirement_id)
    with tr_connection() as conn:
        conn.execute("DELETE FROM tr_requirements WHERE id = ?", (requirement_id,))
        _touch_project(conn, current["project_id"])


def extract_requirements(text: str) -> dict:
    result = traceability_ai.extract_requirements(text)
    if not result.requirements:
        raise BusinessRuleError("Gemini n'a identifié aucune exigence dans ce texte. Vérifiez le cahier des charges.")
    return {"requirements": result.requirements, "source": "ia", "model": traceability_ai.GEMINI_MODEL}


# --- Documents UML et éléments ----------------------------------------------

def _element_dict(row) -> dict:
    element = dict(row)
    element["actors"] = json.loads(element["actors"])
    return element


def list_documents(project_id: int) -> list[dict]:
    get_project(project_id)
    with tr_connection() as conn:
        rows = conn.execute("""
            SELECT d.id, d.project_id, d.name, d.source, d.system_title, d.created_at,
              (SELECT COUNT(*) FROM tr_uml_elements e WHERE e.document_id = d.id AND e.kind = 'actor') AS actors_count,
              (SELECT COUNT(*) FROM tr_uml_elements e WHERE e.document_id = d.id AND e.kind = 'use_case') AS use_cases_count
            FROM tr_uml_documents d WHERE d.project_id = ? ORDER BY d.id DESC
        """, (project_id,)).fetchall()
    return [dict(r) for r in rows]


def get_document(document_id: int) -> dict:
    with tr_connection() as conn:
        row = conn.execute("SELECT * FROM tr_uml_documents WHERE id = ?", (document_id,)).fetchone()
        if row is None:
            raise NotFoundError(f"Document UML {document_id} introuvable.")
        elements = conn.execute(
            "SELECT * FROM tr_uml_elements WHERE document_id = ? ORDER BY kind, name", (document_id,)
        ).fetchall()
    document = dict(row)
    document["elements"] = [_element_dict(e) for e in elements]
    document["actors_count"] = sum(1 for e in document["elements"] if e["kind"] == "actor")
    document["use_cases_count"] = sum(1 for e in document["elements"] if e["kind"] == "use_case")
    return document


def create_document(project_id: int, data: UmlDocumentCreate) -> dict:
    get_project(project_id)
    with tr_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO tr_uml_documents (project_id, name, source, system_title, markdown) VALUES (?, ?, ?, ?, ?)",
            (project_id, data.name, data.source, data.system_title, data.markdown),
        )
        document_id = cursor.lastrowid
        # Les acteurs déjà détectés par la génération de documentation sont repris s'ils figurent dans le texte
        for actor in dict.fromkeys(a.strip() for a in data.detected_actors if a.strip()):
            if appears_in(actor, data.markdown):
                conn.execute(
                    "INSERT OR IGNORE INTO tr_uml_elements (document_id, kind, name, origin) VALUES (?, 'actor', ?, 'generation')",
                    (document_id, actor),
                )
        conn.execute("UPDATE tr_projects SET active_document_id = ?, updated_at = datetime('now') WHERE id = ?",
                     (document_id, project_id))
    return get_document(document_id)


def delete_document(document_id: int):
    get_document(document_id)
    with tr_connection() as conn:
        conn.execute("DELETE FROM tr_uml_documents WHERE id = ?", (document_id,))


def set_active_document(project_id: int, document_id: int) -> dict:
    document = get_document(document_id)
    if document["project_id"] != project_id:
        raise BusinessRuleError("Ce document UML n'appartient pas à ce projet.")
    with tr_connection() as conn:
        conn.execute("UPDATE tr_projects SET active_document_id = ?, updated_at = datetime('now') WHERE id = ?",
                     (document_id, project_id))
    return get_project(project_id)


def add_element(document_id: int, data: UmlElementCreate) -> dict:
    get_document(document_id)
    try:
        with tr_connection() as conn:
            cursor = conn.execute(
                "INSERT INTO tr_uml_elements (document_id, kind, name, actors, origin) VALUES (?, ?, ?, ?, 'manuel')",
                (document_id, data.kind, data.name, json.dumps([a.strip() for a in data.actors if a.strip()], ensure_ascii=False)),
            )
            row = conn.execute("SELECT * FROM tr_uml_elements WHERE id = ?", (cursor.lastrowid,)).fetchone()
    except sqlite3.IntegrityError:
        raise ConflictError(f"L'élément '{data.name}' existe déjà dans ce document.")
    return _element_dict(row)


def delete_element(element_id: int):
    with tr_connection() as conn:
        deleted = conn.execute("DELETE FROM tr_uml_elements WHERE id = ?", (element_id,)).rowcount
    if not deleted:
        raise NotFoundError(f"Élément UML {element_id} introuvable.")


def extract_elements(document_id: int) -> dict:
    """Gemini liste acteurs et cas d'utilisation ; seuls ceux présents dans le texte sont conservés.

    Les éléments existants (et donc leurs associations) sont conservés : on ajoute seulement les nouveaux.
    """
    document = get_document(document_id)
    result: AIExtractedElements = traceability_ai.extract_uml_elements(document["markdown"])
    markdown = document["markdown"]
    rejected = []

    with tr_connection() as conn:
        for actor in result.actors:
            if appears_in(actor, markdown):
                conn.execute("INSERT OR IGNORE INTO tr_uml_elements (document_id, kind, name, origin) VALUES (?, 'actor', ?, 'ia')",
                             (document_id, actor.strip()))
            else:
                rejected.append(actor)
        for use_case in result.use_cases:
            if appears_in(use_case.name, markdown):
                actors = [a for a in use_case.actors if appears_in(a, markdown)]
                conn.execute(
                    "INSERT OR IGNORE INTO tr_uml_elements (document_id, kind, name, actors, origin) VALUES (?, 'use_case', ?, ?, 'ia')",
                    (document_id, use_case.name.strip(), json.dumps(actors, ensure_ascii=False)),
                )
            else:
                rejected.append(use_case.name)

    document = get_document(document_id)
    document["rejected_elements"] = rejected
    return document


# --- Couverture et matrice ---------------------------------------------------

def _resolve_document(project: dict, document_id: Optional[int]) -> Optional[dict]:
    document_id = document_id or project["active_document_id"]
    if document_id is None:
        return None
    document = get_document(document_id)
    if document["project_id"] != project["id"]:
        raise BusinessRuleError("Ce document UML n'appartient pas à ce projet.")
    return document


def build_matrix(project_id: int, document_id: Optional[int] = None) -> dict:
    project = get_project(project_id)
    document = _resolve_document(project, document_id)
    doc_id = document["id"] if document else None

    with tr_connection() as conn:
        requirements = conn.execute("""
            SELECT r.*, c.status, c.justification, c.recommendation, c.origin
            FROM tr_requirements r
            LEFT JOIN tr_coverage c ON c.requirement_id = r.id AND c.document_id = ?
            WHERE r.project_id = ? ORDER BY r.reference
        """, (doc_id, project_id)).fetchall()
        links = conn.execute("""
            SELECT l.requirement_id, e.id, e.name FROM tr_links l
            JOIN tr_uml_elements e ON e.id = l.element_id
            WHERE e.document_id = ? ORDER BY e.name
        """, (doc_id,)).fetchall()

    links_by_req: dict[int, list] = {}
    for link in links:
        links_by_req.setdefault(link["requirement_id"], []).append({"id": link["id"], "name": link["name"]})

    rows = [{
        "requirement_id": r["id"],
        "reference": r["reference"],
        "title": r["title"],
        "description": r["description"],
        "type": r["type"],
        "priority": r["priority"],
        "use_cases": links_by_req.get(r["id"], []),
        "status": r["status"] or "non_analysee",
        "justification": r["justification"],
        "recommendation": r["recommendation"],
        "origin": r["origin"],
    } for r in requirements]

    return {
        "project_id": project_id,
        "document_id": doc_id,
        "document_name": document["name"] if document else None,
        "rows": rows,
        "stats": compute_stats(rows),
        "use_cases": [e for e in document["elements"] if e["kind"] == "use_case"] if document else [],
    }


def update_coverage(project_id: int, requirement_id: int, data: CoverageUpdate) -> dict:
    """Correction humaine : remplace statut, justification et associations de l'exigence."""
    requirement = get_requirement(requirement_id)
    if requirement["project_id"] != project_id:
        raise BusinessRuleError("Cette exigence n'appartient pas à ce projet.")
    document = _resolve_document(get_project(project_id), data.document_id)
    valid_ids = {e["id"] for e in document["elements"] if e["kind"] == "use_case"}
    unknown = [i for i in data.use_case_ids if i not in valid_ids]
    if unknown:
        raise BusinessRuleError("Certains cas d'utilisation sélectionnés n'existent pas dans ce document UML.")
    if data.status in ("couverte", "partielle") and not data.use_case_ids:
        raise BusinessRuleError("Une exigence couverte ou partiellement couverte doit être associée à au moins un cas d'utilisation.")
    if data.status == "non_couverte" and data.use_case_ids:
        raise BusinessRuleError("Une exigence non couverte ne peut pas être associée à un cas d'utilisation.")

    with tr_connection() as conn:
        _save_coverage(conn, requirement_id, document["id"], data.status, data.justification,
                       data.recommendation, "manuel", list(dict.fromkeys(data.use_case_ids)))
        _touch_project(conn, project_id)
    return build_matrix(project_id, document["id"])


def _save_coverage(conn, requirement_id, document_id, status, justification, recommendation, origin, element_ids):
    conn.execute("""
        INSERT INTO tr_coverage (requirement_id, document_id, status, justification, recommendation, origin)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT (requirement_id, document_id) DO UPDATE SET
            status = excluded.status, justification = excluded.justification,
            recommendation = excluded.recommendation, origin = excluded.origin, updated_at = datetime('now')
    """, (requirement_id, document_id, status, justification, recommendation, origin))
    conn.execute("""
        DELETE FROM tr_links WHERE requirement_id = ?
        AND element_id IN (SELECT id FROM tr_uml_elements WHERE document_id = ?)
    """, (requirement_id, document_id))
    for element_id in element_ids:
        conn.execute("INSERT INTO tr_links (requirement_id, element_id, origin) VALUES (?, ?, ?)",
                     (requirement_id, element_id, origin))


# --- Analyse de traçabilité (Gemini) -----------------------------------------

def analyze(project_id: int, document_id: int) -> dict:
    project = get_project(project_id)
    document = _resolve_document(project, document_id)
    requirements = list_requirements(project_id)
    if not requirements:
        raise BusinessRuleError("Ce projet ne contient aucune exigence : extrayez ou ajoutez des exigences avant l'analyse.")

    # Réutilise les éléments déjà identifiés ; sinon Gemini les extrait (sans relancer l'OCR)
    if not any(e["kind"] == "use_case" for e in document["elements"]):
        document = extract_elements(document["id"])
    use_cases = [e for e in document["elements"] if e["kind"] == "use_case"]
    if not use_cases:
        raise BusinessRuleError(
            "Aucun cas d'utilisation n'a été identifié dans ce document UML. "
            "Ajoutez-les manuellement ou importez une documentation plus détaillée."
        )
    actors = [e["name"] for e in document["elements"] if e["kind"] == "actor"]

    ai: AIMappingResponse = traceability_ai.map_requirements(requirements, actors, [u["name"] for u in use_cases])
    by_name = {normalize(u["name"]): u["id"] for u in use_cases}
    by_ref = {r["reference"]: r for r in requirements}

    with tr_connection() as conn:
        manual = {row["requirement_id"] for row in conn.execute(
            "SELECT requirement_id FROM tr_coverage WHERE document_id = ? AND origin = 'manuel'", (document["id"],))}

    ignored: list[str] = []
    seen: set[int] = set()
    with tr_connection() as conn:
        for mapping in ai.mappings:
            requirement = by_ref.get(mapping.reference.strip())
            if requirement is None or requirement["id"] in seen:
                continue
            seen.add(requirement["id"])
            if requirement["id"] in manual:
                continue  # une correction humaine n'est jamais écrasée par l'IA
            status, justification, recommendation, element_ids = _validate_mapping(mapping, requirement, by_name, ignored)
            _save_coverage(conn, requirement["id"], document["id"], status, justification, recommendation, "ia", element_ids)

        # Exigences oubliées par Gemini : on ne suppose rien, vérification manuelle demandée
        for requirement in requirements:
            if requirement["id"] not in seen and requirement["id"] not in manual:
                _save_coverage(conn, requirement["id"], document["id"], "a_verifier",
                               "Gemini n'a pas évalué cette exigence : vérification manuelle nécessaire.", None, "ia", [])

        conn.execute("UPDATE tr_projects SET active_document_id = ?, updated_at = datetime('now') WHERE id = ?",
                     (document["id"], project_id))

    matrix = build_matrix(project_id, document["id"])
    with tr_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO tr_analyses (project_id, document_id, document_name, model, summary, suggestions, stats) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (project_id, document["id"], document["name"], traceability_ai.GEMINI_MODEL, ai.summary.strip(),
             json.dumps(ai.suggestions, ensure_ascii=False), json.dumps(matrix["stats"], ensure_ascii=False)),
        )
        analysis_id = cursor.lastrowid

    return {"analysis": get_analysis(analysis_id), "matrix": matrix, "ignored_use_cases": list(dict.fromkeys(ignored))}


def _validate_mapping(mapping, requirement: dict, by_name: dict, ignored: list) -> tuple:
    """Applique les garde-fous métier à une proposition de Gemini."""
    element_ids = []
    for name in mapping.use_cases:
        element_id = by_name.get(normalize(name))
        if element_id is None:
            ignored.append(name)  # cas d'utilisation inventé : rejeté
        elif element_id not in element_ids:
            element_ids.append(element_id)

    status = mapping.status
    justification = mapping.justification.strip()
    recommendation = (mapping.recommendation or "").strip() or None

    if requirement["type"] == "non_fonctionnelle" and status in ("couverte", "partielle", "non_couverte"):
        status = "a_verifier"
        justification += " — Exigence non fonctionnelle : un cas d'utilisation ne prouve pas sa satisfaction, vérification manuelle requise."
    elif status in ("couverte", "partielle") and not element_ids:
        status = "non_couverte"
        justification += " — Aucun cas d'utilisation cité n'existe dans le document UML."
    elif status == "non_couverte":
        element_ids = []
    if status == "couverte":
        recommendation = None
    return status, justification, recommendation, element_ids


# --- Historique, tableau de bord et exports -----------------------------------

def _analysis_dict(row) -> dict:
    analysis = dict(row)
    analysis["suggestions"] = json.loads(analysis["suggestions"])
    analysis["stats"] = json.loads(analysis["stats"])
    return analysis


def get_analysis(analysis_id: int) -> dict:
    with tr_connection() as conn:
        row = conn.execute("""
            SELECT a.*, p.name AS project_name FROM tr_analyses a
            JOIN tr_projects p ON p.id = a.project_id WHERE a.id = ?
        """, (analysis_id,)).fetchone()
    if row is None:
        raise NotFoundError(f"Analyse {analysis_id} introuvable.")
    return _analysis_dict(row)


def list_analyses(project_id: Optional[int] = None, limit: int = 50) -> list[dict]:
    query = "SELECT a.*, p.name AS project_name FROM tr_analyses a JOIN tr_projects p ON p.id = a.project_id"
    params: tuple = ()
    if project_id is not None:
        get_project(project_id)
        query += " WHERE a.project_id = ?"
        params = (project_id,)
    with tr_connection() as conn:
        rows = conn.execute(query + " ORDER BY a.id DESC LIMIT ?", (*params, limit)).fetchall()
    return [_analysis_dict(r) for r in rows]


def dashboard() -> dict:
    projects = list_projects()
    all_rows, summaries = [], []
    for project in projects:
        matrix = build_matrix(project["id"])
        all_rows.extend(matrix["rows"])
        last = list_analyses(project["id"], limit=1)
        summaries.append({
            "id": project["id"],
            "name": project["name"],
            "requirements_count": project["requirements_count"],
            "active_document_id": project["active_document_id"],
            "stats": matrix["stats"],
            "last_analysis_at": last[0]["created_at"] if last else None,
        })
    with tr_connection() as conn:
        analyses_count = conn.execute("SELECT COUNT(*) FROM tr_analyses").fetchone()[0]
    return {
        "projects_count": len(projects),
        "analyses_count": analyses_count,
        "totals": compute_stats(all_rows),
        "projects": summaries,
        "recent_analyses": list_analyses(limit=5),
    }


def export_matrix_csv(project_id: int, document_id: Optional[int] = None) -> str:
    matrix = build_matrix(project_id, document_id)
    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter=";")
    writer.writerow(["Référence", "Titre", "Description", "Type", "Priorité",
                     "Cas d'utilisation associés", "Couverture", "Justification", "Recommandation", "Origine"])
    for row in matrix["rows"]:
        writer.writerow([
            row["reference"], row["title"], row["description"], TYPE_LABELS[row["type"]], row["priority"],
            " | ".join(u["name"] for u in row["use_cases"]) or "Aucun",
            STATUS_LABELS[row["status"]], row["justification"] or "", row["recommendation"] or "",
            {"ia": "IA (Gemini)", "manuel": "Validation manuelle"}.get(row["origin"], ""),
        ])
    return buffer.getvalue()


def _md_cell(text: Optional[str]) -> str:
    return (text or "").replace("|", "\\|").replace("\n", " ")


def export_report_markdown(project_id: int, document_id: Optional[int] = None) -> str:
    project = get_project(project_id)
    matrix = build_matrix(project_id, document_id)
    stats = matrix["stats"]
    analyses = [a for a in list_analyses(project_id) if a["document_id"] == matrix["document_id"]]
    last = analyses[0] if analyses else None
    rate = f"{stats['coverage_rate']} %" if stats["coverage_rate"] is not None else "non calculable (aucune exigence fonctionnelle analysable)"

    lines = [
        f"# Rapport de couverture — {project['name']}",
        "",
        f"- **Document UML** : {matrix['document_name'] or 'aucun'}",
        f"- **Dernière analyse** : {last['created_at'] + ' (' + last['model'] + ')' if last else 'aucune'}",
        "",
        "## Résumé",
        "",
        (last["summary"] if last and last["summary"] else "Aucun résumé d'analyse IA disponible."),
        "",
        "## Statistiques",
        "",
        "| Indicateur | Valeur |",
        "|---|---|",
        f"| Exigences | {stats['total']} |",
        f"| Fonctionnelles | {stats['functional']} |",
        f"| Non fonctionnelles | {stats['non_functional']} |",
        f"| Couvertes | {stats['covered']} |",
        f"| Partiellement couvertes | {stats['partial']} |",
        f"| Non couvertes | {stats['uncovered']} |",
        f"| À vérifier manuellement | {stats['to_verify']} |",
        f"| Non analysées | {stats['not_analyzed']} |",
        "",
        f"**Taux de couverture : {rate}**",
        "",
        f"Formule : {stats['formula']} — dénominateur = {stats['analyzable_functional']} exigence(s) fonctionnelle(s) analysable(s).",
        "",
        "## Matrice de traçabilité",
        "",
        "| Exigence | Type | Priorité | Cas d'utilisation | Couverture | Justification |",
        "|---|---|---|---|---|---|",
    ]
    for row in matrix["rows"]:
        lines.append(
            f"| {row['reference']} {_md_cell(row['title'])} | {TYPE_LABELS[row['type']]} | {row['priority']} | "
            f"{_md_cell(', '.join(u['name'] for u in row['use_cases'])) or 'Aucun'} | {STATUS_LABELS[row['status']]} | "
            f"{_md_cell(row['justification'])} |"
        )

    missing = [r for r in matrix["rows"] if r["status"] in ("non_couverte", "partielle")]
    lines += ["", "## Exigences manquantes ou partielles", ""]
    lines += [f"- **{r['reference']} {r['title']}** ({STATUS_LABELS[r['status']]}) : {r['recommendation'] or 'aucune recommandation'}"
              for r in missing] or ["Aucune."]

    suggestions = last["suggestions"] if last else []
    lines += ["", "## Suggestions d'amélioration (IA)", ""]
    lines += [f"- {s}" for s in suggestions] or ["Aucune suggestion."]
    lines += ["", "> Ces suggestions sont des recommandations : le diagramme UML original n'est jamais modifié automatiquement.", ""]
    return "\n".join(lines)
