"""Tests de la Gestion 4 : exigences & traçabilité UML (aucun appel réel à Gemini)."""
import csv
import io
import json
import sys
import types as pytypes

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from core.traceability_db import init_traceability_db, tr_connection
from services import traceability_ai
from services.coverage_service import compute_stats, appears_in

SPEC = ("Le client doit pouvoir se connecter, consulter son profil et effectuer une réservation. "
        "L'administrateur doit pouvoir gérer les utilisateurs. Le système doit répondre rapidement aux requêtes.")

UML_MARKDOWN = """# Système de réservation
## Acteurs
- **Client**
- **Administrateur**
## Cas d'utilisation
- Client : Se connecter, Consulter le profil, Réserver
- Administrateur : Gérer les utilisateurs
"""

EXTRACTED = {"requirements": [
    {"title": "Authentification du client", "description": "Le client doit pouvoir se connecter.", "type": "fonctionnelle", "priority": "haute"},
    {"title": "Consultation du profil", "description": "Le client consulte son profil.", "type": "fonctionnelle", "priority": "moyenne"},
    {"title": "Réservation", "description": "Le client effectue une réservation.", "type": "fonctionnelle", "priority": "haute"},
    {"title": "Paiement", "description": "Le client paie sa réservation en ligne.", "type": "fonctionnelle", "priority": "haute"},
    {"title": "Performance du système", "description": "Le système répond rapidement.", "type": "non_fonctionnelle", "priority": "moyenne"},
]}

ELEMENTS = {"actors": ["Client", "Administrateur", "Comptable"],  # "Comptable" est absent du document
            "use_cases": [{"name": "Se connecter", "actors": ["Client"]},
                          {"name": "Consulter le profil", "actors": ["Client"]},
                          {"name": "Réserver", "actors": ["Client"]},
                          {"name": "Payer en ligne", "actors": ["Client"]}]}  # inventé : doit être rejeté

MAPPING = {
    "mappings": [
        {"reference": "REQ-001", "status": "couverte", "use_cases": ["Se connecter"], "justification": "Cas Se connecter présent.", "recommendation": None},
        {"reference": "REQ-002", "status": "partielle", "use_cases": ["Consulter le profil"], "justification": "Consultation seulement.", "recommendation": "Ajouter la modification du profil."},
        {"reference": "REQ-003", "status": "couverte", "use_cases": ["Réserver", "Annuler"], "justification": "Cas Réserver présent.", "recommendation": None},
        {"reference": "REQ-004", "status": "non_couverte", "use_cases": [], "justification": "Aucun cas de paiement.",
         "recommendation": "Étudier l'ajout du cas d'utilisation \"Effectuer un paiement\"."},
        {"reference": "REQ-005", "status": "couverte", "use_cases": ["Se connecter"], "justification": "Rapide."},
    ],
    "summary": "3 exigences fonctionnelles sur 4 sont réalisées.",
    "suggestions": ["Ajouter un cas d'utilisation de paiement."],
}


@pytest.fixture
def tr_db(temp_db):
    init_traceability_db()
    return temp_db


@pytest.fixture
def tr_client(tr_db):
    from api.endpoints import traceability
    app = FastAPI()
    app.include_router(traceability.router, prefix="/api")
    return TestClient(app)


@pytest.fixture
def fake_ai(monkeypatch):
    """Remplace l'appel réseau : chaque appel renvoie la prochaine réponse de la file."""
    queue, prompts = [], []

    def fake_call(prompt):
        prompts.append(prompt)
        item = queue.pop(0)
        if isinstance(item, Exception):
            raise item
        return item if isinstance(item, str) else json.dumps(item)

    monkeypatch.setattr(traceability_ai, "_call_gemini", fake_call)
    return pytypes.SimpleNamespace(queue=queue, prompts=prompts)


def new_project(client, name="Réservation en ligne"):
    response = client.post("/api/traceability/projects", json={"name": name, "specification_text": SPEC})
    assert response.status_code == 201
    return response.json()["id"]


