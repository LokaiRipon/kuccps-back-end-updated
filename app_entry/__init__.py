# ============================================================================
# FILE: app_entry/__init__.py (FIXED - no circular imports)
# ============================================================================
"""KUCCPS Course Checker API - Application Factory"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from motor.motor_asyncio import AsyncIOMotorClient
import logging

from app_entry.core.config import settings
from app_entry.core.cache import CourseCache
from app_entry.core import globals as app_globals
from app_entry.api.routes import router as api_router

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown"""
    # Startup
    try:
        logger.info("Starting application...")
        app_globals.client = AsyncIOMotorClient(settings.MONGO_URI)

        # Initialize cache
        app_globals.cache = CourseCache(app_globals.client, ttl_hours=settings.CACHE_TTL_HOURS)
        await app_globals.cache.initialize()

        logger.info("✓ Database client and cache initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database client: {e}")
        raise

    yield

    # Shutdown
    try:
        if app_globals.client:
            app_globals.client.close()
            logger.info("✓ Database client closed")
    except Exception as e:
        logger.error(f"Error closing database client: {e}")

def create_app() -> FastAPI:
    """Create and configure FastAPI application"""
    app = FastAPI(
        title=settings.API_TITLE,
        description="Check which courses you qualify for based on KCSE results",
        version=settings.API_VERSION,
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
        lifespan=lifespan
    )

    # CORS Configuration
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(api_router, prefix="/api")

    # Health check endpoint
    @app.get("/health")
    async def health_check():
        from datetime import datetime
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "version": settings.API_VERSION
        }

    logger.info("FastAPI application created")
    return app

# Create app instance
app = create_app()