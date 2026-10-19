from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class StrictSchema(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, str_strip_whitespace=True)


class Severity(str, Enum):
    CRITIQUE = "CRITIQUE"
    MOYEN = "MOYEN"
    FAIBLE = "FAIBLE"


class IssueClassification(str, Enum):
    ERREUR_CONFIRMEE = "ERREUR_CONFIRMEE"
    AMELIORATION_POTENTIELLE = "AMELIORATION_POTENTIELLE"


class MissingElementConfidence(str, Enum):
    FAIBLE = "faible"
    MOYENNE = "moyenne"
    ELEVEE = "élevée"


class UMLReviewRequest(StrictSchema):
    documentation_markdown: str = Field(min_length=1, max_length=50_000)

    @field_validator("documentation_markdown")
    @classmethod
    def validate_documentation_markdown(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("La documentation Markdown ne peut pas être vide.")
        return value.strip()


class UMLIssue(StrictSchema):
    title: str = Field(min_length=1)
    severity: Severity
    classification: IssueClassification
    description: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    suggestion: str = Field(min_length=1)


class PossibleMissingElement(StrictSchema):
    element: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    confidence: MissingElementConfidence


class UMLReviewResponse(StrictSchema):
    score: int = Field(ge=0, le=100)
    summary: str = Field(min_length=1)
    issues: list[UMLIssue]
    strengths: list[str]
    possible_missing_elements: list[PossibleMissingElement]
    improved_documentation_markdown: str = Field(min_length=1)