def seeded_project(client):
    project_id = new_project(client)
    client.post(f"/api/traceability/projects/{project_id}/requirements/bulk", json={"requirements": EXTRACTED["requirements"]})
    doc = client.post(f"/api/traceability/projects/{project_id}/documents", json={
        "name": "Doc réservation", "source": "generated", "markdown": UML_MARKDOWN, "detected_actors": ["Client", "Inconnu"],
    }).json()
    return project_id, doc


# --- 1. CRUD des exigences ---------------------------------------------------

def test_project_crud_and_duplicate_name(tr_client):
    project_id = new_project(tr_client)
    assert tr_client.post("/api/traceability/projects", json={"name": "Réservation en ligne"}).status_code == 409
    assert tr_client.post("/api/traceability/projects", json={"name": "  "}).status_code == 422
    updated = tr_client.put(f"/api/traceability/projects/{project_id}", json={"name": "Nouveau nom"})
    assert updated.status_code == 200 and updated.json()["name"] == "Nouveau nom"
    assert tr_client.delete(f"/api/traceability/projects/{project_id}").status_code == 204
    assert tr_client.get(f"/api/traceability/projects/{project_id}").status_code == 404


def test_requirement_create_update_delete_with_auto_reference(tr_client):
    project_id = new_project(tr_client)
    url = f"/api/traceability/projects/{project_id}/requirements"
    first = tr_client.post(url, json={"title": "Connexion", "description": "Se connecter", "type": "fonctionnelle", "priority": "haute"})
    second = tr_client.post(url, json={"title": "Profil", "description": "Voir le profil", "type": "fonctionnelle"})
    assert first.status_code == 201 and first.json()["reference"] == "REQ-001"
    assert second.json()["reference"] == "REQ-002" and second.json()["priority"] == "moyenne"
    assert first.json()["coverage_status"] == "non_analysee"

    req_id = first.json()["id"]
    payload = {"reference": "REQ-010", "title": "Connexion sécurisée", "description": "Se connecter", "type": "fonctionnelle", "priority": "basse"}
    updated = tr_client.put(f"/api/traceability/requirements/{req_id}", json=payload)
    assert updated.status_code == 200 and updated.json()["reference"] == "REQ-010" and updated.json()["priority"] == "basse"
    assert tr_client.put(f"/api/traceability/requirements/{req_id}", json={**payload, "reference": "REQ-002"}).status_code == 409

    third = tr_client.post(url, json={"title": "Paiement", "description": "Payer", "type": "fonctionnelle"})
    assert third.json()["reference"] == "REQ-011"

    assert tr_client.delete(f"/api/traceability/requirements/{req_id}").status_code == 204
    assert tr_client.delete(f"/api/traceability/requirements/{req_id}").status_code == 404
    assert [r["reference"] for r in tr_client.get(url).json()] == ["REQ-002", "REQ-011"]


def test_requirement_validation_errors(tr_client):
    url = f"/api/traceability/projects/{new_project(tr_client)}/requirements"
    assert tr_client.post(url, json={"title": "ab", "description": "desc", "type": "fonctionnelle"}).status_code == 422
    assert tr_client.post(url, json={"title": "Titre", "description": "desc", "type": "autre"}).status_code == 422
    assert tr_client.post(url, json={"title": "Titre", "description": "desc", "type": "fonctionnelle", "priority": "urgente"}).status_code == 422
    assert tr_client.post(url, json={"title": "Titre", "description": "desc", "type": "fonctionnelle", "reference": "R1"}).status_code == 422
    assert tr_client.post("/api/traceability/projects/999/requirements",
                          json={"title": "Titre", "description": "desc", "type": "fonctionnelle"}).status_code == 404


