import pytest
import json
from unittest.mock import patch, MagicMock
from services.test_generator import test_generator

def test_generate_tests_nominal_gemini():
    mock_payload = [
        {
            "analysis_name": "Système Bancaire",
            "use_case": "S'authentifier",
            "actor": "Client",
            "title": "Authentification nominale",
            "test_type": "nominal",
            "injection_id": None,
            "preconditions": "Compte créé",
            "steps": ["Saisir identifiant", "Valider"],
            "expected_result": "Session ouverte",
            "expected_behavior": "traitement_normal",
            "priority": "haute"
        },
        {
            "analysis_name": "Système Bancaire",
            "use_case": "S'authentifier",
            "actor": "Client",
            "title": "Authentification sous flou",
            "test_type": "erreur",
            "injection_id": "A_BLUR_GAUSSIAN",
            "preconditions": "Image dégradée",
            "steps": ["Uploader image floue"],
            "expected_result": "Mode dégradé",
            "expected_behavior": "mode_secours",
            "priority": "moyenne"
        }
    ]

    mock_resp = MagicMock()
    mock_resp.text = json.dumps(mock_payload)

    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = mock_resp

    with patch("services.llm_service.client", mock_client):
        res = test_generator.generate_tests(
            documentation_text="Authentifier Client",
            analysis_name="Système Bancaire",
            save_to_db=False
        )

        assert res.fallback_used is False
        assert len(res.test_cases) == 2
        assert res.test_cases[0].title == "Authentification nominale"
        assert res.test_cases[1].injection_id == "A_BLUR_GAUSSIAN"

def test_generate_tests_with_markdown_fences():
    mock_payload = [
        {
            "analysis_name": "Système E-Commerce",
            "use_case": "Commander",
            "actor": "Acheteur",
            "title": "Commande standard",
            "test_type": "nominal",
            "injection_id": None,
            "expected_result": "Commande validée",
            "expected_behavior": "traitement_normal",
            "priority": "haute"
        }
    ]
    fenced_text = f"```json\n{json.dumps(mock_payload)}\n```"

    mock_resp = MagicMock()
    mock_resp.text = fenced_text
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = mock_resp

    with patch("services.llm_service.client", mock_client):
        res = test_generator.generate_tests("Commander", "Système E-Commerce", save_to_db=False)
        assert res.fallback_used is False
        assert len(res.test_cases) == 1
        assert res.test_cases[0].title == "Commande standard"

def test_generate_tests_invalid_json_triggers_fallback():
    mock_resp = MagicMock()
    mock_resp.text = "Ceci n'est absolument pas du JSON valide {corrompu"
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = mock_resp

    with patch("services.llm_service.client", mock_client):
        res = test_generator.generate_tests("Cas S'authentifier et Client", "Système Test", save_to_db=False)
        assert res.fallback_used is True
        assert len(res.test_cases) > 0
        assert any(t.test_type == "nominal" for t in res.test_cases)
        assert any(t.test_type == "erreur" for t in res.test_cases)

def test_generate_tests_api_error_triggers_fallback():
    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = Exception("500 Google Gemini API Error")

    with patch("services.llm_service.client", mock_client):
        res = test_generator.generate_tests("Consulter Inventaire", "Gestion Stock", save_to_db=False)
        assert res.fallback_used is True
        assert len(res.test_cases) >= 3

def test_ignore_invalid_items_in_llm_response():
    mixed_payload = [
        {
            "title": "Test Invalide Sans Champs Requis"
        },
        {
            "analysis_name": "Sys",
            "use_case": "Paiement",
            "title": "Test Valide",
            "test_type": "nominal",
            "expected_result": "Succès",
            "expected_behavior": "traitement_normal",
            "priority": "basse"
        }
    ]
    mock_resp = MagicMock()
    mock_resp.text = json.dumps(mixed_payload)
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = mock_resp

    with patch("services.llm_service.client", mock_client):
        res = test_generator.generate_tests("Paiement", "Sys", save_to_db=False)
        assert res.fallback_used is False
        assert len(res.test_cases) == 1
        assert res.test_cases[0].title == "Test Valide"

def test_generate_and_save_to_db():
    mock_payload = [
        {
            "analysis_name": "Sys DB Save",
            "use_case": "Login Admin",
            "actor": "Admin",
            "title": "Test Save",
            "test_type": "nominal",
            "expected_result": "Sauvegardé",
            "expected_behavior": "traitement_normal"
        }
    ]
    mock_resp = MagicMock()
    mock_resp.text = json.dumps(mock_payload)
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = mock_resp

    with patch("services.llm_service.client", mock_client):
        res = test_generator.generate_tests("Login Admin", "Sys DB Save", save_to_db=True)
        assert res.fallback_used is False
        assert len(res.test_cases) == 1
        assert res.test_cases[0].id > 0

def test_fallback_heuristics_keywords():
    doc = """
    - login utilisateur
    - creer un compte
    - administrateur du systeme
    """
    items = test_generator._fallback_generate(doc, "Système Test")
    assert len(items) >= 3
    assert any("S'authentifier" in t.use_case for t in items)
