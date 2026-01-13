# ============================================================================
# FILE: app/__init__.py (FIXED)
# ============================================================================
"""KUCCPS Course Checker API - Application Factory"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
import logging

from app.core.config import settings
from app.core.cache import CourseCache
from app.api.routes import router as api_router

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global instances
db: AsyncIOMotorDatabase = None # type: ignore
cache: CourseCache = None # type: ignore

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown"""
    global db, cache
    
    # Startup
    try:
        logger.info("Starting application...")
        client = AsyncIOMotorClient(settings.MONGO_URI)
        db = client[settings.DATABASE_NAME]
        
        # Initialize cache (CourseCache init is NOT async, but initialize() is)
        cache = CourseCache(db, ttl_hours=settings.CACHE_TTL_HOURS)
        await cache.initialize()  # This is the async method
        
        logger.info("✓ Database and cache initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise
    
    yield
    
    # Shutdown
    try:
        await client.close() # type: ignore
        logger.info("✓ Database connection closed")
    except Exception as e:
        logger.error(f"Error closing database: {e}")

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