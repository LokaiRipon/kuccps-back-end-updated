# ============================================================================
# FILE: app/api/endpoints/courses.py (SAFER VERSION)
# ============================================================================
"""Course checking endpoints - defensive version"""

from fastapi import APIRouter, HTTPException, status, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime
import logging
from typing import List

from app.schemas.education import (
    CourseCheckRequest, CourseCheckResponse, EducationType,
    ClusterResult, Programme
)
from app.core.cache import CourseCache
from app.core.dependencies import get_db, get_cache
from app.utils.grade_checker import GradeChecker
from app.utils.validators import validate_subjects

logger = logging.getLogger(__name__)
router = APIRouter()

def _safe_programme(p: dict) -> dict:
    """Safely extract programme data, handling MongoDB ObjectIds and other issues"""
    try:
        return {
            "programme_name": str(p.get("programme_name", "")),
            "programme_code": str(p.get("programme_code", "")) if p.get("programme_code") else None,
            "minimum_grade": str(p.get("minimum_grade", "")) if p.get("minimum_grade") else None,
            "minimum_subject_requirements": p.get("minimum_subject_requirements", {}) if isinstance(p.get("minimum_subject_requirements"), dict) else {}
        }
    except Exception as e:
        logger.error(f"Error converting programme: {e}")
        return {
            "programme_name": "",
            "programme_code": None,
            "minimum_grade": None,
            "minimum_subject_requirements": {}
        }

# ============================================================================
# Helper functions for checking each programme type
# ============================================================================

async def _check_degree(checker: GradeChecker, min_grade: str, cache: CourseCache) -> List[ClusterResult]:
    """Check degree programmes"""
    results = []
    for cluster_no in range(1, 21):
        try:
            programmes = cache.get_degree_cluster(cluster_no)
            qualified = []
            for p in programmes:
                try:
                    if checker.check_programme_requirements(p, min_grade):
                        safe_p = _safe_programme(p)
                        qualified.append(Programme(**safe_p))
                except Exception as e:
                    logger.warning(f"Error checking programme {p.get('programme_name')}: {e}")
                    continue
            
            if qualified:
                results.append(ClusterResult(
                    cluster_name=f"cluster_{cluster_no}",
                    programmes=qualified
                ))
        except Exception as e:
            logger.error(f"Error checking cluster {cluster_no}: {e}")
            continue
    return results

async def _check_diploma(checker: GradeChecker, min_grade: str, cache: CourseCache) -> List[ClusterResult]:
    """Check diploma programmes"""
    results = []
    for category in cache.DIPLOMA_CATEGORIES:
        try:
            programmes = cache.get_diploma_category(category)
            qualified = []
            for p in programmes:
                try:
                    if checker.check_programme_requirements(p, min_grade):
                        safe_p = _safe_programme(p)
                        qualified.append(Programme(**safe_p))
                except Exception as e:
                    logger.warning(f"Error checking programme {p.get('programme_name')}: {e}")
                    continue
            
            if qualified:
                results.append(ClusterResult(
                    cluster_name=category,
                    programmes=qualified
                ))
        except Exception as e:
            logger.error(f"Error checking category {category}: {e}")
            continue
    return results

async def _check_certificate(checker: GradeChecker, min_grade: str, cache: CourseCache) -> List[ClusterResult]:
    """Check certificate programmes"""
    results = []
    for category in cache.CERT_CATEGORIES:
        try:
            programmes = cache.get_cert_category(category)
            qualified = []
            for p in programmes:
                try:
                    if checker.check_programme_requirements(p, min_grade):
                        safe_p = _safe_programme(p)
                        qualified.append(Programme(**safe_p))
                except Exception as e:
                    logger.warning(f"Error checking programme {p.get('programme_name')}: {e}")
                    continue
            
            if qualified:
                results.append(ClusterResult(
                    cluster_name=category,
                    programmes=qualified
                ))
        except Exception as e:
            logger.error(f"Error checking category {category}: {e}")
            continue
    return results

async def _check_kmtc(checker: GradeChecker, min_grade: str, cache: CourseCache) -> List[ClusterResult]:
    """Check KMTC programmes"""
    results = []
    for category in cache.KMTC_CATEGORIES:
        try:
            programmes = cache.get_kmtc()
            qualified = []
            for p in programmes:
                try:
                    if checker.check_programme_requirements(p, min_grade):
                        safe_p = _safe_programme(p)
                        qualified.append(Programme(**safe_p))
                except Exception as e:
                    logger.warning(f"Error checking programme {p.get('programme_name')}: {e}")
                    continue
            
            if qualified:
                results.append(ClusterResult(
                    cluster_name=category,
                    programmes=qualified
                ))
        except Exception as e:
            logger.error(f"Error checking category {category}: {e}")
            continue
    return results

# ============================================================================
# MAIN ENDPOINT
# ============================================================================

@router.post("/check", response_model=CourseCheckResponse)
async def check_courses(
    request: CourseCheckRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
    cache: CourseCache = Depends(get_cache)
) -> CourseCheckResponse:
    """Check which courses user qualifies for"""
    
    # Validate subjects
    is_valid, error_msg = validate_subjects(request.subjects)
    if not is_valid:
        logger.warning(f"Invalid subjects for {request.email}: {error_msg}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg
        )
    
    try:
        logger.info(f"Checking courses for {request.email} - Type: {request.education_type}")
        
        # Extract grades from the subjects list
        grade_dict = {}
        min_grade = None
        
        for subject in request.subjects:
            subject_name = subject.subject.lower()
            grade_dict[subject_name] = subject.grade
            
            # Overall grade is required
            if subject_name == "overall":
                min_grade = subject.grade
        
        if not min_grade:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Overall grade is required"
            )
        
        logger.info(f"User grades: {grade_dict}")
        logger.info(f"Minimum grade: {min_grade}")
        
        # Create grade checker with user's grades
        checker = GradeChecker(grade_dict)
        results = []
        
        # Check courses based on education type
        if request.education_type == EducationType.DEGREE:
            results = await _check_degree(checker, min_grade, cache)
        elif request.education_type == EducationType.DIPLOMA:
            results = await _check_diploma(checker, min_grade, cache)
        elif request.education_type == EducationType.CERTIFICATE:
            results = await _check_certificate(checker, min_grade, cache)
        elif request.education_type == EducationType.KMTC:
            results = await _check_kmtc(checker, min_grade, cache)
        
        logger.info(f"Found {len(results)} clusters with qualified programmes")
        
        # Save user info for later (for checkout)
        await db["payments"].update_one(
            {"$or": [{"email": request.email}, {"ksce_index": request.index_number}]},
            {
                "$set": {
                    "email": request.email,
                    "ksce_index": request.index_number,
                    "last_checked": datetime.utcnow()
                }
            },
            upsert=True
        )
        
        # Also save the course check results
        result_doc = {
            "email": request.email,
            "index_number": request.index_number,
            "education_type": request.education_type,
            "results": [r.dict() for r in results],
            "created_at": datetime.utcnow()
        }
        await db["course_results"].insert_one(result_doc)
        
        logger.info(f"✓ Course check complete for {request.email}")
        
        return CourseCheckResponse(
            email=request.email,
            index_number=request.index_number,
            education_type=request.education_type,
            results=results,
            timestamp=datetime.utcnow().isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error checking courses: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to check courses"
        )