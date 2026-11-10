from fastapi import APIRouter
from app.api.v1.routes import assistant, farmers, health, resources, voice

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(farmers.router, prefix="/farmers", tags=["farmers"])
api_router.include_router(resources.router, tags=["crops", "conversations", "messages", "advisories", "documents"])
api_router.include_router(voice.router, prefix="/voice", tags=["voice"])
api_router.include_router(assistant.router, prefix="/assistant", tags=["assistant"])
