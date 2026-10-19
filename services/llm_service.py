import os
import json
import logging
import time

from functools import lru_cache
from pathlib import Path

from google import genai
from google.genai import types
from dotenv import load_dotenv


# Charge le .env situé à la racine du projet
load_dotenv(Path(__file__).resolve().parents[1] / ".env")


class GeminiAPIKeyMissingError(RuntimeError):
    """Raised when a Gemini operation is requested without an API key."""


class GeminiDocumentationGenerationError(RuntimeError):
    """Raised when Gemini cannot produce valid diagram documentation."""


GEMINI_MODEL = "gemini-3.8-flash"
GEMINI_MAX_ATTEMPTS = 3


@lru_cache(maxsize=1)
def get_gemini_client() -> genai.Client:
    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key or not api_key.strip():
        raise GeminiAPIKeyMissingError(
            "GEMINI_API_KEY is not configured."
        )

    return genai.Client(api_key=api_key.strip())


def generate_content_with_retry(
    *,
    model: str,
    contents: str,
    config=None
):
    """
    Appelle Gemini avec retry en cas d'indisponibilité HTTP 503.
    """

    for attempt in range(GEMINI_MAX_ATTEMPTS):
        try:
            return get_gemini_client().models.generate_content(
                model=model,
                contents=contents,
                config=config,
            )

        except GeminiAPIKeyMissingError:
            raise

        except Exception as error:
            status_code = (
                getattr(error, "code", None)
                or getattr(error, "status_code", None)
                or getattr(error, "status", None)
            )

            if (
                status_code != 503
                or attempt == GEMINI_MAX_ATTEMPTS - 1
            ):
                raise

            delay_seconds = 0.5 * (2 ** attempt)

            logging.warning(
                "Gemini temporarily unavailable (HTTP 503); "
                "retrying attempt %s/%s after %.1f seconds.",
                attempt + 2,
                GEMINI_MAX_ATTEMPTS,
                delay_seconds,
            )

            time.sleep(delay_seconds)


# IMPORTANT :
# Ce contrat JSON reste fixe.
# Le prompt fonctionnel reste géré par la Gestion des Prompts.
JSON_FORMAT_INSTRUCTIONS = """
Ta réponse DOIT être UNIQUEMENT un objet JSON valide suivant exactement
cette structure, sans aucun texte ou bloc markdown supplémentaire :

{
  "system_title": "Nom du système déduit",
  "detected_actors": ["acteur1", "acteur2"],
  "documentation_markdown": "# Documentation Technique\\n..."
}
"""


def generate_documentation(
    ocr_texts: list[str],
    prompt_instructions: str
) -> dict:

    if not ocr_texts:
        return {
            "system_title": "Inconnu",
            "detected_actors": [],
            "documentation_markdown":
                "Aucun texte détecté dans le diagramme.",
        }

    try:
        # On garde le prompt provenant de la gestion du collègue
        prompt = (
            f"{prompt_instructions}\n\n"
            f"{JSON_FORMAT_INSTRUCTIONS}\n\n"
            "Voici les textes extraits par OCR :\n"
        )

        for text in ocr_texts:
            prompt += f"- {text}\n"

        response = generate_content_with_retry(
            model=GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            ),
        )

        if not response.text or not response.text.strip():
            raise ValueError(
                "Gemini returned an empty documentation response."
            )

        documentation = json.loads(response.text)

        if not isinstance(documentation, dict):
            raise ValueError(
                "Gemini returned an invalid documentation object."
            )

        system_title = documentation.get("system_title")
        detected_actors = documentation.get("detected_actors")
        documentation_markdown = documentation.get(
            "documentation_markdown"
        )

        if (
            not isinstance(system_title, str)
            or not system_title.strip()
            or not isinstance(detected_actors, list)
            or not all(
                isinstance(actor, str)
                for actor in detected_actors
            )
            or not isinstance(documentation_markdown, str)
            or not documentation_markdown.strip()
        ):
            raise ValueError(
                "Gemini returned incomplete documentation."
            )

        return {
            "system_title": system_title.strip(),
            "detected_actors": detected_actors,
            "documentation_markdown":
                documentation_markdown.strip(),
        }

    except GeminiAPIKeyMissingError:
        raise

    except Exception as error:
        logging.error(
            "Error during Gemini generation (%s).",
            type(error).__name__,
        )

        raise GeminiDocumentationGenerationError(
            "Une erreur s'est produite lors de la génération "
            "avec l'API Gemini."
        ) from error