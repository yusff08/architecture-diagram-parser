import json
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from main import app
from services.llm_service import (
    GeminiAPIKeyMissingError,
    GeminiDocumentationGenerationError,
)


@pytest.fixture
def client():
    return TestClient(app)


def valid_review_payload():
    return {
        "score": 86,
        "summary": "La documentation est globalement cohérente.",
        "issues": [
            {
                "title": "Nom trop général",
                "severity": "FAIBLE",
                "classification": "AMELIORATION_POTENTIELLE",
                "description": "Un cas d'utilisation porte un nom peu précis.",
                "reason": "Le nom ne décrit pas clairement le résultat attendu.",
                "suggestion": "Employer un verbe et un complément explicites.",
            }
        ],
        "strengths": ["Les responsabilités des acteurs sont identifiables."],
        "possible_missing_elements": [
            {
                "element": "Gestion des erreurs",
                "reason": "Aucun comportement d'erreur n'est mentionné.",
                "confidence": "faible",
            }
        ],
        "improved_documentation_markdown": "# Documentation UML améliorée",
    }


def mock_gemini(monkeypatch, *, text=None, error=None):
    generate_content = MagicMock()
    if error is not None:
        generate_content.side_effect = error
    else:
        generate_content.return_value = SimpleNamespace(text=text)

    fake_client = SimpleNamespace(
        models=SimpleNamespace(generate_content=generate_content)
    )
    monkeypatch.setattr(
        "services.uml_review_service.get_gemini_client", lambda: fake_client
    )
    return generate_content


def test_review_documentation_returns_validated_gemini_review(client, monkeypatch):
    documentation = "# Gestion des commandes\nActeur : Client"
    payload = valid_review_payload()
    generate_content = mock_gemini(
        monkeypatch,
        text=f"```json\n{json.dumps(payload, ensure_ascii=False)}\n```",
    )

    response = client.post(
        "/api/review-documentation",
        json={"documentation_markdown": documentation},
    )

    assert response.status_code == 200
    result = response.json()
    assert result["score"] == payload["score"]
    assert result["summary"] == payload["summary"]
    assert result["issues"] == payload["issues"]
    assert result["strengths"] == payload["strengths"]
    assert result["possible_missing_elements"] == payload["possible_missing_elements"]
    assert (
        result["improved_documentation_markdown"]
        == payload["improved_documentation_markdown"]
    )
    assert documentation in generate_content.call_args.kwargs["contents"]


def test_review_documentation_rejects_empty_markdown(client):
    response = client.post(
        "/api/review-documentation",
        json={"documentation_markdown": " \n\t "},
    )

    assert response.status_code == 422


def test_review_documentation_returns_503_when_api_key_is_missing(
    client, monkeypatch
):
    monkeypatch.setattr(
        "services.uml_review_service.get_gemini_client",
        MagicMock(side_effect=GeminiAPIKeyMissingError()),
    )

    response = client.post(
        "/api/review-documentation",
        json={"documentation_markdown": "# Documentation"},
    )

    assert response.status_code == 503


def test_review_documentation_returns_504_on_gemini_timeout(client, monkeypatch):
    mock_gemini(monkeypatch, error=TimeoutError("request timed out"))

    response = client.post(
        "/api/review-documentation",
        json={"documentation_markdown": "# Documentation"},
    )

    assert response.status_code == 504


def test_review_documentation_returns_502_on_gemini_api_error(client, monkeypatch):
    mock_gemini(monkeypatch, error=RuntimeError("Gemini API failure"))

    response = client.post(
        "/api/review-documentation",
        json={"documentation_markdown": "# Documentation"},
    )

    assert response.status_code == 502


