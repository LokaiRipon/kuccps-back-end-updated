# ============================================================================
# FILE: app/core/cache.py (UPDATED - accepts client, opens DBs explicitly)
# ============================================================================
"""Course data caching system"""

from datetime import datetime, timedelta
from typing import Dict, List, Any
import logging
from motor.motor_asyncio import AsyncIOMotorClient
from app_entry.core.config import settings

logger = logging.getLogger(__name__)

class CourseCache:
    """In-memory cache for course data with TTL support"""

    DIPLOMA_CATEGORIES = [
        "Agricultural_Sciences_Related", "Animal_Health_Related", "Applied_Sciences",
        "Building_Construction_Related", "Business_Related", "Clothing_Fashion_Textile",
        "Computing_IT_Related", "Education_Related", "Engineering_Technology_Related",
        "Environmental_Sciences", "Food_Science_Related", "Graphics_MediaStudies_Related",
        "Health_Sciences_Related", "Hospitality_Hotel_Tourism_Related", "Library_Information_Science",
        "Music_Related", "Natural_Sciences_Related", "Nutrition_Dietetics", "Social_Sciences",
        "Tax_Custom_Administration", "Technical_Courses"
    ]

    CERT_CATEGORIES = [
        "Agricultural_Sciences_Related", "Animal_Health_Related", "Applied_Sciences",
        "Building_Construction_Related", "Business_Related", "Clothing_Fashion_Textile",
        "Computing_IT_Related", "Engineering_Cert_Related", "Engineering_Technology_Related",
        "Environmental_Sciences", "Food_Science_Related", "Graphics_MediaStudies_MediaProduction",
        "HairDressing_Beauty_Therapy", "Health_Sciences_Related", "Hospitality_Hotel_Tourism_Related",
        "Library_Information_Science", "Natural_Sciences_Related", "Nutrition_Dietetics",
        "Social_Sciences", "Tax_Custom_Administration", "clothing"
    ]

    KMTC_CATEGORIES = ["kmtc"]

    def __init__(self, client: AsyncIOMotorClient, ttl_hours: int = 6):
        """Initialize cache with Mongo client"""
        self.client = client
        self.ttl = timedelta(hours=ttl_hours)
        self.cache_timestamp: datetime = None  # type: ignore

        # Cache stores
        self.degree_cache: Dict[str, List[Any]] = {}
        self.diploma_cache: Dict[str, List[Any]] = {}
        self.cert_cache: Dict[str, List[Any]] = {}
        self.kmtc_cache: Dict[str, List[Any]] = {}

        logger.debug("CourseCache initialized")

    async def initialize(self) -> None:
        """Load all course data into memory on startup"""
        try:
            await self.refresh_all()
            logger.info("✓ Course cache initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize cache: {e}")
            raise

    async def refresh_all(self) -> None:
        """Refresh all cached course data from database"""
        try:
            logger.info("Starting cache refresh...")

            await self._load_degree_clusters()
            logger.info(f"  ✓ Loaded {len(self.degree_cache)} degree clusters")

            await self._load_diploma_categories()
            logger.info(f"  ✓ Loaded {len(self.diploma_cache)} diploma categories")

            await self._load_cert_categories()
            logger.info(f"  ✓ Loaded {len(self.cert_cache)} certificate categories")

            await self._load_kmtc()
            logger.info(f"  ✓ Loaded {len(self.kmtc_cache)} KMTC programmes")

            self.cache_timestamp = datetime.utcnow()
            logger.info("✓ All caches refreshed successfully")

        except Exception as e:
            logger.error(f"Error refreshing cache: {e}")
            raise

    async def _load_degree_clusters(self) -> None:
        """Load degree cluster data from DEGREE_DB"""
        db_degree = self.client[settings.DEGREE_DB]
        for i in range(1, 21):
            cluster_name = f"cluster_{i}"
            try:
                data = await db_degree[cluster_name].find({}).to_list(None)
                self.degree_cache[cluster_name] = data or []
            except Exception as e:
                logger.warning(f"Failed to load {cluster_name}: {e}")
                self.degree_cache[cluster_name] = []

    async def _load_diploma_categories(self) -> None:
        """Load diploma category data from DP_COURSES_DB"""
        db_diploma = self.client[settings.DP_COURSES_DB]
        for category in self.DIPLOMA_CATEGORIES:
            try:
                data = await db_diploma[category].find({}).to_list(None)
                self.diploma_cache[category] = data or []
            except Exception as e:
                logger.warning(f"Failed to load diploma {category}: {e}")
                self.diploma_cache[category] = []

    async def _load_cert_categories(self) -> None:
        """Load certificate category data from CERT_COURSES_DB"""
        db_cert = self.client[settings.CERT_COURSES_DB]
        for category in self.CERT_CATEGORIES:
            try:
                data = await db_cert[category].find({}).to_list(None)
                self.cert_cache[category] = data or []
            except Exception as e:
                logger.warning(f"Failed to load cert {category}: {e}")
                self.cert_cache[category] = []

    async def _load_kmtc(self) -> None:
        """Load KMTC data from KMTC_COURSES_DB"""
        db_kmtc = self.client[settings.KMTC_COURSES_DB]
        for category in self.KMTC_CATEGORIES:
            try:
                data = await db_kmtc[category].find({}).to_list(None)
                self.kmtc_cache[category] = data or []
            except Exception as e:
                logger.warning(f"Failed to load kmtc: {e}")
                self.kmtc_cache[category] = []

    def should_refresh(self) -> bool:
        """Check if cache needs refresh based on TTL"""
        if not self.cache_timestamp:
            return True
        return datetime.utcnow() - self.cache_timestamp > self.ttl

    def get_degree_cluster(self, cluster_no: int) -> List[Any]:
        """Get cached degree cluster data"""
        return self.degree_cache.get(f"cluster_{cluster_no}", [])

    def get_diploma_category(self, category: str) -> List[Any]:
        """Get cached diploma category data"""
        return self.diploma_cache.get(category, [])

    def get_cert_category(self, category: str) -> List[Any]:
        """Get cached certificate category data"""
        return self.cert_cache.get(category, [])

    def get_kmtc(self) -> List[Any]:
        """Get cached KMTC programmes"""
        return self.kmtc_cache.get("kmtc", [])
