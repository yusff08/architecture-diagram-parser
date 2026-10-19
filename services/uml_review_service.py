from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import json
import logging
import re
import time
from json import JSONDecodeError

import httpx
from google.genai import types
from pydantic import ValidationError

from schemas.uml_review import UMLReviewResponse
from services.llm_service import GEMINI_MODEL, GeminiAPIKeyMissingError, get_gemini_client

logger = logging.getLogger(__name__)
PRIMARY_MODEL = GEMINI_MODEL
MAX_ATTEMPTS = 4
RETRY_BACKOFF_SECONDS = (1.0, 2.0, 4.0)

UML_REVIEW_PROMPT = """Tu es architecte logiciel senior, spécialiste UML et analyse des exigences.
Évalue la documentation d'un diagramme UML de cas d'utilisation en te limitant aux informations fournies. N'affirme jamais une hypothèse comme erreur certaine.
Vérifie : cohérence et responsabilités des acteurs; clarté des noms de cas; associations acteur-cas; relations <<include>>/<<extend>> si présentes; cas isolés/incohérents; doublons/responsabilités redondantes; bonnes/mauvaises pratiques UML; éléments potentiellement manquants.
Attribue un score entier de 0 à 100. Pour chaque issue, fournis titre, gravité (CRITIQUE, MOYEN ou FAIBLE), classification (ERREUR_CONFIRMEE ou AMELIORATION_POTENTIELLE), description, raison et correction précise. Les éléments absents/incertains vont dans possible_missing_elements avec confiance, pas parmi les erreurs confirmées. Liste aussi les points corrects.
Rédige improved_documentation_markdown sans inventer d'informations. Réponds uniquement par un JSON valide conforme au schéma fourni, sans Markdown englobant ni commentaire."""


class UMLReviewError(Exception):
    """Base class for errors produced while reviewing UML documentation."""


class UMLReviewTimeoutError(UMLReviewError):
    """Raised when the Gemini request times out."""


class UMLReviewAPIError(UMLReviewError):
    """Raised when the Gemini API request fails."""


class UMLReviewOverloadedError(UMLReviewError):
    """Raised when Gemini remains unavailable after all review retries."""


class UMLReviewInvalidResponseError(UMLReviewError):
    """Raised when Gemini returns JSON that does not match the response schema."""


def _gemini_response_schema() -> dict:
    schema = UMLReviewResponse.model_json_schema()

    def remove_unsupported_schema_keywords(value: object) -> None:
        if isinstance(value, dict):
            value.pop("additionalProperties", None)
            for child in value.values():
                remove_unsupported_schema_keywords(child)
        elif isinstance(value, list):
            for child in value:
                remove_unsupported_schema_keywords(child)

    remove_unsupported_schema_keywords(schema)
    return schema


