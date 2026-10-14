from fastapi import APIRouter
from api.endpoints import diagram, prompts, uml_review

api_router = APIRouter()

api_router.include_router(diagram.router, tags=["Diagrams"])
api_router.include_router(prompts.router, tags=["Gestion des Prompts"])
api_router.include_router(uml_review.router, tags=["UML Review"])