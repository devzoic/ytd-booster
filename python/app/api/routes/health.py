"""
Health check endpoints.
"""

from fastapi import APIRouter
from app.config import settings
from app.models.response import APIResponse

router = APIRouter()


@router.get("/health", response_model=APIResponse)
async def health_check():
    """Health check endpoint."""
    return APIResponse(
        success=True,
        message="Service is healthy",
        data={
            "app_name": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "status": "running"
        }
    )


@router.get("/", response_model=APIResponse)
async def root():
    """Root endpoint."""
    return APIResponse(
        success=True,
        message=f"Welcome to {settings.APP_NAME}",
        data={
            "docs": "/docs",
            "health": "/health"
        }
    )
