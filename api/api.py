from fastapi import APIRouter
from api.endpoints import diagram, prompts

api_router = APIRouter()
api_router.include_router(diagram.router, tags=["Diagrams"])
api_router.include_router(prompts.router, tags=["Gestion des Prompts"])
