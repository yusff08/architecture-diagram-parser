"""Appels Gemini de la Gestion 4 (extraction d'exigences, éléments UML, traçabilité).

Contrairement à l'analyse de prompts, il n'y a PAS de fallback local déguisé :
si Gemini est indisponible, une TraceabilityAIError explicite est levée et
l'API renvoie une erreur claire (les données déjà saisies restent intactes).
"""
import os
import json
import logging
from pydantic import BaseModel, ValidationError
from dotenv import load_dotenv

from schemas.traceability import AIExtractedRequirements, AIExtractedElements, AIMappingResponse

load_dotenv()

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
GEMINI_TIMEOUT_SECONDS = int(os.getenv("GEMINI_TIMEOUT_SECONDS", "90"))


class TraceabilityAIError(Exception):
    """Erreur IA avec un code HTTP et un message compréhensible par l'utilisateur."""
    status_code = 502

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class AIConfigurationError(TraceabilityAIError):
    status_code = 503


class AITimeoutError(TraceabilityAIError):
    status_code = 504


class AIQuotaError(TraceabilityAIError):
    status_code = 429


class AIInvalidResponseError(TraceabilityAIError):
    status_code = 502


EXTRACTION_PROMPT = """Tu es un analyste fonctionnel expert en ingénierie des exigences.
Extrais les exigences du cahier des charges ci-dessous.

Règles :
1. Une exigence = un besoin unique et vérifiable. Découpe les phrases qui en contiennent plusieurs.
2. "type" vaut "fonctionnelle" (ce que le système fait pour un acteur) ou "non_fonctionnelle" (performance, sécurité, disponibilité, ergonomie, contraintes...).
3. "priority" vaut "haute", "moyenne" ou "basse" : déduis-la des mots du texte (doit, obligatoire, critique => haute ; souhaitable, pourrait => basse ; sinon moyenne).
4. "title" est court (2 à 6 mots), "description" reformule fidèlement le besoin en une phrase.
5. N'invente aucune exigence absente du texte. Réponds en français.

Réponds UNIQUEMENT avec un objet JSON de cette forme :
{"requirements": [{"title": "...", "description": "...", "type": "fonctionnelle", "priority": "haute"}]}

Cahier des charges :
\"\"\"
%s
\"\"\""""

ELEMENTS_PROMPT = """Tu analyses la documentation d'un diagramme UML de cas d'utilisation.
Liste UNIQUEMENT les acteurs et les cas d'utilisation EXPLICITEMENT écrits dans la documentation ci-dessous.
Recopie leurs noms exactement comme ils apparaissent dans le texte. N'invente, ne déduis et ne reformule aucun élément.
Pour chaque cas d'utilisation, indique les acteurs qui y participent s'ils sont cités.

Réponds UNIQUEMENT avec un objet JSON de cette forme :
{"actors": ["Client"], "use_cases": [{"name": "Se connecter", "actors": ["Client"]}]}

Documentation :
\"\"\"
%s
\"\"\""""

MAPPING_PROMPT = """Tu es un expert en traçabilité des exigences et en modélisation UML.
Pour chaque exigence, indique quels cas d'utilisation du diagramme la réalisent.

Règles strictes :
1. Utilise UNIQUEMENT les noms de la liste "Cas d'utilisation disponibles", recopiés à l'identique. N'invente aucun cas d'utilisation.
2. "status" :
   - "couverte" : un ou plusieurs cas d'utilisation réalisent entièrement l'exigence ;
   - "partielle" : un cas d'utilisation n'en réalise qu'une partie ;
   - "non_couverte" : aucun cas d'utilisation ne correspond (liste "use_cases" vide) ;
   - "a_verifier" : l'exigence n'est pas vérifiable par un diagramme de cas d'utilisation.
3. Une exigence non fonctionnelle (performance, sécurité...) doit être "a_verifier" : un cas d'utilisation ne prouve pas sa satisfaction.
4. "justification" explique le choix en citant les éléments UML réellement présents.
5. Pour "non_couverte" ou "partielle", "recommendation" propose une amélioration (ex : étudier l'ajout du cas d'utilisation "Effectuer un paiement"). Sinon null.
6. "summary" résume l'analyse en 2 ou 3 phrases ; "suggestions" liste des recommandations globales. Ce sont des recommandations : le diagramme n'est jamais modifié.

Réponds UNIQUEMENT avec un objet JSON de cette forme :
{"mappings": [{"reference": "REQ-001", "status": "couverte", "use_cases": ["Se connecter"], "justification": "...", "recommendation": null}],
 "summary": "...", "suggestions": ["..."]}

Acteurs disponibles : %s

Cas d'utilisation disponibles :
%s

Exigences :
%s"""


