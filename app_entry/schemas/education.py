# ============================================================================
# FILE: app_entry/schemas/education.py (UPDATED - includes cluster_weights)
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
    cluster_weights: Optional[Dict[str, float]] = None  # For degree students only
    
    @field_validator('cluster_weights', mode='before')
    @classmethod
    def validate_cluster_weights(cls, v, info):
        """Validate cluster weights if provided (must be for degree type)"""
        if info.data.get('education_type') == EducationType.DEGREE:
            if v is None:
                raise ValueError("cluster_weights required for degree students")
            if not isinstance(v, dict):
                raise ValueError("cluster_weights must be a dictionary")
            
            # Check we have all 20 clusters
            expected_clusters = {f"cl{i}" for i in range(1, 21)}
            provided_clusters = set(v.keys())
            
            if provided_clusters != expected_clusters:
                missing = expected_clusters - provided_clusters
                extra = provided_clusters - expected_clusters
                msg = f"Invalid clusters. "
                if missing:
                    msg += f"Missing: {missing}. "
                if extra:
                    msg += f"Extra: {extra}"
                raise ValueError(msg)
            
            # Validate each weight is a number
            for cluster, weight in v.items():
                try:
                    w = float(weight)
                    if w < 0:
                        raise ValueError(f"{cluster}: weight cannot be negative")
                    if w > 100:
                        raise ValueError(f"{cluster}: weight should not exceed 100")
                except (TypeError, ValueError) as e:
                    raise ValueError(f"{cluster}: must be a valid number - {str(e)}")
        
        return v
    
    class Config:
        example = {
            "email": "user@example.com",
            "index_number": "12345/001",
            "education_type": "degree",
            "subjects": [
                {"subject": "overall", "grade": "C+"},
                {"subject": "mathematics", "grade": "A"},
                {"subject": "english", "grade": "B+"}
            ],
            "cluster_weights": {
                "cl1": 34.486,
                "cl2": 33.001,
                "cl3": 34.486,
                # ... cl4 through cl20
            }
        }

class Programme(BaseModel):
    """Course/Programme information"""
    institution_name: str
    programme_name: str
    programme_code: Optional[Union[str, int]] = None
    cut_off_points: Optional[float] = None  # For degrees only
    minimum_grade: Optional[str] = None  # For diplomas/certs/kmtc
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