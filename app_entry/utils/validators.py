
# ============================================================================
# FILE: app/utils/validators.py
# ============================================================================
"""Input validation utilities"""

from typing import List, Tuple
from app_entry.schemas.education import SubjectGrade
import logging

logger = logging.getLogger(__name__)

VALID_GRADES = {'A', 'A-', 'B+', 'B', 'B-', 'C+', 'C', 'C-', 'D+', 'D', 'D-', 'E'}

def validate_subjects(subjects: List[SubjectGrade]) -> Tuple[bool, str]:
    """Validate subject input
    
    Args:
        subjects: List of SubjectGrade objects
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not subjects:
        return False, "At least one subject is required"
    
    if len(subjects) > 15:
        return False, "Maximum 15 subjects allowed"
    
    for subject in subjects:
        if subject.grade not in VALID_GRADES:
            error_msg = f"Invalid grade: {subject.grade}. Valid grades are: {', '.join(sorted(VALID_GRADES))}"
            logger.warning(error_msg)
            return False, error_msg
    
    logger.debug(f"Validated {len(subjects)} subjects successfully")
    return True, ""

def validate_index_number(index_number: str) -> Tuple[bool, str]:
    """Validate KCSE index number format
    
    Args:
        index_number: KCSE index number
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not index_number or len(index_number) < 5:
        return False, "Invalid index number format"
    
    return True, ""

def validate_email(email: str) -> Tuple[bool, str]:
    """Validate email format
    
    Args:
        email: Email address
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not email or '@' not in email:
        return False, "Invalid email format"
    
    return True, ""