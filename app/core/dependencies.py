# ============================================================================
# FILE: app/core/dependencies.py (CLEANED - KEEP THIS)
# ============================================================================
"""Dependency injection for FastAPI routes"""

from fastapi import Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
import logging

logger = logging.getLogger(__name__)

async def get_db() -> AsyncIOMotorDatabase:
    """Get database instance
    
    This is a dependency that provides the database connection
    to any endpoint that needs it
    """
    from app import db
    if db is None:
        logger.error("Database connection is not available")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection unavailable"
        )
    return db

async def get_cache():
    """Get cache instance
    
    This is a dependency that provides the course cache
    to any endpoint that needs it
    """
    from app import cache
    if cache is None:
        logger.error("Cache is not available")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Cache unavailable"
        )
    return cache