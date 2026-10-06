from fastapi import APIRouter
from api.endpoints import diagram

api_router = APIRouter()
api_router.include_router(diagram.router, tags=["Diagrams"])