def test_review_retries_503_four_times_with_configured_backoff(
    client, monkeypatch
):
    from services import uml_review_service

    class TemporaryGeminiError(Exception):
        code = 503

    generate_content = MagicMock(
        side_effect=TemporaryGeminiError("temporary service unavailability")
    )
    fake_client = SimpleNamespace(
        models=SimpleNamespace(generate_content=generate_content)
    )
    sleep_mock = MagicMock()
    monkeypatch.setattr(
        uml_review_service, "get_gemini_client", lambda: fake_client
    )
    monkeypatch.setattr(uml_review_service.time, "sleep", sleep_mock)

    response = client.post(
        "/api/review-documentation",
        json={"documentation_markdown": "# Documentation"},
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "gemini_temporarily_overloaded"
    assert generate_content.call_count == 4
    assert [call.args[0] for call in sleep_mock.call_args_list] == [1.0, 2.0, 4.0]


def test_review_uses_retry_after_header_when_available(monkeypatch):
    from services import uml_review_service

    class TemporaryGeminiError(Exception):
        code = 503

        def __init__(self, retry_after=None):
            super().__init__("temporary service unavailability")
            self.response = (
                SimpleNamespace(headers={"Retry-After": retry_after})
                if retry_after is not None
                else None
            )

    generate_content = MagicMock(
        side_effect=[
            TemporaryGeminiError("3"),
            TemporaryGeminiError(),
            SimpleNamespace(text=json.dumps(valid_review_payload(), ensure_ascii=False)),
        ]
    )
    fake_client = SimpleNamespace(
        models=SimpleNamespace(generate_content=generate_content)
    )
    sleep_mock = MagicMock()
    monkeypatch.setattr(
        uml_review_service, "get_gemini_client", lambda: fake_client
    )
    monkeypatch.setattr(uml_review_service.time, "sleep", sleep_mock)

    result = uml_review_service.review_uml_documentation("# Documentation")

    assert result.score == 86
    assert [call.args[0] for call in sleep_mock.call_args_list] == [3.0, 2.0]


def test_review_uses_retry_delay_from_gemini_error_details():
    from services.uml_review_service import _retry_after_seconds

    error = RuntimeError("temporary service unavailability")
    error.details = {
        "details": [{"@type": "google.rpc.RetryInfo", "retryDelay": "2.5s"}]
    }

    assert _retry_after_seconds(error) == 2.5


def test_review_documentation_returns_502_on_invalid_gemini_json(
    client, monkeypatch
):
    mock_gemini(monkeypatch, text="{not valid JSON")

    response = client.post(
        "/api/review-documentation",
        json={"documentation_markdown": "# Documentation"},
    )

    assert response.status_code == 502


@pytest.mark.parametrize(
    "invalid_change",
    [
        pytest.param(
            lambda payload: payload.update(score=101),
            id="score-above-100",
        ),
        pytest.param(
            lambda payload: payload.pop("summary"),
            id="required-field-missing",
        ),
        pytest.param(
            lambda payload: payload["issues"][0].update(severity="URGENT"),
            id="invalid-severity",
        ),
    ],
)
def test_review_documentation_returns_502_when_gemini_schema_is_invalid(
    client, monkeypatch, invalid_change
):
    payload = valid_review_payload()
    invalid_change(payload)
    mock_gemini(monkeypatch, text=json.dumps(payload, ensure_ascii=False))

    response = client.post(
        "/api/review-documentation",
        json={"documentation_markdown": "# Documentation"},
    )

    assert response.status_code == 502


def test_existing_upload_route_keeps_its_response_contract(client, monkeypatch):
    extracted_text = [{"text": "Client", "confidence": 0.95}]
    generated_documentation = {
        "system_title": "Gestion des commandes",
        "detected_actors": ["Client"],
        "documentation_markdown": "# Gestion des commandes",
    }
    extract_mock = MagicMock(return_value=extracted_text)
    documentation_mock = MagicMock(return_value=generated_documentation)
    monkeypatch.setattr("api.endpoints.diagram.extract_text_from_image", extract_mock)
    monkeypatch.setattr(
        "api.endpoints.diagram.generate_documentation",
        documentation_mock,
    )

    response = client.post(
        "/api/upload-diagram",
        files={"file": ("diagram.png", b"mock image bytes", "image/png")},
    )

    assert response.status_code == 201
    assert set(response.json()) == {
        "system_title",
        "detected_actors",
        "documentation_markdown",
        "ocr_snippets",
    }
    assert response.json()["system_title"] == generated_documentation["system_title"]
    assert response.json()["ocr_snippets"] == extracted_text
    extract_mock.assert_called_once()
    documentation_mock.assert_called_once_with(["Client"])


def test_documentation_generation_retries_503_and_succeeds(monkeypatch):
    from services import llm_service

    class TemporaryGeminiError(Exception):
        code = 503

    generated = {
        "system_title": "Gestion des commandes",
        "detected_actors": ["Client"],
        "documentation_markdown": (
            "# Gestion des commandes\n\n## Acteurs\n- Client\n\n"
            "## Cas d'utilisation\n- Passer commande"
        ),
    }
    generate_content = MagicMock(
        side_effect=[
            TemporaryGeminiError("temporary service unavailability"),
            TemporaryGeminiError("temporary service unavailability"),
            SimpleNamespace(text=json.dumps(generated, ensure_ascii=False)),
        ]
    )
    fake_client = SimpleNamespace(
        models=SimpleNamespace(generate_content=generate_content)
    )
    monkeypatch.setattr(llm_service, "get_gemini_client", lambda: fake_client)
    sleep_mock = MagicMock()
    monkeypatch.setattr(llm_service.time, "sleep", sleep_mock)

    result = llm_service.generate_documentation(["Client", "Passer commande"])

    assert result == generated
    assert generate_content.call_count == 3
    assert [call.args[0] for call in sleep_mock.call_args_list] == [0.5, 1.0]


def test_documentation_generation_stops_after_three_503_attempts(monkeypatch):
    from services import llm_service

    class TemporaryGeminiError(Exception):
        code = 503

    generate_content = MagicMock(
        side_effect=TemporaryGeminiError("temporary service unavailability")
    )
    fake_client = SimpleNamespace(
        models=SimpleNamespace(generate_content=generate_content)
    )
    monkeypatch.setattr(llm_service, "get_gemini_client", lambda: fake_client)
    monkeypatch.setattr(llm_service.time, "sleep", MagicMock())

    with pytest.raises(GeminiDocumentationGenerationError):
        llm_service.generate_documentation(["Client", "Passer commande"])

    assert generate_content.call_count == 3


def test_upload_returns_502_instead_of_success_shaped_documentation(
    client, monkeypatch
):
    monkeypatch.setattr(
        "api.endpoints.diagram.extract_text_from_image",
        MagicMock(return_value=[{"text": "Client", "confidence": 0.95}]),
    )
    monkeypatch.setattr(
        "api.endpoints.diagram.generate_documentation",
        MagicMock(side_effect=GeminiDocumentationGenerationError()),
    )

    response = client.post(
        "/api/upload-diagram",
        files={"file": ("diagram.png", b"mock image bytes", "image/png")},
    )

    assert response.status_code == 502
    assert response.json()["detail"] == (
        "Une erreur s'est produite lors de la génération avec l'API Gemini."
    )
