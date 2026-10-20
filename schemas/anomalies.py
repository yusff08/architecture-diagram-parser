from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Literal

from schemas.tests import TestCaseResponse

Severity = Literal["critique", "majeure", "mineure"]
AnomalyCategory = Literal["structure", "coherence", "qualite_donnees", "securite"]
AnomalySource = Literal["regle", "ia", "regle+ia"]


class DetectedAnomaly(BaseModel):
    id: str = Field(..., description="Identifiant de l'anomalie (ANO-001...)")
    rule: str = Field(..., description="Code de la règle ou 'IA_SEMANTIQUE' pour une anomalie trouvée par Gemini")
    category: AnomalyCategory
    severity: Severity
    title: str
    description: str
    elements: List[str] = Field(default_factory=list, description="Éléments UML concernés")
    suggestion: str
    injection_id: Optional[str] = Field(None, description="Anomalie du catalogue d'injection qui reproduit ce défaut")
    source: AnomalySource
    confidence: float = Field(..., ge=0.0, le=1.0)
    confirmed_by_ai: Optional[bool] = Field(None, description="Verdict de Gemini (None si l'IA n'a pas été consultée)")
    ai_explanation: Optional[str] = None


class UMLRelation(BaseModel):
    source: str
    type: Literal["include", "extend"]
    target: str


class ExtractedUMLModel(BaseModel):
    system_name: Optional[str] = None
    actors: List[str] = Field(default_factory=list)
    use_cases: List[str] = Field(default_factory=list)
    relations: List[UMLRelation] = Field(default_factory=list)
    associations: Dict[str, List[str]] = Field(default_factory=dict, description="Cas d'utilisation -> acteurs liés")


class DetectAnomaliesRequest(BaseModel):
    documentation_text: str = Field(..., min_length=1, max_length=200_000, description="Documentation UML ou textes extraits à analyser")
    analysis_name: Optional[str] = Field("Système UML", description="Nom du système ou de l'analyse")
    use_ai: bool = Field(True, description="Faire valider et enrichir la détection par Gemini")
    generate_tests: bool = Field(False, description="Créer un cas de test de robustesse pour chaque anomalie détectée")
    save: bool = Field(True, description="Enregistrer les cas de test générés en base")


class DetectAnomaliesResponse(BaseModel):
    analysis_name: str
    anomalies: List[DetectedAnomaly]
    quality_score: int = Field(..., ge=0, le=100, description="Score de qualité du modèle (100 = aucune anomalie)")
    by_severity: Dict[str, int]
    by_source: Dict[str, int]
    extracted: ExtractedUMLModel
    ai_used: bool
    fallback_used: bool = Field(False, description="Gemini était demandé mais indisponible : seules les règles ont été appliquées")
    ai_summary: Optional[str] = None
    generated_tests: List[TestCaseResponse] = Field(default_factory=list)
    message: str
