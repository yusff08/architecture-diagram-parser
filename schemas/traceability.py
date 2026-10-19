"""Schémas Pydantic de la Gestion 4 : exigences et traçabilité UML."""
from pydantic import BaseModel as _PydanticBaseModel, ConfigDict, Field
from typing import Optional, List, Literal

RequirementType = Literal["fonctionnelle", "non_fonctionnelle"]
Priority = Literal["haute", "moyenne", "basse"]
# "non_analysee" : aucune analyse n'a encore été faite pour cette exigence
CoverageStatus = Literal["couverte", "partielle", "non_couverte", "a_verifier", "non_analysee"]
AnalyzedStatus = Literal["couverte", "partielle", "non_couverte", "a_verifier"]
ElementKind = Literal["actor", "use_case"]

MAX_SPEC_CHARS = 50_000
MAX_MARKDOWN_CHARS = 200_000


class BaseModel(_PydanticBaseModel):
    # "   " ne doit pas passer la contrainte min_length : on retire les espaces avant validation
    model_config = ConfigDict(str_strip_whitespace=True)


# --- Projets -----------------------------------------------------------------

class ProjectPayload(BaseModel):
    name: str = Field(..., min_length=3, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    specification_text: Optional[str] = Field(None, max_length=MAX_SPEC_CHARS)


class ProjectResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    specification_text: Optional[str]
    active_document_id: Optional[int]
    requirements_count: int = 0
    created_at: str
    updated_at: str


# --- Exigences ---------------------------------------------------------------

class RequirementDraft(BaseModel):
    """Exigence proposée (par Gemini ou l'utilisateur) avant enregistrement."""
    title: str = Field(..., min_length=3, max_length=150)
    description: str = Field(..., min_length=3, max_length=2000)
    type: RequirementType
    priority: Priority = "moyenne"


class RequirementCreate(RequirementDraft):
    reference: Optional[str] = Field(None, pattern=r"^REQ-\d{3,}$")


class RequirementUpdate(RequirementDraft):
    reference: str = Field(..., pattern=r"^REQ-\d{3,}$")


class RequirementBulkCreate(BaseModel):
    requirements: List[RequirementDraft] = Field(..., min_length=1, max_length=200)
    replace_existing: bool = Field(False, description="Supprime d'abord les exigences existantes du projet")


class RequirementResponse(BaseModel):
    id: int
    project_id: int
    reference: str
    title: str
    description: str
    type: RequirementType
    priority: Priority
    coverage_status: CoverageStatus
    created_at: str
    updated_at: str


class ExtractionRequest(BaseModel):
    text: str = Field(..., min_length=20, max_length=MAX_SPEC_CHARS)


class ExtractionResponse(BaseModel):
    requirements: List[RequirementDraft]
    source: Literal["ia"] = "ia"
    model: str


class TextFileResponse(BaseModel):
    filename: str
    text: str
    characters: int


# --- Documents UML et éléments ----------------------------------------------

class UmlDocumentCreate(BaseModel):
    name: str = Field(..., min_length=3, max_length=150)
    source: Literal["generated", "import", "manual"] = "import"
    system_title: Optional[str] = Field(None, max_length=200)
    markdown: str = Field(..., min_length=20, max_length=MAX_MARKDOWN_CHARS)
    detected_actors: List[str] = Field(default_factory=list, max_length=100)


class UmlElementCreate(BaseModel):
    kind: ElementKind
    name: str = Field(..., min_length=2, max_length=150)
    actors: List[str] = Field(default_factory=list)


class UmlElementResponse(BaseModel):
    id: int
    document_id: int
    kind: ElementKind
    name: str
    actors: List[str]
    origin: Literal["ia", "manuel", "generation"]


class UmlDocumentSummary(BaseModel):
    id: int
    project_id: int
    name: str
    source: str
    system_title: Optional[str]
    actors_count: int
    use_cases_count: int
    created_at: str


class UmlDocumentResponse(UmlDocumentSummary):
    markdown: str
    elements: List[UmlElementResponse]


# --- Couverture, matrice et analyses ----------------------------------------

class CoverageUpdate(BaseModel):
    """Correction manuelle de la couverture d'une exigence (validation humaine)."""
    document_id: int
    status: AnalyzedStatus
    use_case_ids: List[int] = Field(default_factory=list, max_length=50)
    justification: str = Field(..., min_length=3, max_length=2000)
    recommendation: Optional[str] = Field(None, max_length=2000)


class AnalyzeRequest(BaseModel):
    document_id: int


class LinkedUseCase(BaseModel):
    id: int
    name: str


class MatrixRow(BaseModel):
    requirement_id: int
    reference: str
    title: str
    description: str
    type: RequirementType
    priority: Priority
    use_cases: List[LinkedUseCase]
    status: CoverageStatus
    justification: Optional[str]
    recommendation: Optional[str]
    origin: Optional[Literal["ia", "manuel"]]


class CoverageStats(BaseModel):
    total: int
    functional: int
    non_functional: int
    covered: int
    partial: int
    uncovered: int
    to_verify: int
    not_analyzed: int
    analyzable_functional: int = Field(..., description="Dénominateur : fonctionnelles couvertes + partielles + non couvertes")
    coverage_rate: Optional[float] = Field(None, description="En %, None si le dénominateur vaut 0")
    formula: str


class MatrixResponse(BaseModel):
    project_id: int
    document_id: Optional[int]
    document_name: Optional[str]
    rows: List[MatrixRow]
    stats: CoverageStats
    use_cases: List[UmlElementResponse]


class AnalysisSummary(BaseModel):
    id: int
    project_id: int
    project_name: Optional[str] = None
    document_id: Optional[int]
    document_name: Optional[str]
    model: str
    summary: str
    suggestions: List[str]
    stats: CoverageStats
    created_at: str


class AnalysisResult(BaseModel):
    analysis: AnalysisSummary
    matrix: MatrixResponse
    ignored_use_cases: List[str] = Field(default_factory=list, description="Cas cités par l'IA mais absents du document (rejetés)")


class DashboardProject(BaseModel):
    id: int
    name: str
    requirements_count: int
    active_document_id: Optional[int]
    stats: Optional[CoverageStats]
    last_analysis_at: Optional[str]


class DashboardResponse(BaseModel):
    projects_count: int
    analyses_count: int
    totals: CoverageStats
    projects: List[DashboardProject]
    recent_analyses: List[AnalysisSummary]


# --- Contrats JSON attendus de Gemini (validation stricte) -------------------

class AIExtractedRequirements(BaseModel):
    requirements: List[RequirementDraft]


class AIExtractedElement(BaseModel):
    name: str = Field(..., min_length=2, max_length=150)
    actors: List[str] = Field(default_factory=list)


class AIExtractedElements(BaseModel):
    actors: List[str] = Field(default_factory=list)
    use_cases: List[AIExtractedElement] = Field(default_factory=list)


class AIMapping(BaseModel):
    reference: str
    status: AnalyzedStatus
    use_cases: List[str] = Field(default_factory=list)
    justification: str = Field(..., min_length=3)
    recommendation: Optional[str] = None


class AIMappingResponse(BaseModel):
    mappings: List[AIMapping]
    summary: str = ""
    suggestions: List[str] = Field(default_factory=list)
