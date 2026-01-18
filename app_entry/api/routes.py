"""Main API router - simplified for frontend sync"""

from fastapi import APIRouter

from app_entry.api.endpoints import clusterWeight, courses, payments

router = APIRouter()


# Include only the endpoints we actually need
router.include_router(courses.router, prefix="/courses", tags=["Courses"])
router.include_router(payments.router, prefix="/payments", tags=["Payments"])
router.include_router(clusterWeight.router, prefix="/payments", tags=["Cluster Weights"])