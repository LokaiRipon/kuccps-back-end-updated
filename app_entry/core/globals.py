# ============================================================================
# FILE: app_entry/core/globals.py (NEW - global instances)
# ============================================================================
"""Global application instances - client and cache"""

from typing import Optional
from motor.motor_asyncio import AsyncIOMotorClient
from app_entry.core.cache import CourseCache

# Global instances
client: Optional[AsyncIOMotorClient] = None
cache: Optional[CourseCache] = None