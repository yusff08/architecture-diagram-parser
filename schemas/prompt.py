from pydantic import BaseModel, Field
from typing import Optional, List, Literal

class PromptBase(BaseModel):
    name: str = Field(..., min_length=3, max_length=100, description="Nom du prompt")
    description: Optional[str] = Field(None, max_length=255, description="Courte description du prompt")
    content: str = Field(..., min_length=20, description="Instructions envoyées au LLM")

class PromptCreate(PromptBase):
    pass

class PromptUpdate(PromptBase):
    pass

class PromptResponse(PromptBase):
    id: int
    is_default: bool
    created_at: str
    updated_at: str


class PromptAnalysisRequest(BaseModel):
    content: str = Field(..., min_length=20, description="Contenu du prompt à analyser")

class PromptAnalysisResponse(BaseModel):
    score: int = Field(..., ge=0, le=100, description="Score de qualité sur 100")
    verdict: str = Field(..., description="Excellent / Correct / À améliorer")
    strengths: List[str] = Field(default_factory=list, description="Points forts du prompt")
    suggestions: List[str] = Field(default_factory=list, description="Suggestions d'amélioration")
    source: Literal["ia", "local"] = Field(..., description="ia = Gemini, local = analyse de secours")
    fallback_reason: Optional[str] = Field(None, description="Raison du fallback local")