def test_deleting_requirement_removes_its_coverage_and_links(tr_client, fake_ai):
    project_id, doc = seeded_project(tr_client)
    fake_ai.queue += [ELEMENTS, MAPPING]
    tr_client.post(f"/api/traceability/projects/{project_id}/analyze", json={"document_id": doc["id"]})
    req_id = tr_client.get(f"/api/traceability/projects/{project_id}/requirements").json()[0]["id"]
    with tr_connection() as conn:
        assert conn.execute("SELECT COUNT(*) FROM tr_links WHERE requirement_id = ?", (req_id,)).fetchone()[0] == 1

    tr_client.delete(f"/api/traceability/requirements/{req_id}")
    with tr_connection() as conn:
        assert conn.execute("SELECT COUNT(*) FROM tr_links WHERE requirement_id = ?", (req_id,)).fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM tr_coverage WHERE requirement_id = ?", (req_id,)).fetchone()[0] == 0


def test_bulk_save_can_replace_existing(tr_client):
    project_id = new_project(tr_client)
    url = f"/api/traceability/projects/{project_id}/requirements/bulk"
    tr_client.post(url, json={"requirements": EXTRACTED["requirements"][:2]})
    response = tr_client.post(url, json={"requirements": EXTRACTED["requirements"][2:], "replace_existing": True})
    assert response.status_code == 201
    assert [r["reference"] for r in response.json()] == ["REQ-001", "REQ-002", "REQ-003"]
    assert tr_client.post(url, json={"requirements": []}).status_code == 422


# --- 2 à 5. Extraction IA et gestion des erreurs ----------------------------

def test_extraction_with_valid_ai_response(tr_client, fake_ai):
    fake_ai.queue.append(EXTRACTED)
    response = tr_client.post("/api/traceability/requirements/extract", json={"text": SPEC})
    assert response.status_code == 200
    body = response.json()
    assert body["source"] == "ia" and len(body["requirements"]) == 5
    assert body["requirements"][4]["type"] == "non_fonctionnelle"
    assert SPEC in fake_ai.prompts[0]


@pytest.mark.parametrize("bad", ["pas du json", {"requirements": [{"title": "X"}]}, {"requirements": "abc"},
                                 {"requirements": [{"title": "Titre", "description": "d", "type": "fonctionnelle", "priority": "urgente"}]}])
def test_extraction_with_invalid_ai_response_returns_502(tr_client, fake_ai, bad):
    fake_ai.queue.append(bad)
    response = tr_client.post("/api/traceability/requirements/extract", json={"text": SPEC})
    assert response.status_code == 502
    assert "format JSON" in response.json()["detail"]


def test_extraction_with_no_requirement_returns_400(tr_client, fake_ai):
    fake_ai.queue.append({"requirements": []})
    assert tr_client.post("/api/traceability/requirements/extract", json={"text": SPEC}).status_code == 400


def test_extraction_text_too_short_returns_422(tr_client):
    assert tr_client.post("/api/traceability/requirements/extract", json={"text": "court"}).status_code == 422


def test_missing_api_key_returns_503(tr_client, no_api_key):
    response = tr_client.post("/api/traceability/requirements/extract", json={"text": SPEC})
    assert response.status_code == 503
    assert "GEMINI_API_KEY" in response.json()["detail"]


def install_fake_sdk(monkeypatch, error=None, text=None):
    """Faux SDK google-genai pour tester la traduction des erreurs de _call_gemini."""
    class FakeModels:
        def generate_content(self, model, contents, config):
            if error:
                raise error
            return pytypes.SimpleNamespace(text=text)

    genai = pytypes.ModuleType("google.genai")
    genai.Client = lambda api_key, http_options=None: pytypes.SimpleNamespace(models=FakeModels())
    genai_types = pytypes.ModuleType("google.genai.types")
    genai_types.GenerateContentConfig = lambda **kwargs: kwargs
    genai_types.HttpOptions = lambda **kwargs: kwargs
    genai.types = genai_types
    google = pytypes.ModuleType("google")
    google.genai = genai
    monkeypatch.setitem(sys.modules, "google", google)
    monkeypatch.setitem(sys.modules, "google.genai", genai)
    monkeypatch.setitem(sys.modules, "google.genai.types", genai_types)
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")


