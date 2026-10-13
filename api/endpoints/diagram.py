from fastapi import APIRouter, UploadFile, File, Form, HTTPException, status
from typing import List, Optional
from schemas.diagram import DiagramDocumentationResponse
from core.config import settings
from services.ocr import extract_text_from_image
from services.llm_service import generate_documentation
from services import prompt_service
from services.prompt_service import PromptNotFoundError

router = APIRouter()

@router.post(
    "/upload-diagram",
    response_model=DiagramDocumentationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload an architecture diagram",
    description="Uploads an image file of an architecture diagram for processing. Supports JPEG, PNG, and WebP."
)
async def upload_diagram(file: UploadFile = File(...), prompt_id: Optional[int] = Form(None)):
    # 0. Resolve the prompt to use (chosen one, or the default one)
    try:
        prompt = prompt_service.get_prompt(prompt_id) if prompt_id is not None else prompt_service.get_default_prompt()
    except PromptNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    if prompt is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Aucun prompt par défaut n'est configuré."
        )

    # 1. Validate content type
    if not file.content_type or file.content_type not in settings.ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file type: {file.content_type}. Allowed types are: {', '.join(settings.ALLOWED_IMAGE_TYPES)}"
        )
    
    # 2. Validate file size and read bytes (reading chunk by chunk)
    file_size = 0
    chunk_size = 1024 * 1024  # 1 MB chunks
    image_bytes = b""
    
    while True:
        chunk = await file.read(chunk_size)
        if not chunk:
            break
        file_size += len(chunk)
        image_bytes += chunk
        if file_size > settings.MAX_UPLOAD_SIZE:
            # File is too large
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File size exceeds the maximum limit of {settings.MAX_UPLOAD_SIZE / (1024 * 1024):.1f} MB."
            )
            
    # Reset file cursor so it can be read later by another process if needed
    await file.seek(0)
    
    # 3. Process image through PaddleOCR
    try:
        extracted_text = extract_text_from_image(image_bytes, confidence_threshold=0.70)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process image through OCR: {str(e)}"
        )
    
    # 4. Generate LLM documentation
    try:
        texts_only = [item["text"] for item in extracted_text]
        doc_json = generate_documentation(texts_only, prompt["content"])
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to generate documentation via LLM: {str(e)}"
        )
        
    return DiagramDocumentationResponse(
        system_title=doc_json.get("system_title", "Titre inconnu"),
        detected_actors=doc_json.get("detected_actors", []),
        documentation_markdown=doc_json.get("documentation_markdown", ""),
        ocr_snippets=extracted_text,
        prompt_name=prompt["name"]
    )
