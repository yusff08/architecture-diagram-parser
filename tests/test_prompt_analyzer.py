import sys
import json
import types as pytypes

import pytest

from services import prompt_analyzer
from services.prompt_analyzer import analyze_prompt, _analyze_locally, _verdict

EXCELLENT_PROMPT = """Tu es un architecte logiciel sénior.
Analyse les textes extraits par OCR d'un diagramme UML de cas d'utilisation.
1. Identifie les acteurs du système.
2. Rédige une documentation en Markdown avec une section par acteur.
Tu dois répondre uniquement en français, sans inventer de cas d'utilisation, en 300 mots maximum."""

WEAK_PROMPT = "Fais quelque chose de bien avec ces données stp merci."


def install_fake_gemini(monkeypatch, response_text=None, error=None):
    """Replaces the google-genai SDK by a fake one: no network call in tests."""
    calls = {}

    class FakeModels:
        def generate_content(self, model, contents, config):
            calls["model"], calls["contents"] = model, contents
            if error:
                raise error
            return pytypes.SimpleNamespace(text=response_text)

    genai = pytypes.ModuleType("google.genai")
    genai.Client = lambda api_key: pytypes.SimpleNamespace(models=FakeModels())
    genai_types = pytypes.ModuleType("google.genai.types")
    genai_types.GenerateContentConfig = lambda **kwargs: kwargs
    genai.types = genai_types
    google = pytypes.ModuleType("google")
    google.genai = genai

    monkeypatch.setitem(sys.modules, "google", google)
    monkeypatch.setitem(sys.modules, "google.genai", genai)
    monkeypatch.setitem(sys.modules, "google.genai.types", genai_types)
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
    return calls


# --- Verdict -----------------------------------------------------------------

@pytest.mark.parametrize("score, expected", [(100, "Excellent"), (80, "Excellent"), (79, "Correct"),
                                             (50, "Correct"), (49, "À améliorer"), (0, "À améliorer")])
def test_verdict_thresholds(score, expected):
    assert _verdict(score) == expected


# --- Local analysis (fallback rules) -----------------------------------------

def test_local_analysis_excellent_prompt_gets_full_score():
    result = _analyze_locally(EXCELLENT_PROMPT, reason="test")
    assert result["score"] == 100
    assert result["verdict"] == "Excellent"
    assert result["suggestions"] == []
    assert result["source"] == "local" and result["fallback_reason"] == "test"


def test_local_analysis_weak_prompt_gets_low_score_and_suggestions():
    result = _analyze_locally(WEAK_PROMPT, reason="test")
    assert result["score"] == 0
    assert result["verdict"] == "À améliorer"
    assert len(result["suggestions"]) == len(prompt_analyzer.LOCAL_CRITERIA)


def test_local_analysis_single_list_line_is_not_a_structure():
    result = _analyze_locally("Tu es un expert.\n1. Analyse le diagramme UML.", reason="test")
    assert "Structure (étapes)" not in result["strengths"]
    assert "Rôle défini" in result["strengths"]


# --- AI analysis + fallback --------------------------------------------------

def test_analyze_uses_gemini_when_available(monkeypatch):
    calls = install_fake_gemini(monkeypatch, json.dumps({
        "score": 72, "strengths": ["Rôle clair"], "suggestions": ["Ajoutez un exemple."]
    }))
    result = analyze_prompt(EXCELLENT_PROMPT)
    assert result == {"score": 72, "verdict": "Correct", "strengths": ["Rôle clair"],
                      "suggestions": ["Ajoutez un exemple."], "source": "ia", "fallback_reason": None}
    assert EXCELLENT_PROMPT in calls["contents"]
    assert calls["model"] == prompt_analyzer.GEMINI_MODEL


def test_analyze_clamps_out_of_range_gemini_score(monkeypatch):
    install_fake_gemini(monkeypatch, json.dumps({"score": 140}))
    result = analyze_prompt(EXCELLENT_PROMPT)
    assert result["score"] == 100 and result["strengths"] == [] and result["source"] == "ia"


def test_analyze_falls_back_when_api_key_missing(no_api_key):
    result = analyze_prompt(EXCELLENT_PROMPT)
    assert result["source"] == "local"
    assert "GEMINI_API_KEY" in result["fallback_reason"]


def test_analyze_falls_back_when_sdk_not_installed(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
    monkeypatch.setitem(sys.modules, "google", None)  # makes "from google import genai" fail
    result = analyze_prompt(EXCELLENT_PROMPT)
    assert result["source"] == "local"


def test_analyze_falls_back_when_gemini_raises(monkeypatch):
    install_fake_gemini(monkeypatch, error=ConnectionError("API indisponible"))
    result = analyze_prompt(EXCELLENT_PROMPT)
    assert result["source"] == "local"
    assert result["fallback_reason"] == "API indisponible"
    assert result["score"] == 100


@pytest.mark.parametrize("bad_response", ["pas du json", json.dumps({"strengths": []}), json.dumps({"score": "abc"})])
def test_analyze_falls_back_when_gemini_response_is_invalid(monkeypatch, bad_response):
    install_fake_gemini(monkeypatch, bad_response)
    result = analyze_prompt(EXCELLENT_PROMPT)
    assert result["source"] == "local"
    assert "invalide" in result["fallback_reason"]