class FakeAPIError(Exception):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


@pytest.mark.parametrize("error, expected_status, expected_text", [
    (TimeoutError("read timed out"), 504, "délai"),
    (Exception("httpx.ReadTimeout: timeout"), 504, "délai"),
    (FakeAPIError(429, "RESOURCE_EXHAUSTED"), 429, "Quota"),
    (FakeAPIError(403, "API key not valid"), 503, "refusée"),
    (ConnectionError("réseau coupé"), 502, "indisponible"),
])
def test_gemini_errors_are_translated(tr_client, monkeypatch, error, expected_status, expected_text):
    install_fake_sdk(monkeypatch, error=error)
    response = tr_client.post("/api/traceability/requirements/extract", json={"text": SPEC})
    assert response.status_code == expected_status
    assert expected_text in response.json()["detail"]


def test_gemini_empty_response_is_rejected(tr_client, monkeypatch):
    install_fake_sdk(monkeypatch, text="")
    assert tr_client.post("/api/traceability/requirements/extract", json={"text": SPEC}).status_code == 502


def test_sdk_success_path_is_parsed(tr_client, monkeypatch):
    install_fake_sdk(monkeypatch, text=json.dumps(EXTRACTED))
    response = tr_client.post("/api/traceability/requirements/extract", json={"text": SPEC})
    assert response.status_code == 200 and len(response.json()["requirements"]) == 5


def test_ai_failure_keeps_existing_data(tr_client, fake_ai):
    project_id, doc = seeded_project(tr_client)
    fake_ai.queue.append(traceability_ai.AITimeoutError("Gemini n'a pas répondu."))
    response = tr_client.post(f"/api/traceability/projects/{project_id}/analyze", json={"document_id": doc["id"]})
    assert response.status_code == 504
    assert len(tr_client.get(f"/api/traceability/projects/{project_id}/requirements").json()) == 5
    assert tr_client.get(f"/api/traceability/projects/{project_id}/analyses").json() == []


# --- Documents UML et fichiers -------------------------------------------------

def test_document_keeps_only_generated_actors_present_in_text(tr_client):
    _, doc = seeded_project(tr_client)
    names = [e["name"] for e in doc["elements"]]
    assert names == ["Client"]  # "Inconnu" n'apparaît pas dans la documentation


def test_extract_elements_rejects_invented_elements(tr_client, fake_ai):
    _, doc = seeded_project(tr_client)
    fake_ai.queue.append(ELEMENTS)
    response = tr_client.post(f"/api/traceability/documents/{doc['id']}/extract-elements")
    assert response.status_code == 200
    body = response.json()
    use_cases = sorted(e["name"] for e in body["elements"] if e["kind"] == "use_case")
    actors = sorted(e["name"] for e in body["elements"] if e["kind"] == "actor")
    assert use_cases == ["Consulter le profil", "Réserver", "Se connecter"]
    assert actors == ["Administrateur", "Client"]


def test_manual_elements_and_duplicates(tr_client):
    _, doc = seeded_project(tr_client)
    url = f"/api/traceability/documents/{doc['id']}/elements"
    created = tr_client.post(url, json={"kind": "use_case", "name": "Gérer les utilisateurs", "actors": ["Administrateur"]})
    assert created.status_code == 201 and created.json()["origin"] == "manuel"
    assert tr_client.post(url, json={"kind": "use_case", "name": "Gérer les utilisateurs"}).status_code == 409
    assert tr_client.delete(f"/api/traceability/elements/{created.json()['id']}").status_code == 204
    assert tr_client.delete(f"/api/traceability/elements/{created.json()['id']}").status_code == 404


