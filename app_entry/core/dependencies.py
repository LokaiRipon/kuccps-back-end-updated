# ============================================================================
# FILE: app_entry/core/dependencies.py (FIXED - no circular imports)
# ============================================================================
"""Dependency injection for FastAPI routes"""

from fastapi import HTTPException, status
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
import logging

from app_entry.core import globals as app_globals
from app_entry.core.config import settings

logger = logging.getLogger(__name__)

def get_db_by_name(db_name: str):
    """Factory to get a specific database by name
    
    Usage in routes:
        db: AsyncIOMotorDatabase = Depends(get_db_by_name(settings.PAYMENTS_DB))
    """
    async def _get_db() -> AsyncIOMotorDatabase:
        if app_globals.client is None:
            logger.error("Database client is not available")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database client unavailable"
            )
        return app_globals.client[db_name]
    return _get_db

async def get_cache():
    """Get cache instance
    
    This provides the course cache to any endpoint that needs it
    """
    if app_globals.cache is None:
        logger.error("Cache is not available")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Cache unavailable"
        )
    return app_globals.cache