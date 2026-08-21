"""
FastAPI Application Entry Point.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from app.config import settings
from app.api.routes import health, profiles, dashboard
from app.utils.logger import setup_logger

# Setup logging
logger = setup_logger(__name__)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    
    application = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="Chrome Profile Management API for YouTube Automation",
        docs_url="/docs",
        redoc_url="/redoc",
    )
    
    # CORS Middleware
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Static files (if any)
    static_dir = Path(__file__).parent / "static"
    if static_dir.exists():
        application.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
    
    # Include routers
    application.include_router(health.router, tags=["Health"])
    application.include_router(profiles.router, prefix="/api/profiles", tags=["Profiles"])
    application.include_router(dashboard.router, tags=["Dashboard"])
    
    @application.on_event("startup")
    async def startup_event():
        logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
        logger.info(f"Profiles directory: {settings.PROFILES_DIR}")
        
        # Start background poller service
        import asyncio
        from app.services.poller_service import poller_service
        asyncio.create_task(poller_service.start())
    
    @application.on_event("shutdown")
    async def shutdown_event():
        logger.info("Shutting down application")
        try:
            from app.services.browser_service import BrowserService
            BrowserService.close_all_browsers()
        except Exception as e:
            logger.error(f"Error closing browsers on shutdown: {e}")

        try:
            from app.services.poller_service import poller_service
            await poller_service.stop()
        except Exception as e:
            logger.error(f"Error stopping poller service: {e}")
    
    return application


# Create app instance
app = create_app()