@pytest.mark.parametrize("filename, content, expected", [
    ("cahier.txt", SPEC.encode("utf-8"), 200),
    ("doc.md", UML_MARKDOWN.encode("utf-8"), 200),
    ("image.png", b"abc", 415),
    ("vide.txt", b"   \n", 400),
    ("latin1.txt", "réservation".encode("latin-1"), 400),
    ("gros.txt", b"a" * (1024 * 1024 + 1), 413),
], ids=["txt", "md", "png", "vide", "latin1", "trop-gros"])
def test_read_text_file_validation(tr_client, filename, content, expected):
    response = tr_client.post("/api/traceability/files/read-text", files={"file": (filename, content, "text/plain")})
    assert response.status_code == expected
    if expected == 200:
        assert response.json()["characters"] > 0


# --- 6 à 9. Couverture, score et persistance ---------------------------------

def run_analysis(client, fake_ai, mapping=MAPPING):
    project_id, doc = seeded_project(client)
    fake_ai.queue += [ELEMENTS, mapping]
    response = client.post(f"/api/traceability/projects/{project_id}/analyze", json={"document_id": doc["id"]})
    assert response.status_code == 200, response.text
    return project_id, doc, response.json()


def test_analysis_detects_covered_and_uncovered_requirements(tr_client, fake_ai):
    _, _, result = run_analysis(tr_client, fake_ai)
    rows = {r["reference"]: r for r in result["matrix"]["rows"]}
    assert rows["REQ-001"]["status"] == "couverte"
    assert [u["name"] for u in rows["REQ-001"]["use_cases"]] == ["Se connecter"]
    assert rows["REQ-002"]["status"] == "partielle" and rows["REQ-002"]["recommendation"]
    assert rows["REQ-004"]["status"] == "non_couverte" and rows["REQ-004"]["use_cases"] == []
    assert "Effectuer un paiement" in rows["REQ-004"]["recommendation"]
    # cas d'utilisation inventé par l'IA rejeté
    assert [u["name"] for u in rows["REQ-003"]["use_cases"]] == ["Réserver"]
    assert result["ignored_use_cases"] == ["Annuler"]


def test_non_functional_requirement_is_never_proven_by_uml(tr_client, fake_ai):
    _, _, result = run_analysis(tr_client, fake_ai)
    performance = next(r for r in result["matrix"]["rows"] if r["reference"] == "REQ-005")
    assert performance["status"] == "a_verifier"
    assert "non fonctionnelle" in performance["justification"]


def test_covered_without_existing_use_case_becomes_uncovered(tr_client, fake_ai):
    mapping = {"mappings": [{"reference": "REQ-004", "status": "couverte", "use_cases": ["Payer"], "justification": "Paiement."}]}
    _, _, result = run_analysis(tr_client, fake_ai, mapping)
    rows = {r["reference"]: r for r in result["matrix"]["rows"]}
    assert rows["REQ-004"]["status"] == "non_couverte"
    # Les exigences oubliées par l'IA ne sont jamais supposées couvertes
    assert rows["REQ-001"]["status"] == "a_verifier"


def test_coverage_rate_calculation(tr_client, fake_ai):
    _, _, result = run_analysis(tr_client, fake_ai)
    stats = result["matrix"]["stats"]
    # Fonctionnelles analysables : REQ-001 (1) + REQ-002 (0,5) + REQ-003 (1) + REQ-004 (0) = 2,5 / 4
    assert stats["analyzable_functional"] == 4
    assert stats["coverage_rate"] == 62.5
    assert (stats["total"], stats["functional"], stats["non_functional"]) == (5, 4, 1)
    assert (stats["covered"], stats["partial"], stats["uncovered"], stats["to_verify"]) == (2, 1, 1, 1)
    assert "0,5" in stats["formula"]


