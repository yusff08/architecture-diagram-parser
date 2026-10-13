from fastapi import APIRouter, HTTPException, status
from typing import List
from schemas.prompt import PromptCreate, PromptUpdate, PromptResponse, PromptAnalysisRequest, PromptAnalysisResponse
from services import prompt_service, prompt_analyzer
from services.prompt_service import PromptNotFoundError, PromptNameExistsError, DefaultPromptDeletionError

router = APIRouter(prefix="/prompts")


@router.get("", response_model=List[PromptResponse], summary="Lister les prompts")
def list_prompts():
    return prompt_service.list_prompts()


@router.post("/analyze", response_model=PromptAnalysisResponse, summary="Analyser la qualité d'un prompt (IA + fallback local)")
def analyze_prompt(data: PromptAnalysisRequest):
    return prompt_analyzer.analyze_prompt(data.content)


@router.get("/{prompt_id}", response_model=PromptResponse, summary="Consulter un prompt")
def get_prompt(prompt_id: int):
    try:
        return prompt_service.get_prompt(prompt_id)
    except PromptNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("", response_model=PromptResponse, status_code=status.HTTP_201_CREATED, summary="Créer un prompt")
def create_prompt(data: PromptCreate):
    try:
        return prompt_service.create_prompt(data)
    except PromptNameExistsError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.put("/{prompt_id}", response_model=PromptResponse, summary="Modifier un prompt")
def update_prompt(prompt_id: int, data: PromptUpdate):
    try:
        return prompt_service.update_prompt(prompt_id, data)
    except PromptNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except PromptNameExistsError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.delete("/{prompt_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Supprimer un prompt")
def delete_prompt(prompt_id: int):
    try:
        prompt_service.delete_prompt(prompt_id)
    except PromptNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except DefaultPromptDeletionError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.put("/{prompt_id}/default", response_model=PromptResponse, summary="Définir le prompt par défaut")
def set_default_prompt(prompt_id: int):
    try:
        return prompt_service.set_default_prompt(prompt_id)
    except PromptNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
