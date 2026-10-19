import logging

from fastapi import APIRouter, HTTPException, status

from schemas.uml_review import UMLReviewRequest, UMLReviewResponse
from services.llm_service import GeminiAPIKeyMissingError
from services.uml_review_service import (
    UMLReviewAPIError,
    UMLReviewInvalidResponseError,
    UMLReviewOverloadedError,
    UMLReviewTimeoutError,
    review_uml_documentation,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/review-documentation",
    response_model=UMLReviewResponse,
    status_code=status.HTTP_200_OK,
    summary="Review UML documentation",
    description="Critically reviews existing UML Markdown documentation without processing an image or running OCR.",
)
def review_documentation(request: UMLReviewRequest) -> UMLReviewResponse:
    try:
        return review_uml_documentation(request.documentation_markdown)
    except GeminiAPIKeyMissingError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The Gemini API key is not configured.",
        ) from error
    except UMLReviewTimeoutError as error:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="The UML review timed out. Please try again.",
        ) from error
    except UMLReviewOverloadedError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="gemini_temporarily_overloaded",
        ) from error
    except (UMLReviewAPIError, UMLReviewInvalidResponseError) as error:
        logger.error("UML review could not be completed: %s", error)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The UML review service returned an invalid response or failed.",
        ) from error