def _call_gemini(prompt: str) -> str:
    """Appelle Gemini et convertit toute erreur technique en TraceabilityAIError lisible."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or not api_key.strip():
        raise AIConfigurationError("La clé GEMINI_API_KEY est absente du fichier .env du backend : l'analyse IA est indisponible.")

    try:
        from google import genai
        from google.genai import types
    except ImportError:
        raise AIConfigurationError("Le SDK google-genai n'est pas installé sur le serveur (pip install google-genai).")

    try:
        client = genai.Client(
            api_key=api_key.strip(),
            http_options=types.HttpOptions(timeout=GEMINI_TIMEOUT_SECONDS * 1000),
        )
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(response_mime_type="application/json", temperature=0.1),
        )
    except Exception as e:
        raise _translate_error(e)

    text = getattr(response, "text", None)
    if not text:
        raise AIInvalidResponseError("Gemini a renvoyé une réponse vide.")
    return text


def _translate_error(error: Exception) -> TraceabilityAIError:
    logging.error(f"Traceability: Gemini call failed: {error!r}")
    code = getattr(error, "code", None) or getattr(error, "status_code", None)
    text = f"{type(error).__name__} {error}".lower()

    if code == 429 or "resource_exhausted" in text or "quota" in text or "rate limit" in text:
        return AIQuotaError("Quota Gemini dépassé : réessayez dans quelques instants. Vos données ne sont pas perdues.")
    if isinstance(error, TimeoutError) or "timeout" in text or "timed out" in text or "deadline" in text:
        return AITimeoutError(f"Gemini n'a pas répondu dans le délai imparti ({GEMINI_TIMEOUT_SECONDS} s). Réessayez.")
    if code in (401, 403) or "api key" in text or "permission" in text:
        return AIConfigurationError("La clé GEMINI_API_KEY est refusée par Google (invalide ou sans droits).")
    return TraceabilityAIError(f"Gemini est indisponible : {error}")


def _parse(text: str, model: type[BaseModel]) -> BaseModel:
    try:
        return model.model_validate(json.loads(text))
    except (json.JSONDecodeError, ValidationError, TypeError) as e:
        logging.error(f"Traceability: invalid Gemini JSON: {e}")
        raise AIInvalidResponseError("La réponse de Gemini n'a pas le format JSON attendu. Relancez l'analyse.")


def extract_requirements(specification: str) -> AIExtractedRequirements:
    return _parse(_call_gemini(EXTRACTION_PROMPT % specification), AIExtractedRequirements)


def extract_uml_elements(markdown: str) -> AIExtractedElements:
    return _parse(_call_gemini(ELEMENTS_PROMPT % markdown), AIExtractedElements)


def map_requirements(requirements: list[dict], actors: list[str], use_cases: list[str]) -> AIMappingResponse:
    req_lines = "\n".join(
        f"- {r['reference']} [{r['type']}] {r['title']} : {r['description']}" for r in requirements
    )
    uc_lines = "\n".join(f"- {name}" for name in use_cases) or "(aucun)"
    prompt = MAPPING_PROMPT % (", ".join(actors) or "(aucun)", uc_lines, req_lines)
    return _parse(_call_gemini(prompt), AIMappingResponse)
