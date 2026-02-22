from fastapi import APIRouter
from app.api.endpoints import documents, auth

api_router = APIRouter()
api_router.include_router(documents.router, prefix="/documents", tags=["documents"])
api_router.include_router(auth.router, tags=["login"])
