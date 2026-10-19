import importlib
import sys
import types

from fastapi import FastAPI
from fastapi.testclient import TestClient

VALID = {"name": "Résumé court", "description": "5 lignes max",
         "content": "Tu es un analyste. Résume le diagramme UML en 5 lignes."}


def create(client, **overrides):
    return client.post("/api/prompts", json={**VALID, **overrides})


# --- CRUD routes -------------------------------------------------------------

def test_list_returns_default_prompt(client, default_prompt_name):
    response = client.get("/api/prompts")
    assert response.status_code == 200
    assert response.json()[0]["name"] == default_prompt_name


def test_create_returns_201(client):
    response = create(client)
    assert response.status_code == 201
    assert response.json()["name"] == "Résumé court"


def test_create_duplicate_name_returns_409(client):
    create(client)
    assert create(client).status_code == 409


def test_create_invalid_data_returns_422(client):
    assert create(client, name="ab").status_code == 422
    assert create(client, content="trop court").status_code == 422
    assert create(client, description="x" * 256).status_code == 422


def test_get_returns_200_or_404(client):
    prompt_id = create(client).json()["id"]
    assert client.get(f"/api/prompts/{prompt_id}").status_code == 200
    assert client.get("/api/prompts/999").status_code == 404


def test_update_returns_200_404_409(client, default_prompt_name):
    prompt_id = create(client).json()["id"]
    ok = client.put(f"/api/prompts/{prompt_id}", json={**VALID, "name": "Nouveau nom"})
    assert ok.status_code == 200 and ok.json()["name"] == "Nouveau nom"
    assert client.put("/api/prompts/999", json=VALID).status_code == 404
    assert client.put(f"/api/prompts/{prompt_id}", json={**VALID, "name": default_prompt_name}).status_code == 409


def test_delete_returns_204_404_400(client):
    prompt_id = create(client).json()["id"]
    default_id = client.get("/api/prompts").json()[0]["id"]
    assert client.delete(f"/api/prompts/{prompt_id}").status_code == 204
    assert client.delete(f"/api/prompts/{prompt_id}").status_code == 404
    refused = client.delete(f"/api/prompts/{default_id}")
    assert refused.status_code == 400 and "défaut" in refused.json()["detail"]


def test_set_default_returns_200_or_404(client):
    prompt_id = create(client).json()["id"]
    response = client.put(f"/api/prompts/{prompt_id}/default")
    assert response.status_code == 200 and response.json()["is_default"] is True
    assert client.get("/api/prompts").json()[0]["id"] == prompt_id
    assert client.put("/api/prompts/999/default").status_code == 404


# --- Quality analysis route (Atelier 4) --------------------------------------

def test_analyze_returns_local_result_without_api_key(client, no_api_key):
    response = client.post("/api/prompts/analyze", json={"content": VALID["content"]})
    assert response.status_code == 200
    body = response.json()
    assert body["source"] == "local" and 0 <= body["score"] <= 100


def test_analyze_too_short_content_returns_422(client):
    assert client.post("/api/prompts/analyze", json={"content": "court"}).status_code == 422


# --- Upload uses the chosen prompt -------------------------------------------

def make_upload_client(monkeypatch):
    """Loads the diagram router with fake OCR + LLM services (no PaddleOCR, no Gemini)."""
    received = {}
    ocr = types.ModuleType("services.ocr")
    ocr.extract_text_from_image = lambda image_bytes, confidence_threshold=0.70: [{"text": "Client", "confidence": 0.9}]
    llm = types.ModuleType("services.llm_service")

    def fake_generate(texts, prompt_instructions):
        received["instructions"] = prompt_instructions
        return {"system_title": "Boutique", "detected_actors": ["Client"], "documentation_markdown": "# Doc"}

    llm.generate_documentation = fake_generate
    # Error classes imported by api/endpoints/diagram.py (added with the UML review module)
    llm.GeminiAPIKeyMissingError = type("GeminiAPIKeyMissingError", (RuntimeError,), {})
    llm.GeminiDocumentationGenerationError = type("GeminiDocumentationGenerationError", (RuntimeError,), {})
    monkeypatch.setitem(sys.modules, "services.ocr", ocr)
    monkeypatch.setitem(sys.modules, "services.llm_service", llm)
    # Restore the real module afterwards (sys.modules entry AND the package attribute),
    # otherwise other tests patching "api.endpoints.diagram.*" would patch this fake copy
    import api.endpoints as endpoints_pkg
    monkeypatch.setattr(endpoints_pkg, "diagram", getattr(endpoints_pkg, "diagram", None), raising=False)
    monkeypatch.delitem(sys.modules, "api.endpoints.diagram", raising=False)
    diagram = importlib.import_module("api.endpoints.diagram")
    monkeypatch.delitem(sys.modules, "api.endpoints.diagram")

    app = FastAPI()
    app.include_router(diagram.router, prefix="/api")
    return TestClient(app), received


IMAGE = {"file": ("diagram.png", b"fake-image", "image/png")}


def test_upload_without_prompt_id_uses_default_prompt(client, monkeypatch, default_prompt_name):
    upload_client, received = make_upload_client(monkeypatch)
    response = upload_client.post("/api/upload-diagram", files=IMAGE)
    assert response.status_code == 201
    assert response.json()["prompt_name"] == default_prompt_name
    assert "Architecte Logiciel" in received["instructions"]


def test_upload_with_prompt_id_uses_chosen_prompt(client, monkeypatch):
    prompt_id = create(client).json()["id"]
    upload_client, received = make_upload_client(monkeypatch)
    response = upload_client.post("/api/upload-diagram", files=IMAGE, data={"prompt_id": str(prompt_id)})
    assert response.json()["prompt_name"] == "Résumé court"
    assert received["instructions"] == VALID["content"]


def test_upload_with_unknown_prompt_id_returns_404(client, monkeypatch):
    upload_client, _ = make_upload_client(monkeypatch)
    response = upload_client.post("/api/upload-diagram", files=IMAGE, data={"prompt_id": "999"})
    assert response.status_code == 404


def test_upload_without_any_default_prompt_returns_500(client, monkeypatch):
    from core.database import get_connection
    with get_connection() as conn:
        conn.execute("DELETE FROM prompts")
    upload_client, _ = make_upload_client(monkeypatch)
    assert upload_client.post("/api/upload-diagram", files=IMAGE).status_code == 500