def _extract_json_object(response_text: str) -> str:
    fenced_json = re.search(
        r"```(?:json)?\s*(.*?)\s*```",
        response_text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    candidate = fenced_json.group(1).strip() if fenced_json else response_text.strip()

    try:
        json.loads(candidate)
        return candidate
    except JSONDecodeError:
        start = candidate.find("{")
        if start == -1:
            raise

        try:
            _, end = json.JSONDecoder().raw_decode(candidate[start:])
        except JSONDecodeError:
            raise
        return candidate[start : start + end]


def _retry_after_seconds(error: Exception) -> float | None:
    response = getattr(error, "response", None)
    headers = getattr(response, "headers", None)
    retry_after = headers.get("Retry-After") if headers is not None else None

    if retry_after is not None:
        try:
            return max(0.0, float(retry_after))
        except (TypeError, ValueError):
            try:
                retry_at = parsedate_to_datetime(str(retry_after))
                if retry_at.tzinfo is None:
                    retry_at = retry_at.replace(tzinfo=timezone.utc)
                return max(0.0, (retry_at - datetime.now(timezone.utc)).total_seconds())
            except (TypeError, ValueError, OverflowError):
                pass

    def find_retry_delay(value: object) -> float | None:
        if isinstance(value, dict):
            for key, child in value.items():
                if str(key).casefold() in {"retry-after", "retry_after", "retrydelay"}:
                    if isinstance(child, (int, float)):
                        return max(0.0, float(child))
                    if isinstance(child, str):
                        match = re.fullmatch(r"\s*(\d+(?:\.\d+)?)s?\s*", child)
                        if match:
                            return float(match.group(1))
                nested = find_retry_delay(child)
                if nested is not None:
                    return nested
        elif isinstance(value, list):
            for child in value:
                nested = find_retry_delay(child)
                if nested is not None:
                    return nested
        return None

    return find_retry_delay(getattr(error, "details", None))


def _is_http_503(error: Exception) -> bool:
    status_code = (
        getattr(error, "code", None)
        or getattr(error, "status_code", None)
        or getattr(error, "status", None)
    )
    try:
        return int(status_code) == 503
    except (TypeError, ValueError):
        return False


def _generate_review_response(prompt: str):
    client = get_gemini_client()
    config = types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=_gemini_response_schema(),
    )

    for attempt in range(MAX_ATTEMPTS):
        try:
            response = client.models.generate_content(
                model=PRIMARY_MODEL,
                contents=prompt,
                config=config,
            )
            logger.info(
                "Gemini UML review succeeded (model=%s).",
                getattr(response, "model_version", None) or PRIMARY_MODEL,
            )
            return response
        except GeminiAPIKeyMissingError:
            raise
        except Exception as error:
            if not _is_http_503(error):
                raise
            if attempt == MAX_ATTEMPTS - 1:
                raise UMLReviewOverloadedError(
                    "Gemini remains temporarily overloaded after four attempts."
                ) from error

            retry_after = _retry_after_seconds(error)
            delay_seconds = (
                retry_after
                if retry_after is not None
                else RETRY_BACKOFF_SECONDS[attempt]
            )
            logger.warning(
                "Gemini UML review temporarily unavailable (HTTP 503); "
                "retrying attempt %s/%s after %.1f seconds.",
                attempt + 2,
                MAX_ATTEMPTS,
                delay_seconds,
            )
            time.sleep(delay_seconds)


def review_uml_documentation(documentation_markdown: str) -> UMLReviewResponse:
    prompt = (
        f"{UML_REVIEW_PROMPT}\n\n"
        "Documentation UML Markdown à analyser :\n"
        f"{documentation_markdown}"
    )

    try:
        response = _generate_review_response(prompt)
    except GeminiAPIKeyMissingError:
        raise
    except UMLReviewOverloadedError:
        raise
    except (TimeoutError, httpx.TimeoutException) as error:
        logger.warning("Gemini UML review request timed out (%s).", type(error).__name__)
        raise UMLReviewTimeoutError("The Gemini review request timed out.") from error
    except Exception as error:
        status_code = (
            getattr(error, "code", None)
            or getattr(error, "status_code", None)
            or getattr(error, "status", None)
        )
        logger.error(
            "Gemini UML review request failed (type=%s, status=%s).",
            type(error).__name__,
            status_code,
        )
        raise UMLReviewAPIError("The Gemini review request failed.") from error

    try:
        response_text = response.text
        if not response_text or not response_text.strip():
            raise ValueError("Gemini returned an empty response.")
        json_content = _extract_json_object(response_text)
        return UMLReviewResponse.model_validate_json(json_content)
    except (JSONDecodeError, ValidationError, ValueError, TypeError, AttributeError) as error:
        if isinstance(error, ValidationError):
            validation_issues = [
                {
                    "field": ".".join(str(part) for part in issue["loc"]),
                    "type": issue["type"],
                }
                for issue in error.errors(include_input=False)
            ]
            logger.warning(
                "Gemini UML review response failed schema validation: %s",
                validation_issues,
            )
        else:
            logger.warning(
                "Gemini returned an invalid UML review response (%s).",
                type(error).__name__,
            )
        raise UMLReviewInvalidResponseError(
            "Gemini returned a response that does not match the UML review schema."
        ) from error
