from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any, Literal

TestType = Literal["nominal", "limite", "erreur"]
ExpectedBehavior = Literal[
    "erreur_4xx_message_clair",
    "mode_secours",
    "traitement_normal",
    "rejet_propre"
]
Priority = Literal["haute", "moyenne", "basse"]
TestStatus = Literal["a_faire", "passe", "echoue"]
RunStatus = Literal["passe", "echoue", "erreur"]

class TestCaseBase(BaseModel):
    __test__ = False
    analysis_name: str = Field(..., description="Nom de l'analyse UML source")
    use_case: str = Field(..., description="Cas d'utilisation UML testé")
    actor: Optional[str] = Field(None, description="Acteur principal associé")
    title: str = Field(..., description="Titre descriptif du test")
    test_type: TestType = Field(..., description="Type de test : nominal, limite ou erreur")
    injection_id: Optional[str] = Field(None, description="Identifiant de l'injection d'anomalie associée")
    preconditions: Optional[str] = Field(None, description="Préconditions requises")
    steps: List[str] = Field(default_factory=list, description="Liste ordonnée des étapes de test")
    expected_result: str = Field(..., description="Résultat métier attendu")
    expected_behavior: ExpectedBehavior = Field(
        ...,
        description="Comportement système attendu face à l'entrée"
    )
    priority: Priority = Field(default="moyenne", description="Priorité du test")
    status: TestStatus = Field(default="a_faire", description="Statut d'exécution du test")
    generated_by_llm: bool = Field(default=False, description="Indique si le test a été généré par l'IA")

class TestCaseCreate(TestCaseBase):
    __test__ = False

class TestCaseUpdate(BaseModel):
    __test__ = False
    analysis_name: Optional[str] = None
    use_case: Optional[str] = None
    actor: Optional[str] = None
    title: Optional[str] = None
    test_type: Optional[TestType] = None
    injection_id: Optional[str] = None
    preconditions: Optional[str] = None
    steps: Optional[List[str]] = None
    expected_result: Optional[str] = None
    expected_behavior: Optional[ExpectedBehavior] = None
    priority: Optional[Priority] = None
    status: Optional[TestStatus] = None

class TestCaseStatusUpdate(BaseModel):
    __test__ = False
    status: TestStatus = Field(..., description="Nouveau statut du cas de test")

class TestCaseResponse(TestCaseBase):
    __test__ = False
    id: int
    created_at: str
    updated_at: str
    last_run: Optional[Dict[str, Any]] = None
    model_config = ConfigDict(from_attributes=True)

class TestRunBase(BaseModel):
    __test__ = False
    test_case_id: int
    duration_ms: int
    status: RunStatus
    actual_behavior: str
    details: Dict[str, Any] = Field(default_factory=dict)
    injection_id: Optional[str] = None

class TestRunResponse(TestRunBase):
    __test__ = False
    id: int
    started_at: str
    model_config = ConfigDict(from_attributes=True)

class FaultInjectionCatalogItem(BaseModel):
    __test__ = False
    id: str
    category: Literal["A", "B", "C", "D"]
    category_name: str
    name: str
    description: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    expected_behavior: ExpectedBehavior

class GenerateTestsRequest(BaseModel):
    __test__ = False
    documentation_text: str = Field(..., min_length=5, description="Documentation UML ou texte extrait à analyser")
    analysis_name: Optional[str] = Field("Système UML", description="Nom du système ou de l'analyse")
    save: Optional[bool] = Field(True, description="Enregistrer immédiatement les tests en base")

class GenerateTestsResponse(BaseModel):
    __test__ = False
    test_cases: List[TestCaseResponse]
    fallback_used: bool = Field(False, description="Indique si le fallback local par gabarits a été utilisé")
    total_generated: int
    message: str

class RunSelectionRequest(BaseModel):
    __test__ = False
    test_ids: Optional[List[int]] = Field(None, description="Liste des IDs de tests à exécuter, ou None pour tous")

class RunResultResponse(BaseModel):
    __test__ = False
    test_case_id: int
    test_run: TestRunResponse
    new_status: TestStatus
    passed: bool

class RunAllSummaryResponse(BaseModel):
    __test__ = False
    total_executed: int
    passed: int
    failed: int
    errors: int
    results: List[RunResultResponse]
    duration_total_ms: int

class CategoryRobustnessScore(BaseModel):
    __test__ = False
    category: str
    category_name: str
    total_tests: int
    passed_tests: int
    score_percentage: float

class TestStatsResponse(BaseModel):
    __test__ = False
    total: int
    by_status: Dict[str, int]
    by_type: Dict[str, int]
    by_priority: Dict[str, int]
    success_rate: float
    category_scores: Dict[str, CategoryRobustnessScore]
    global_robustness_score: float
