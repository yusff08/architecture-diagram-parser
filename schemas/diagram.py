from pydantic import BaseModel, Field
from typing import List

class ExtractedTextSnippet(BaseModel):
    text: str = Field(..., description="The detected text snippet")
    confidence: float = Field(..., description="Confidence score of the detected text")

class DiagramDocumentationResponse(BaseModel):
    system_title: str = Field(..., description="Le nom déduit du système")
    detected_actors: List[str] = Field(..., description="Liste des acteurs détectés")
    documentation_markdown: str = Field(..., description="La documentation générée en Markdown")
    ocr_snippets: List[ExtractedTextSnippet] = Field(default_factory=list, description="Les textes extraits par l'OCR")
