import pytest
from fastapi.testclient import TestClient
from main import app
from unittest.mock import patch, MagicMock

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_env(monkeypatch):
    monkeypatch.setenv("ENABLE_FAULT_INJECTION", "true")

def test_get_injections_endpoint():
    res = client.get("/api/tests/injections")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert len(data) >= 30
    assert any(inj["id"] == "A_BLUR_GAUSSIAN" for inj in data)

def test_generate_endpoint():
    mock_resp = MagicMock()
    mock_resp.text = """[
        {
            "analysis_name": "API Gen",
            "use_case": "Auth",
            "title": "Test IA",
            "test_type": "nominal",
            "expected_result": "Succès",
            "expected_behavior": "traitement_normal"
        }
    ]"""
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = mock_resp

    with patch("services.llm_service.client", mock_client):
        res = client.post("/api/tests/generate", json={
            "documentation_text": "Cas Auth",
            "analysis_name": "API Gen",
            "save": True
        })
        assert res.status_code == 201
        data = res.json()
        assert data["total_generated"] >= 1
        assert "test_cases" in data

def test_generate_endpoint_error_500():
    with patch("services.test_generator.test_generator.generate_tests", side_effect=RuntimeError("Erreur interne critique")):
        res = client.post("/api/tests/generate", json={
            "documentation_text": "Cas Auth",
            "analysis_name": "API Gen"
        })
        assert res.status_code == 500
        assert "Échec de la génération" in res.json()["detail"]

def test_crud_endpoints():
    # 1. Create (201)
    create_payload = {
        "analysis_name": "Test CRUD",
        "use_case": "Login",
        "actor": "Admin",
        "title": "Connexion Admin",
        "test_type": "nominal",
        "steps": ["Saisir login", "Saisir mot de passe"],
        "expected_result": "Connecté",
        "expected_behavior": "traitement_normal",
        "priority": "haute"
    }
    create_res = client.post("/api/tests", json=create_payload)
    assert create_res.status_code == 201
    created = create_res.json()
    test_id = created["id"]
    assert created["title"] == "Connexion Admin"

    # 2. Get list (200)
    list_res = client.get("/api/tests?use_case=Login&test_type=nominal")
    assert list_res.status_code == 200
    assert any(t["id"] == test_id for t in list_res.json())

    # 3. Get single (200 & 404)
    get_res = client.get(f"/api/tests/{test_id}")
    assert get_res.status_code == 200
    assert get_res.json()["id"] == test_id

    not_found_res = client.get("/api/tests/999999")
    assert not_found_res.status_code == 404

    # 4. Update (200 & 404)
    put_res = client.put(f"/api/tests/{test_id}", json={"title": "Connexion Admin Modifiée"})
    assert put_res.status_code == 200
    assert put_res.json()["title"] == "Connexion Admin Modifiée"

    put_404 = client.put("/api/tests/999999", json={"title": "Inconnu"})
    assert put_404.status_code == 404

    # 5. Patch status (200 & 404)
    patch_res = client.patch(f"/api/tests/{test_id}/status", json={"status": "passe"})
    assert patch_res.status_code == 200
    assert patch_res.json()["status"] == "passe"

    patch_404 = client.patch("/api/tests/999999/status", json={"status": "passe"})
    assert patch_404.status_code == 404

    # 6. Delete (204 & 404)
    del_res = client.delete(f"/api/tests/{test_id}")
    assert del_res.status_code == 204

    del_404 = client.delete(f"/api/tests/{test_id}")
    assert del_404.status_code == 404

def test_run_endpoints():
    # Crée un test pour l'exécution
    tc_res = client.post("/api/tests", json={
        "analysis_name": "API Runner",
        "use_case": "Test Run",
        "title": "Exécution Endpoint",
        "test_type": "erreur",
        "injection_id": "D_API_NONEXISTENT_ID",
        "expected_result": "404",
        "expected_behavior": "erreur_4xx_message_clair"
    })
    test_id = tc_res.json()["id"]

    # Run unitaire
    run_res = client.post(f"/api/tests/{test_id}/run")
    assert run_res.status_code == 200
    assert run_res.json()["passed"] is True

    # 404 sur run unitaire
    run_404 = client.post("/api/tests/999999/run")
    assert run_404.status_code == 404

    # Historique des runs
    runs_res = client.get(f"/api/tests/{test_id}/runs")
    assert runs_res.status_code == 200
    assert len(runs_res.json()) >= 1

    runs_404 = client.get("/api/tests/999999/runs")
    assert runs_404.status_code == 404

    # Run All
    run_all_res = client.post("/api/tests/run-all", json={"test_ids": [test_id]})
    assert run_all_res.status_code == 200
    assert run_all_res.json()["total_executed"] == 1

def test_run_endpoints_forbidden_when_disabled(monkeypatch):
    monkeypatch.setenv("ENABLE_FAULT_INJECTION", "false")
    
    # Run unitaire bloqué (403)
    res_single = client.post("/api/tests/1/run")
    assert res_single.status_code == 403
    assert "désactivée" in res_single.json()["detail"]

    # Run All bloqué (403)
    res_all = client.post("/api/tests/run-all", json={})
    assert res_all.status_code == 403
    assert "désactivée" in res_all.json()["detail"]

def test_stats_and_exports_endpoints():
    # Stats (200)
    stats_res = client.get("/api/tests/stats")
    assert stats_res.status_code == 200
    data = stats_res.json()
    assert "total" in data
    assert "category_scores" in data
    assert "global_robustness_score" in data

    # Export Markdown (200)
    exp_md = client.get("/api/tests/export?format=markdown")
    assert exp_md.status_code == 200
    assert "text/markdown" in exp_md.headers["content-type"]
    assert "# 📋 Cahier de Recette" in exp_md.text

    # Export Gherkin (200)
    exp_gh = client.get("/api/tests/export?format=gherkin")
    assert exp_gh.status_code == 200
    assert "Fonctionnalité:" in exp_gh.text