def test_compute_stats_edge_cases():
    assert compute_stats([])["coverage_rate"] is None
    only_nf = compute_stats([{"type": "non_fonctionnelle", "status": "a_verifier"}])
    assert only_nf["coverage_rate"] is None and only_nf["to_verify"] == 1
    rows = [{"type": "fonctionnelle", "status": "couverte"}, {"type": "fonctionnelle", "status": "a_verifier"},
            {"type": "fonctionnelle", "status": "non_analysee"}, {"type": "fonctionnelle", "status": "partielle"}]
    stats = compute_stats(rows)
    assert stats["analyzable_functional"] == 2 and stats["coverage_rate"] == 75.0
    assert stats["not_analyzed"] == 1


def test_appears_in_is_accent_and_case_insensitive():
    assert appears_in("gerer les utilisateurs", "L'Administrateur peut Gérer les utilisateurs.")
    assert not appears_in("Payer", "Le client peut réserver.")
    assert not appears_in("Client", "Clientèle")  # mot entier uniquement


def test_analysis_is_persisted_and_reloaded(tr_client, fake_ai):
    project_id, doc, result = run_analysis(tr_client, fake_ai)
    analyses = tr_client.get(f"/api/traceability/projects/{project_id}/analyses").json()
    assert len(analyses) == 1 and analyses[0]["summary"] == MAPPING["summary"]
    assert analyses[0]["stats"]["coverage_rate"] == 62.5
    assert tr_client.get(f"/api/traceability/analyses/{analyses[0]['id']}").status_code == 200

    # Simule une actualisation : un nouveau client relit la même base
    from api.endpoints import traceability
    app = FastAPI()
    app.include_router(traceability.router, prefix="/api")
    fresh = TestClient(app)
    matrix = fresh.get(f"/api/traceability/projects/{project_id}/matrix").json()
    assert matrix["document_id"] == doc["id"] and matrix["stats"]["coverage_rate"] == 62.5
    statuses = [r["coverage_status"] for r in fresh.get(f"/api/traceability/projects/{project_id}/requirements").json()]
    assert statuses == ["couverte", "partielle", "couverte", "non_couverte", "a_verifier"]

    dashboard = fresh.get("/api/traceability/dashboard").json()
    assert dashboard["projects_count"] == 1 and dashboard["analyses_count"] == 1
    assert dashboard["totals"]["coverage_rate"] == 62.5


def test_manual_correction_is_kept_by_next_ai_analysis(tr_client, fake_ai):
    project_id, doc, result = run_analysis(tr_client, fake_ai)
    use_cases = {u["name"]: u["id"] for u in result["matrix"]["use_cases"]}
    payment = next(r for r in result["matrix"]["rows"] if r["reference"] == "REQ-004")
    url = f"/api/traceability/projects/{project_id}/coverage/{payment['requirement_id']}"

    response = tr_client.put(url, json={"document_id": doc["id"], "status": "partielle",
                                        "use_case_ids": [use_cases["Réserver"]], "justification": "Le paiement est fait à la réservation."})
    assert response.status_code == 200
    row = next(r for r in response.json()["rows"] if r["reference"] == "REQ-004")
    assert row["status"] == "partielle" and row["origin"] == "manuel"

    fake_ai.queue.append(MAPPING)  # éléments déjà connus : pas de nouvelle extraction
    again = tr_client.post(f"/api/traceability/projects/{project_id}/analyze", json={"document_id": doc["id"]}).json()
    row = next(r for r in again["matrix"]["rows"] if r["reference"] == "REQ-004")
    assert row["status"] == "partielle" and row["origin"] == "manuel"
    assert len(fake_ai.prompts) == 3


def test_manual_correction_business_rules(tr_client, fake_ai):
    project_id, doc, result = run_analysis(tr_client, fake_ai)
    req_id = result["matrix"]["rows"][0]["requirement_id"]
    uc_id = result["matrix"]["use_cases"][0]["id"]
    url = f"/api/traceability/projects/{project_id}/coverage/{req_id}"
    base = {"document_id": doc["id"], "justification": "Justification"}
    assert tr_client.put(url, json={**base, "status": "couverte", "use_case_ids": []}).status_code == 400
    assert tr_client.put(url, json={**base, "status": "non_couverte", "use_case_ids": [uc_id]}).status_code == 400
    assert tr_client.put(url, json={**base, "status": "couverte", "use_case_ids": [99999]}).status_code == 400
    assert tr_client.put(url, json={**base, "status": "a_verifier"}).status_code == 200


