from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.api import api_router
from core.config import settings
from core.database import init_db
from core.traceability_db import init_traceability_db

# Create the prompts table + default prompt on first launch
init_db()
# Create the tr_* tables of the "Exigences & Traçabilité" module (existing data untouched)
init_traceability_db()

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_STR)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
