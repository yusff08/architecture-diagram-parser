from fastapi import APIRouter, HTTPException, UploadFile, File, Query, Response, status
from functools import wraps
from pathlib import Path
from typing import List, Optional

from schemas.traceability import (
    ProjectPayload, ProjectResponse, RequirementCreate, RequirementUpdate, RequirementBulkCreate,
    RequirementResponse, ExtractionRequest, ExtractionResponse, TextFileResponse,
    UmlDocumentCreate, UmlDocumentSummary, UmlDocumentResponse, UmlElementCreate, UmlElementResponse,
    CoverageUpdate, AnalyzeRequest, AnalysisResult, AnalysisSummary, MatrixResponse, DashboardResponse,
)
from services import traceability_service as service
from services.traceability_service import NotFoundError, ConflictError, BusinessRuleError
from services.traceability_ai import TraceabilityAIError

router = APIRouter(prefix="/traceability")

MAX_TEXT_FILE_SIZE = 1024 * 1024  # 1 Mo
ALLOWED_TEXT_EXTENSIONS = {".txt", ".md", ".markdown"}


def handle_errors(func):
    """Traduit les exceptions métier et IA en réponses HTTP avec un message lisible."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except NotFoundError as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        except ConflictError as e:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
        except BusinessRuleError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except TraceabilityAIError as e:
            raise HTTPException(status_code=e.status_code, detail=e.message)
    return wrapper


# --- Tableau de bord ---------------------------------------------------------

@router.get("/dashboard", response_model=DashboardResponse, summary="Statistiques globales et analyses récentes")
@handle_errors
def get_dashboard():
    return service.dashboard()


# --- Projets -----------------------------------------------------------------

@router.get("/projects", response_model=List[ProjectResponse], summary="Lister les projets d'analyse")
@handle_errors
def list_projects():
    return service.list_projects()


@router.post("/projects", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED, summary="Créer un projet")
@handle_errors
def create_project(data: ProjectPayload):
    return service.create_project(data)


@router.get("/projects/{project_id}", response_model=ProjectResponse, summary="Consulter un projet")
@handle_errors
def get_project(project_id: int):
    return service.get_project(project_id)


@router.put("/projects/{project_id}", response_model=ProjectResponse, summary="Modifier un projet")
@handle_errors
def update_project(project_id: int, data: ProjectPayload):
    return service.update_project(project_id, data)


@router.delete("/projects/{project_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Supprimer un projet et ses données")
@handle_errors
def delete_project(project_id: int):
    service.delete_project(project_id)


# --- Exigences ---------------------------------------------------------------

@router.post("/requirements/extract", response_model=ExtractionResponse,
             summary="Extraire les exigences d'un cahier des charges avec Gemini (non enregistrées)")
@handle_errors
def extract_requirements(data: ExtractionRequest):
    return service.extract_requirements(data.text)


@router.get("/projects/{project_id}/requirements", response_model=List[RequirementResponse], summary="Lister les exigences")
@handle_errors
def list_requirements(project_id: int):
    return service.list_requirements(project_id)


@router.post("/projects/{project_id}/requirements", response_model=RequirementResponse,
             status_code=status.HTTP_201_CREATED, summary="Ajouter une exigence")
@handle_errors
def create_requirement(project_id: int, data: RequirementCreate):
    return service.create_requirement(project_id, data)


@router.post("/projects/{project_id}/requirements/bulk", response_model=List[RequirementResponse],
             status_code=status.HTTP_201_CREATED, summary="Enregistrer les exigences validées")
@handle_errors
def bulk_create_requirements(project_id: int, data: RequirementBulkCreate):
    return service.bulk_create_requirements(project_id, data.requirements, data.replace_existing)


@router.get("/requirements/{requirement_id}", response_model=RequirementResponse, summary="Consulter une exigence")
@handle_errors
def get_requirement(requirement_id: int):
    return service.get_requirement(requirement_id)


@router.put("/requirements/{requirement_id}", response_model=RequirementResponse, summary="Modifier une exigence")
@handle_errors
def update_requirement(requirement_id: int, data: RequirementUpdate):
    return service.update_requirement(requirement_id, data)


@router.delete("/requirements/{requirement_id}", status_code=status.HTTP_204_NO_CONTENT,
               summary="Supprimer une exigence (et ses associations)")
@handle_errors
def delete_requirement(requirement_id: int):
    service.delete_requirement(requirement_id)


# --- Import de fichiers texte ------------------------------------------------

@router.post("/files/read-text", response_model=TextFileResponse, summary="Lire un fichier .txt ou .md (max 1 Mo)")
async def read_text_file(file: UploadFile = File(...)):
    extension = Path(file.filename or "").suffix.lower()
    if extension not in ALLOWED_TEXT_EXTENSIONS:
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                            detail="Format non supporté : importez un fichier .txt ou .md.")
    content = await file.read(MAX_TEXT_FILE_SIZE + 1)
    if len(content) > MAX_TEXT_FILE_SIZE:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                            detail="Le fichier dépasse la taille maximale de 1 Mo.")
    try:
        text = content.decode("utf-8-sig").strip()
    except UnicodeDecodeError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Le fichier n'est pas un texte UTF-8 valide.")
    if not text:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Le fichier est vide.")
    return {"filename": file.filename, "text": text, "characters": len(text)}


# --- Documents UML -----------------------------------------------------------

@router.get("/projects/{project_id}/documents", response_model=List[UmlDocumentSummary], summary="Lister les documents UML")
@handle_errors
def list_documents(project_id: int):
    return service.list_documents(project_id)


@router.post("/projects/{project_id}/documents", response_model=UmlDocumentResponse,
             status_code=status.HTTP_201_CREATED, summary="Ajouter une documentation UML (Markdown)")
@handle_errors
def create_document(project_id: int, data: UmlDocumentCreate):
    return service.create_document(project_id, data)


@router.put("/projects/{project_id}/documents/{document_id}/active", response_model=ProjectResponse,
            summary="Sélectionner le document UML du projet")
@handle_errors
def set_active_document(project_id: int, document_id: int):
    return service.set_active_document(project_id, document_id)


@router.get("/documents/{document_id}", response_model=UmlDocumentResponse, summary="Consulter un document UML")
@handle_errors
def get_document(document_id: int):
    return service.get_document(document_id)


@router.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Supprimer un document UML")
@handle_errors
def delete_document(document_id: int):
    service.delete_document(document_id)


@router.post("/documents/{document_id}/extract-elements", response_model=UmlDocumentResponse,
             summary="Identifier acteurs et cas d'utilisation avec Gemini")
@handle_errors
def extract_elements(document_id: int):
    return service.extract_elements(document_id)


@router.post("/documents/{document_id}/elements", response_model=UmlElementResponse,
             status_code=status.HTTP_201_CREATED, summary="Ajouter manuellement un acteur ou un cas d'utilisation")
@handle_errors
def add_element(document_id: int, data: UmlElementCreate):
    return service.add_element(document_id, data)


@router.delete("/elements/{element_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Supprimer un élément UML")
@handle_errors
def delete_element(element_id: int):
    service.delete_element(element_id)


# --- Traçabilité -------------------------------------------------------------

@router.post("/projects/{project_id}/analyze", response_model=AnalysisResult, summary="Lancer l'analyse de traçabilité (Gemini)")
@handle_errors
def analyze(project_id: int, data: AnalyzeRequest):
    return service.analyze(project_id, data.document_id)


@router.get("/projects/{project_id}/matrix", response_model=MatrixResponse, summary="Matrice de traçabilité")
@handle_errors
def get_matrix(project_id: int, document_id: Optional[int] = Query(None)):
    return service.build_matrix(project_id, document_id)


@router.put("/projects/{project_id}/coverage/{requirement_id}", response_model=MatrixResponse,
            summary="Corriger manuellement une couverture et ses associations")
@handle_errors
def update_coverage(project_id: int, requirement_id: int, data: CoverageUpdate):
    return service.update_coverage(project_id, requirement_id, data)


@router.get("/projects/{project_id}/matrix.csv", summary="Exporter la matrice en CSV")
@handle_errors
def export_matrix_csv(project_id: int, document_id: Optional[int] = Query(None)):
    content = service.export_matrix_csv(project_id, document_id)
    # BOM UTF-8 pour un affichage correct des accents dans Excel
    return Response(content="﻿" + content, media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="matrice-tracabilite-{project_id}.csv"'})


@router.get("/projects/{project_id}/report.md", summary="Exporter le rapport de couverture en Markdown")
@handle_errors
def export_report(project_id: int, document_id: Optional[int] = Query(None)):
    content = service.export_report_markdown(project_id, document_id)
    return Response(content=content, media_type="text/markdown; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="rapport-couverture-{project_id}.md"'})


@router.get("/projects/{project_id}/analyses", response_model=List[AnalysisSummary], summary="Historique des analyses")
@handle_errors
def list_analyses(project_id: int):
    return service.list_analyses(project_id)


@router.get("/analyses/{analysis_id}", response_model=AnalysisSummary, summary="Consulter une analyse")
@handle_errors
def get_analysis(analysis_id: int):
    return service.get_analysis(analysis_id)