def test_analysis_without_requirements_or_use_cases(tr_client, fake_ai):
    project_id = new_project(tr_client)
    doc = tr_client.post(f"/api/traceability/projects/{project_id}/documents",
                         json={"name": "Doc", "markdown": UML_MARKDOWN}).json()
    response = tr_client.post(f"/api/traceability/projects/{project_id}/analyze", json={"document_id": doc["id"]})
    assert response.status_code == 400 and "aucune exigence" in response.json()["detail"]

    tr_client.post(f"/api/traceability/projects/{project_id}/requirements/bulk", json={"requirements": EXTRACTED["requirements"]})
    fake_ai.queue.append({"actors": [], "use_cases": []})
    response = tr_client.post(f"/api/traceability/projects/{project_id}/analyze", json={"document_id": doc["id"]})
    assert response.status_code == 400 and "cas d'utilisation" in response.json()["detail"]


def test_document_of_another_project_is_refused(tr_client):
    project_a, doc = seeded_project(tr_client)
    project_b = new_project(tr_client, "Autre projet")
    response = tr_client.post(f"/api/traceability/projects/{project_b}/analyze", json={"document_id": doc["id"]})
    assert response.status_code == 400


def test_deleting_active_document_resets_project(tr_client):
    project_id, doc = seeded_project(tr_client)
    assert tr_client.get(f"/api/traceability/projects/{project_id}").json()["active_document_id"] == doc["id"]
    assert tr_client.delete(f"/api/traceability/documents/{doc['id']}").status_code == 204
    assert tr_client.get(f"/api/traceability/projects/{project_id}").json()["active_document_id"] is None
    assert tr_client.get(f"/api/traceability/projects/{project_id}/matrix").json()["document_id"] is None


# --- 10. Matrice et exports ---------------------------------------------------

def test_matrix_csv_export(tr_client, fake_ai):
    project_id, _, _ = run_analysis(tr_client, fake_ai)
    response = tr_client.get(f"/api/traceability/projects/{project_id}/matrix.csv")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "attachment" in response.headers["content-disposition"]
    rows = list(csv.reader(io.StringIO(response.content.decode("utf-8-sig")), delimiter=";"))
    assert rows[0][0] == "Référence" and len(rows) == 6
    assert rows[1][:2] == ["REQ-001", "Authentification du client"]
    assert rows[1][5] == "Se connecter" and rows[1][6] == "Couverte"
    assert rows[4][5] == "Aucun" and rows[4][6] == "Non couverte"


def test_report_markdown_export(tr_client, fake_ai):
    project_id, _, _ = run_analysis(tr_client, fake_ai)
    response = tr_client.get(f"/api/traceability/projects/{project_id}/report.md")
    assert response.status_code == 200
    report = response.text
    assert "# Rapport de couverture — Réservation en ligne" in report
    assert "Taux de couverture : 62.5 %" in report
    assert "dénominateur = 4" in report
    assert "REQ-004 Paiement" in report and MAPPING["suggestions"][0] in report


def test_exports_for_unknown_project_return_404(tr_client):
    assert tr_client.get("/api/traceability/projects/999/matrix.csv").status_code == 404
    assert tr_client.get("/api/traceability/projects/999/report.md").status_code == 404


def test_traceability_tables_do_not_touch_prompts(tr_client, default_prompt_name):
    init_traceability_db()  # idempotent
    with tr_connection() as conn:
        names = [r[0] for r in conn.execute("SELECT name FROM prompts")]
    assert names == [default_prompt_name]
