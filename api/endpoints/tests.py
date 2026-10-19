from fastapi import APIRouter, HTTPException, status, Query, Response
from typing import List, Optional
from schemas.tests import (
    TestCaseCreate,
    TestCaseUpdate,
    TestCaseStatusUpdate,
    TestCaseResponse,
    TestRunResponse,
    FaultInjectionCatalogItem,
    GenerateTestsRequest,
    GenerateTestsResponse,
    RunSelectionRequest,
    RunResultResponse,
    RunAllSummaryResponse,
    TestStatsResponse
)
from services.fault_injector import fault_injector, FaultInjectionDisabledError
from services.test_service import test_service
from services.test_generator import test_generator
from services.test_runner import test_runner

router = APIRouter(prefix="/tests", tags=["Gestion des Tests"])

@router.get(
    "/injections",
    response_model=List[FaultInjectionCatalogItem],
    summary="Catalogue des anomalies et injections",
    description="Retourne la liste complète des injections de fautes disponibles (Catégories A, B, C, D)."
)
def get_injections_catalog():
    return fault_injector.get_catalog()

@router.post(
    "/generate",
    response_model=GenerateTestsResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Générer des cas de test via l'IA",
    description="Analyse la documentation UML et génère des cas de test nominaux, limites et erreurs. Bascule sur un fallback local si Gemini est indisponible."
)
def generate_tests_from_documentation(payload: GenerateTestsRequest):
    try:
        response = test_generator.generate_tests(
            documentation_text=payload.documentation_text,
            analysis_name=payload.analysis_name or "Système UML",
            save_to_db=payload.save if payload.save is not None else True
        )
        return response
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Échec de la génération des tests : {str(e)}"
        )

@router.get(
    "",
    response_model=List[TestCaseResponse],
    summary="Lister les cas de test",
    description="Récupère les cas de test avec filtres optionnels sur le cas d'utilisation, type, statut, priorité et anomalie."
)
def list_test_cases(
    use_case: Optional[str] = Query(None, description="Filtre par cas d'utilisation"),
    test_type: Optional[str] = Query(None, description="Filtre par type (nominal, limite, erreur)"),
    status: Optional[str] = Query(None, description="Filtre par statut (a_faire, passe, echoue)"),
    priority: Optional[str] = Query(None, description="Filtre par priorité (haute, moyenne, basse)"),
    injection_id: Optional[str] = Query(None, description="Filtre par anomalie injectée")
):
    return test_service.get_test_cases(
        use_case=use_case,
        test_type=test_type,
        status=status,
        priority=priority,
        injection_id=injection_id
    )

@router.post(
    "",
    response_model=TestCaseResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Créer un cas de test manuellement"
)
def create_test_case(payload: TestCaseCreate):
    return test_service.create_test_case(payload)

@router.get(
    "/stats",
    response_model=TestStatsResponse,
    summary="Statistiques et scores de robustesse",
    description="Fournit la répartition des statuts, le taux de réussite global et les scores de robustesse par catégorie."
)
def get_test_statistics():
    return test_service.get_stats()

@router.get(
    "/export",
    summary="Exporter le cahier de tests",
    description="Exporte l'ensemble des tests au format Markdown ou Gherkin (.feature)."
)
def export_test_suite(format: str = Query("markdown", pattern="^(markdown|gherkin)$")):
    if format == "gherkin":
        content = test_service.export_gherkin()
        media_type = "text/plain; charset=utf-8"
        headers = {"Content-Disposition": 'attachment; filename="cahier_tests.feature"'}
    else:
        content = test_service.export_markdown()
        media_type = "text/markdown; charset=utf-8"
        headers = {"Content-Disposition": 'attachment; filename="cahier_tests.md"'}

    return Response(content=content, media_type=media_type, headers=headers)

@router.post(
    "/run-all",
    response_model=RunAllSummaryResponse,
    summary="Exécuter une sélection ou tous les tests",
    description="Exécute les tests séquentiellement sous perturbation contrôlée."
)
def run_all_tests(payload: Optional[RunSelectionRequest] = None):
    if not fault_injector.is_enabled():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="L'injection d'anomalies est désactivée. Définissez ENABLE_FAULT_INJECTION=true dans le fichier .env pour exécuter les tests."
        )

    test_ids = payload.test_ids if payload else None
    return test_runner.run_all(test_ids=test_ids)

@router.get(
    "/{test_id}",
    response_model=TestCaseResponse,
    summary="Obtenir le détail d'un cas de test"
)
def get_test_case(test_id: int):
    tc = test_service.get_test_case_by_id(test_id)
    if not tc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cas de test #{test_id} introuvable."
        )
    return tc

@router.put(
    "/{test_id}",
    response_model=TestCaseResponse,
    summary="Modifier un cas de test"
)
def update_test_case(test_id: int, payload: TestCaseUpdate):
    updated = test_service.update_test_case(test_id, payload)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cas de test #{test_id} introuvable."
        )
    return updated

@router.delete(
    "/{test_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Supprimer un cas de test"
)
def delete_test_case(test_id: int):
    deleted = test_service.delete_test_case(test_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cas de test #{test_id} introuvable."
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)

@router.patch(
    "/{test_id}/status",
    response_model=TestCaseResponse,
    summary="Modifier manuellement le statut d'un test"
)
def update_test_status(test_id: int, payload: TestCaseStatusUpdate):
    updated = test_service.update_test_status(test_id, payload.status)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cas de test #{test_id} introuvable."
        )
    return updated

@router.post(
    "/{test_id}/run",
    response_model=RunResultResponse,
    summary="Exécuter un test individuel",
    description="Applique l'anomalie configurée, exécute le pipeline, évalue la conformité et met à jour le statut."
)
def run_single_test(test_id: int):
    if not fault_injector.is_enabled():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="L'injection d'anomalies est désactivée. Définissez ENABLE_FAULT_INJECTION=true dans le fichier .env pour exécuter les tests."
        )

    tc = test_service.get_test_case_by_id(test_id)
    if not tc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cas de test #{test_id} introuvable."
        )

    return test_runner.run_test(test_id)

@router.get(
    "/{test_id}/runs",
    response_model=List[TestRunResponse],
    summary="Historique des exécutions d'un test"
)
def get_test_runs_history(test_id: int):
    tc = test_service.get_test_case_by_id(test_id)
    if not tc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cas de test #{test_id} introuvable."
        )
    return test_service.get_runs_for_test(test_id)
