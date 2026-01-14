# ============================================================================
# FILE: app_entry/api/endpoints/courses.py (FIXED - with cluster_weights)
# ============================================================================
"""Course checking endpoints - with multi-step qualification"""

from fastapi import APIRouter, HTTPException, status, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime
import logging
from typing import List

from app_entry.schemas.education import (
    CourseCheckRequest, CourseCheckResponse, EducationType,
    ClusterResult, Programme
)
from app_entry.core.cache import CourseCache
from app_entry.core.dependencies import get_db_by_name, get_cache
from app_entry.core.config import settings
from app_entry.utils.grade_checker import GradeChecker
from app_entry.utils.validators import validate_subjects

logger = logging.getLogger(__name__)
router = APIRouter()

def _safe_programme(p: dict) -> dict:
    """Safely extract programme data, handling MongoDB ObjectIds and other issues"""
    try:
        # Handle minimum_grade - it's a dict like {'mean_grade': 'D'}
        min_grade = p.get("minimum_grade", {})
        if isinstance(min_grade, dict):
            grade_value = min_grade.get("mean_grade", "")
        else:
            grade_value = str(min_grade) if min_grade else None
        
        return {
            "institution_name": str(p.get("institution_name", "")),
            "programme_name": str(p.get("programme_name", "")),
            "programme_code": str(p.get("programme_code", "")) if p.get("programme_code") else None,
            "cut_off_points": float(p.get("cut_off_points", 0.0)) if p.get("cut_off_points") else None,
            "minimum_grade": grade_value,
            "minimum_subject_requirements": p.get("minimum_subject_requirements", {}) if isinstance(p.get("minimum_subject_requirements"), dict) else {}
        }
    except Exception as e:
        logger.error(f"Error converting programme: {e}")
        return {
            "institution_name": "",
            "programme_name": "",
            "programme_code": None,
            "cut_off_points": None,
            "minimum_grade": None,
            "minimum_subject_requirements": {}
        }

# ============================================================================
# Helper functions for checking each programme type
# ============================================================================

async def _check_degree(checker: GradeChecker, min_grade: str, cache: CourseCache) -> List[ClusterResult]:
    """Check degree programmes with cut-off points validation"""
    results = []
    for cluster_no in range(1, 21):
        try:
            programmes = cache.get_degree_cluster(cluster_no)
            qualified = []
            for p in programmes:
                try:
                    # Pass cluster number for cut-off points check
                    if checker.check_programme_requirements(p, min_grade, cluster_number=str(cluster_no)):
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
                logger.info(f"✓ Cluster {cluster_no}: {len(qualified)} qualified programmes")
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
                logger.info(f"✓ Diploma {category}: {len(qualified)} qualified programmes")
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
                logger.info(f"✓ Cert {category}: {len(qualified)} qualified programmes")
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
                logger.info(f"✓ KMTC {category}: {len(qualified)} qualified programmes")
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
    db: AsyncIOMotorDatabase = Depends(get_db_by_name(settings.PAYMENTS_DB)),
    cache: CourseCache = Depends(get_cache)
) -> CourseCheckResponse:
    """Check which courses user qualifies for
    
    Multi-step qualification logic:
    - DEGREE: cut_off_points → minimum_grade → subject_requirements
    - DIPLOMA/CERT/KMTC: minimum_grade → subject_requirements
    """
    
    # Validate subjects
    is_valid, error_msg = validate_subjects(request.subjects)
    if not is_valid:
        logger.warning(f"Invalid subjects for {request.email}: {error_msg}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg
        )
    
    try:
        logger.info(f"🔍 Checking courses for {request.email} - Type: {request.education_type}")
        
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
        
        logger.info(f"📊 User grades extracted: {len(grade_dict)} subjects, overall={min_grade}")
        
        # Create grade checker with ALL necessary info
        checker = GradeChecker(
            user_grades=grade_dict,
            education_type=EducationType(request.education_type),
            cluster_weights=request.cluster_weights or {}
        )
        
        results = []
        
        # Check courses based on education type
        if request.education_type == EducationType.DEGREE:
            logger.info("🎓 Running DEGREE qualification logic with cut-off points")
            results = await _check_degree(checker, min_grade, cache)
        elif request.education_type == EducationType.DIPLOMA:
            logger.info("📚 Running DIPLOMA qualification logic")
            results = await _check_diploma(checker, min_grade, cache)
        elif request.education_type == EducationType.CERTIFICATE:
            logger.info("🏆 Running CERTIFICATE qualification logic")
            results = await _check_certificate(checker, min_grade, cache)
        elif request.education_type == EducationType.KMTC:
            logger.info("🏥 Running KMTC qualification logic")
            results = await _check_kmtc(checker, min_grade, cache)
        
        # Count total qualified programmes
        total_qualified = sum(len(cluster.programmes) for cluster in results)
        logger.info(f"✅ Found {len(results)} clusters with {total_qualified} qualified programmes")
        
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
        
        # Save the course check results
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