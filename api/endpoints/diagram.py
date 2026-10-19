from fastapi import APIRouter, UploadFile, File, Form, HTTPException, status
from typing import List, Optional

from schemas.diagram import DiagramDocumentationResponse
from core.config import settings
from services.ocr import extract_text_from_image

from services.llm_service import (
    GeminiAPIKeyMissingError,
    GeminiDocumentationGenerationError,
    generate_documentation,
)

from services import prompt_service
from services.prompt_service import PromptNotFoundError


router = APIRouter()


@router.post(
    "/upload-diagram",
    response_model=DiagramDocumentationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload an architecture diagram",
    description=(
        "Uploads an image file of an architecture diagram for processing. "
        "Supports JPEG, PNG, and WebP."
    ),
)
async def upload_diagram(
    file: UploadFile = File(...),
    prompt_id: Optional[int] = Form(None),
):
    # 0. Resolve the prompt to use
    try:
        prompt = (
            prompt_service.get_prompt(prompt_id)
            if prompt_id is not None
            else prompt_service.get_default_prompt()
        )
    except PromptNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e

    if prompt is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Aucun prompt par défaut n'est configuré.",
        )

    # 1. Validate content type
    if (
        not file.content_type
        or file.content_type not in settings.ALLOWED_IMAGE_TYPES
    ):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=(
                f"Unsupported file type: {file.content_type}. "
                f"Allowed types: {settings.ALLOWED_IMAGE_TYPES}"
            ),
        )

    # 2. Read image
    try:
        image_bytes = await file.read()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to read uploaded file.",
        ) from e

    if not image_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    # 3. OCR extraction
    try:
        extracted_text = extract_text_from_image(image_bytes)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Failed to process image with OCR.",
        ) from e

    # 4. Generate documentation with Gemini
    try:
        texts_only = [item["text"] for item in extracted_text]

        # IMPORTANT:
        # on garde le prompt sélectionné par la gestion de ton collègue
        doc_json = generate_documentation(
            texts_only,
            prompt["content"],
        )

    except GeminiAPIKeyMissingError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The Gemini API key is not configured.",
        ) from e

    except GeminiDocumentationGenerationError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=(
                "Une erreur s'est produite lors de la génération "
                "avec l'API Gemini."
            ),
        ) from e

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to generate documentation via LLM.",
        ) from e

    return DiagramDocumentationResponse(
        system_title=doc_json.get(
            "system_title",
            "Titre inconnu",
        ),
        detected_actors=doc_json.get(
            "detected_actors",
            [],
        ),
        documentation_markdown=doc_json.get(
            "documentation_markdown",
            "",
        ),
        ocr_snippets=extracted_text,

        # On conserve aussi l'information de la gestion Prompts
        prompt_name=prompt["name"],
    )