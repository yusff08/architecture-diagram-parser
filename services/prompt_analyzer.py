"""
Analyse de la qualité d'un prompt (Atelier 4).

1. On essaie d'abord l'analyse par l'IA (Google Gemini).
2. Si l'IA n'est pas disponible (clé absente, SDK absent, erreur réseau, réponse invalide),
   on utilise une analyse locale basée sur des règles simples (fallback).
"""
import os
import re
import json
import logging
from dotenv import load_dotenv

load_dotenv()

GEMINI_MODEL = "gemini-3.8-flash"

# (label, points, regex, suggestion if missing)
LOCAL_CRITERIA = [
    ("Rôle défini", 15,
     r"\b(tu es|vous [êe]tes|en tant que|agis comme|you are|act as)\b",
     "Définissez un rôle pour l'IA (ex : « Tu es un architecte logiciel sénior »)."),
    ("Tâche claire", 20,
     r"\b(analyse|rédige|génère|genere|identifie|déduis|deduis|résume|resume|explique|liste|décris|decris|produis|écris|ecris|cartographie)",
     "Indiquez clairement la tâche avec un verbe d'action (analyse, rédige, identifie...)."),
    ("Contexte", 15,
     r"(uml|diagramme|cas d'utilisation|use case|acteur|ocr|système|systeme|architecture)",
     "Donnez du contexte : sur quoi porte l'analyse (diagramme UML, acteurs, OCR...)."),
    ("Structure (étapes)", 15,
     None,  # checked by _has_structure()
     "Structurez les instructions en étapes numérotées ou en liste à puces."),
    ("Contraintes", 15,
     r"\b(doit|doivent|ne pas|jamais|uniquement|seulement|maximum|minimum|au moins|sans|must|only|never)\b",
     "Ajoutez des contraintes (longueur maximale, ce qu'il ne faut pas faire...)."),
    ("Format de sortie", 10,
     r"(markdown|tableau|section|titre|format|liste|puces|paragraphe)",
     "Précisez le format de sortie attendu (Markdown, tableau, sections...)."),
    ("Longueur suffisante", 10,
     None,  # checked by word count
     "Le prompt est trop court : détaillez davantage vos attentes (au moins 30 mots)."),
]

MIN_WORDS = 30

ANALYSIS_META_PROMPT = """Tu es un expert en prompt engineering.
Évalue la qualité du prompt ci-dessous, destiné à un LLM qui génère une documentation technique à partir des textes extraits d'un diagramme UML de cas d'utilisation.
Critères : rôle défini, tâche claire, contexte, structure, contraintes, format de sortie, précision.

Réponds UNIQUEMENT avec un objet JSON valide de cette forme :
{
  "score": <entier entre 0 et 100>,
  "strengths": ["point fort 1", "..."],
  "suggestions": ["suggestion d'amélioration concrète 1", "..."]
}

Prompt à évaluer :
\"\"\"
%s
\"\"\""""


def _verdict(score: int) -> str:
    if score >= 80:
        return "Excellent"
    if score >= 50:
        return "Correct"
    return "À améliorer"


def _has_structure(content: str) -> bool:
    list_lines = re.findall(r"^\s*(\d+[.)]|[-*•])\s+", content, flags=re.MULTILINE)
    return len(list_lines) >= 2


def _analyze_locally(content: str, reason: str) -> dict:
    """Fallback : analyse par règles, sans aucune dépendance externe."""
    text = content.lower()
    score = 0
    strengths, suggestions = [], []

    for label, points, pattern, suggestion in LOCAL_CRITERIA:
        if label == "Structure (étapes)":
            ok = _has_structure(content)
        elif label == "Longueur suffisante":
            ok = len(content.split()) >= MIN_WORDS
        else:
            ok = re.search(pattern, text) is not None

        if ok:
            score += points
            strengths.append(label)
        else:
            suggestions.append(suggestion)

    return {
        "score": score,
        "verdict": _verdict(score),
        "strengths": strengths,
        "suggestions": suggestions,
        "source": "local",
        "fallback_reason": reason,
    }


def _analyze_with_ai(content: str) -> dict:
    """Analyse par Gemini. Lève une exception si l'IA n'est pas utilisable."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("Clé GEMINI_API_KEY absente.")

    # Imported here so that a missing SDK also triggers the fallback
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key.strip())
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=ANALYSIS_META_PROMPT % content,
        config=types.GenerateContentConfig(response_mime_type="application/json"),
    )

    try:
        data = json.loads(response.text)
        score = max(0, min(100, int(data["score"])))
        strengths = [str(s) for s in data.get("strengths", [])]
        suggestions = [str(s) for s in data.get("suggestions", [])]
    except (ValueError, KeyError, TypeError) as e:
        raise ValueError(f"Réponse de Gemini invalide : {e}")

    return {
        "score": score,
        "verdict": _verdict(score),
        "strengths": strengths,
        "suggestions": suggestions,
        "source": "ia",
        "fallback_reason": None,
    }


def analyze_prompt(content: str) -> dict:
    """Point d'entrée : IA d'abord, analyse locale si l'IA échoue."""
    try:
        return _analyze_with_ai(content)
    except Exception as e:
        logging.warning(f"Prompt analysis: AI unavailable, using local fallback ({e})")
        return _analyze_locally(content, reason=str(e))
