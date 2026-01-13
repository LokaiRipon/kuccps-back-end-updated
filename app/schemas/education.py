# ============================================================================
# app/schemas/education.py (FIXED - HANDLES INT PROGRAMME CODES)
# ============================================================================
"""Education-related schemas"""

from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import List, Dict, Optional, Union
from enum import Enum

class EducationType(str, Enum):
    """Education programme types"""
    DEGREE = "degree"
    DIPLOMA = "diploma"
    CERTIFICATE = "cert"
    KMTC = "kmtc"

class SubjectGrade(BaseModel):
    """Subject and grade pair"""
    subject: str = Field(..., min_length=1)
    grade: str = Field(..., min_length=1, max_length=2)
    
    class Config:
        example = {"subject": "mathematics", "grade": "A"}

class CourseCheckRequest(BaseModel):
    """Request to check eligible courses"""
    email: EmailStr
    index_number: str = Field(..., min_length=5, max_length=20)
    education_type: EducationType
    subjects: List[SubjectGrade] = Field(..., min_items=1) # type: ignore
    
    class Config:
        example = {
            "email": "user@example.com",
            "index_number": "12345/001",
            "education_type": "degree",
            "subjects": [
                {"subject": "mathematics", "grade": "A"},
                {"subject": "english", "grade": "B+"}
            ]
        }

class Programme(BaseModel):
    """Course/Programme information"""
    programme_name: str
    programme_code: Optional[Union[str, int]] = None  # CHANGED: Accept both string and int
    minimum_grade: Optional[str] = None
    minimum_subject_requirements: Optional[Dict[str, str]] = None
    
    @field_validator('programme_code', mode='before')
    @classmethod
    def convert_code_to_string(cls, v):
        """Convert programme_code to string if it's an int"""
        if v is None:
            return None
        if isinstance(v, int):
            return str(v)
        return v

class ClusterResult(BaseModel):
    """Results grouped by cluster/category"""
    cluster_name: str
    programmes: List[Programme]

class CourseCheckResponse(BaseModel):
    """Response with course check results"""
    email: str
    index_number: str
    education_type: EducationType
    results: List[ClusterResult]
    timestamp: str