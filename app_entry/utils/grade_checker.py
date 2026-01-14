# ============================================================================
# FILE: app_entry/utils/grade_checker.py (CLEANED - Production Ready)
# ============================================================================
"""Grade checking and programme matching logic with education type support"""

from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

# Import EducationType from schemas to avoid duplication
from app_entry.schemas.education import EducationType

class GradeChecker:
    """Handles grade validation and programme matching with multi-step qualification"""
    
    GRADE_POINTS = {
        "A": 12, "A-": 11, "B+": 10, "B": 9, "B-": 8,
        "C+": 7, "C": 6, "C-": 5, "D+": 4, "D": 3,
        "D-": 2, "E": 1,
    }
    
    def __init__(
        self,
        user_grades: Dict[str, str],
        education_type: EducationType = EducationType.DEGREE,
        cluster_weights: Optional[Dict[str, float]] = None
    ):
        """Initialize with user's grades and education type"""
        self.user_grades = user_grades
        self.education_type = education_type
        self.cluster_weights = cluster_weights or {}
        logger.debug(f"GradeChecker initialized: type={education_type}, grades={len(user_grades)}, clusters={len(self.cluster_weights)}")
    
    def check_programme_requirements(
        self,
        programme: Dict[str, Any],
        user_min_grade: str,
        cluster_number: Optional[str] = None
    ) -> bool:
        """Check if user qualifies for a programme (multi-step validation)"""
        prog_name = programme.get('programme_name', 'Unknown')
        
        try:
            # STEP 1: Cut-off points check (DEGREES ONLY)
            if self.education_type == EducationType.DEGREE:
                if not self._check_cutoff_points(programme, cluster_number):
                    return False
            
            # STEP 2: Minimum grade check
            if not self._check_minimum_grade(programme, user_min_grade):
                return False
            
            # STEP 3: Subject requirements check
            if not self._check_subjects(programme.get("minimum_subject_requirements", {})):
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking {prog_name}: {e}", exc_info=True)
            return False
    
    def _check_cutoff_points(self, programme: Dict[str, Any], cluster_number: Optional[str]) -> bool:
        """Check cut-off points qualification (degrees only)"""
        if self.education_type != EducationType.DEGREE or not cluster_number:
            return True
        
        try:
            prog_cutoff = programme.get("cut_off_points")
            
            # If no cutoff requirement, user qualifies
            if prog_cutoff is None or prog_cutoff == "":
                return True
            
            # Get the cluster key (e.g., "cl1" from "1")
            cluster_key = f"cl{cluster_number}"
            user_weight = self.cluster_weights.get(cluster_key, 0.0)
            
            # Convert to float for comparison
            try:
                prog_cutoff = float(prog_cutoff)
            except (TypeError, ValueError):
                logger.warning(f"Invalid cut_off_points: {prog_cutoff}")
                return True
            
            return user_weight >= prog_cutoff
            
        except Exception as e:
            logger.error(f"Error checking cut-off points: {e}")
            return False
    
    def _check_minimum_grade(self, programme: Dict[str, Any], user_grade: str) -> bool:
        """Check minimum grade requirement"""
        try:
            prog_min_grade = programme.get("minimum_grade")
            
            if prog_min_grade is None or prog_min_grade == "":
                return True
            
            # Extract the actual grade value
            if isinstance(prog_min_grade, dict):
                grade_value = prog_min_grade.get("mean_grade")
                if not grade_value:
                    return True
            else:
                grade_value = prog_min_grade
            
            # Compare grades
            user_grade_val = self._grade_value(user_grade)
            prog_grade_val = self._grade_value(str(grade_value))
            
            return user_grade_val >= prog_grade_val
            
        except Exception as e:
            logger.error(f"Error checking minimum grade: {e}")
            return False
    
    def _check_subjects(self, requirements: Dict[str, str]) -> bool:
        """Verify user has all required subjects with required grades"""
        try:
            if not requirements or not isinstance(requirements, dict):
                return True
            
            for req_subject, req_grade in requirements.items():
                if not req_subject or not isinstance(req_subject, str):
                    continue
                if not req_grade or not isinstance(req_grade, str):
                    continue
                
                # Handle subject alternatives (e.g., "ENG/KIS" or "Math/Statistics")
                if "/" in req_subject:
                    subjects = [s.strip() for s in req_subject.split("/")]
                    found = any(
                        self._user_has_subject(s, req_grade)
                        for s in subjects
                    )
                    if not found:
                        return False
                else:
                    if not self._user_has_subject(req_subject, req_grade):
                        return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking subjects: {e}")
            return False
    
    def _user_has_subject(self, subject: str, required_grade: str) -> bool:
        """Check if user has subject with required grade"""
        try:
            if not isinstance(subject, str) or not isinstance(required_grade, str):
                return False
            
            subject_lower = subject.lower().strip()
            required_grade_val = self._grade_value(required_grade)
            
            for user_subject, user_grade in self.user_grades.items():
                if not isinstance(user_subject, str) or not isinstance(user_grade, str):
                    continue
                
                user_subject_lower = user_subject.lower().strip()
                
                if subject_lower in user_subject_lower or user_subject_lower in subject_lower:
                    user_grade_val = self._grade_value(user_grade)
                    qualified = user_grade_val >= required_grade_val
                    if qualified:
                        return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking user subject: {e}")
            return False
    
    def _grade_value(self, grade: str) -> int:
        """Get numeric value of grade for comparison"""
        if not isinstance(grade, str):
            return 0
        
        grade_clean = grade.strip().upper()
        return self.GRADE_POINTS.get(grade_clean, 0)