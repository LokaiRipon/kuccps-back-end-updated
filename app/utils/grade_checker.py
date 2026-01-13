# ============================================================================
# FILE: app/utils/grade_checker.py (FIXED - HANDLE DICT ERROR)
# ============================================================================
"""Grade checking and programme matching logic"""

from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

class GradeChecker:
    """Handles grade validation and programme matching"""
    
    GRADE_POINTS = {
        "A": 12, "A-": 11, "B+": 10, "B": 9, "B-": 8,
        "C+": 7, "C": 6, "C-": 5, "D+": 4, "D": 3,
        "D-": 2, "E": 1,
    }
    
    def __init__(self, user_grades: Dict[str, str]):
        """Initialize with user's grades
        
        Args:
            user_grades: Dictionary mapping subject names to grades
                        e.g., {"mathematics": "A", "english": "B+"}
        """
        self.user_grades = user_grades
        logger.debug(f"Initialized GradeChecker with {len(user_grades)} grades")
    
    def check_programme_requirements(
        self,
        programme: Dict[str, Any],
        user_min_grade: str
    ) -> bool:
        """Check if user qualifies for a programme
        
        Args:
            programme: Programme dict from database
            user_min_grade: User's overall grade
            
        Returns:
            True if user qualifies, False otherwise
        """
        try:
            # Check minimum grade requirement
            prog_min_grade = programme.get("minimum_grade")
            if prog_min_grade:
                if self._grade_value(user_min_grade) < self._grade_value(prog_min_grade):
                    return False
            
            # Check subject requirements
            subject_reqs = programme.get("minimum_subject_requirements", {})
            
            # Handle case where subject_reqs might be None or empty
            if not subject_reqs or not isinstance(subject_reqs, dict):
                return True
            
            return self._check_subjects(subject_reqs)
        except Exception as e:
            logger.error(f"Error checking programme requirements: {e}")
            # If there's an error, assume user doesn't qualify to be safe
            return False
    
    def _check_subjects(self, requirements: Dict[str, str]) -> bool:
        """Verify user has all required subjects with required grades
        
        Args:
            requirements: Dict of subject -> grade requirements
            
        Returns:
            True if all requirements met, False otherwise
        """
        try:
            # Make sure requirements is actually a dict
            if not isinstance(requirements, dict):
                logger.warning(f"requirements is not a dict: {type(requirements)}")
                return True
            
            for req_subject, req_grade in requirements.items():
                # Skip if req_subject or req_grade is None or not a string
                if not req_subject or not isinstance(req_subject, str):
                    continue
                if not req_grade or not isinstance(req_grade, str):
                    continue
                
                # Handle subject alternatives (e.g., "Math/Statistics")
                if "/" in req_subject:
                    subjects = req_subject.split("/")
                    found = any(
                        self._user_has_subject(s.strip(), req_grade)
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
        """Check if user has subject with required grade
        
        Args:
            subject: Required subject name
            required_grade: Minimum grade required
            
        Returns:
            True if user qualifies, False otherwise
        """
        try:
            # Ensure inputs are strings
            if not isinstance(subject, str) or not isinstance(required_grade, str):
                return False
            
            subject_lower = subject.lower().strip()
            
            for user_subject, user_grade in self.user_grades.items():
                # Ensure both are strings
                if not isinstance(user_subject, str) or not isinstance(user_grade, str):
                    continue
                
                user_subject_lower = user_subject.lower().strip()
                
                if subject_lower in user_subject_lower:
                    user_grade_value = self._grade_value(user_grade)
                    required_grade_value = self._grade_value(required_grade)
                    return user_grade_value >= required_grade_value
            
            return False
        except Exception as e:
            logger.error(f"Error checking if user has subject: {e}")
            return False
    
    def _grade_value(self, grade: str) -> int:
        """Get numeric value of grade for comparison
        
        Args:
            grade: Letter grade (e.g., "A", "B+")
            
        Returns:
            Numeric value, or 0 if invalid
        """
        if not isinstance(grade, str):
            return 0
        
        grade_clean = grade.strip().upper()
        return self.GRADE_POINTS.get(grade_clean, 0)