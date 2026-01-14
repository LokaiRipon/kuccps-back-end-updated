# app/schemas/payments.py
"""Payment-related schemas"""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Dict, Any, List
from datetime import datetime


# ==================== REQUEST SCHEMAS ====================

class CheckUserRequest(BaseModel):
    """Check if user is returning customer"""
    email: EmailStr = Field(..., description="User email")
    index_number: str = Field(..., description="KCSE index number")
    education_type: str = Field(..., description="Education type (degree, diploma, cert, kmtc)")

class PaymentVerifyRequest(BaseModel):
    """Verify payment with Paystack and save user data"""
    reference: str = Field(..., description="Paystack transaction reference")
    email: EmailStr = Field(..., description="User email")
    index_number: str = Field(..., description="KCSE index number")
    education_type: str = Field(..., description="Education type")
    course_results: Dict[str, Any] = Field(..., description="User's qualified courses data")


class UserResultsRequest(BaseModel):
    """Request to retrieve stored user results"""
    email: EmailStr = Field(..., description="User email")
    index_number: str = Field(..., description="KCSE index number")
    education_type: str = Field(..., description="Education type to retrieve")


class PaymentInitializeRequest(BaseModel):
    """Initialize payment session"""
    email: EmailStr = Field(..., description="User email")
    index_number: str = Field(..., description="KCSE index number")
    education_type: str = Field(..., description="Education type")
    amount: int = Field(19900, description="Amount in kobo (KES 199 = 19900)")


# ==================== RESPONSE SCHEMAS ====================

class CheckUserResponse(BaseModel):
    """Response for user check - shows if returning customer and discount eligibility"""
    exists: bool = Field(..., description="Whether user exists in database")
    education_types: List[str] = Field(default=[], description="Education types already purchased")
    hasThisType: bool = Field(..., description="Whether they've already purchased this education_type")


class PaymentVerifyResponse(BaseModel):
    """Response after successful payment verification"""
    status: str = Field(..., description="Status (success/failed)")
    message: str = Field(..., description="Response message")
    reference: str = Field(..., description="Paystack transaction reference")
    email: str = Field(..., description="User email")
    education_type: str = Field(..., description="Education type purchased")


class UserResultsResponse(BaseModel):
    """Response with stored course results"""
    email: EmailStr = Field(..., description="User email")
    index_number: str = Field(..., description="KCSE index number")
    education_type: str = Field(..., description="Education type")
    course_results: Dict[str, Any] = Field(..., description="Qualified courses data")
    verified_at: Optional[datetime] = Field(None, description="Payment verification timestamp")


class UserPaymentTypesResponse(BaseModel):
    """Response with user's purchase history"""
    email: str = Field(..., description="User email")
    index_number: str = Field(..., description="KCSE index number")
    purchased_types: List[str] = Field(..., description="Education types purchased")
    count: int = Field(..., description="Total types purchased")


class PaymentResponse(BaseModel):
    """Basic payment response"""
    payment_id: Optional[str] = Field(None, description="Unique payment ID")
    amount: int = Field(..., description="Amount in kobo")
    email: str = Field(..., description="User email")
    status: str = Field("pending", description="Payment status")


class HealthCheckResponse(BaseModel):
    """Health check response"""
    status: str = Field(..., description="Service status")
    message: str = Field(..., description="Status message")


# ==================== DATABASE SCHEMAS ====================

class PaymentRecord(BaseModel):
    """Payment record stored in payments collection"""
    email: EmailStr = Field(..., description="User email")
    index_number: str = Field(..., description="KCSE index number")
    reference: str = Field(..., description="Paystack transaction reference")
    education_type: str = Field(..., description="Education type purchased")
    status: str = Field("success", description="Payment status")
    amount_kes: int = Field(199, description="Amount in KES")
    amount_kobo: int = Field(19900, description="Amount in kobo")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Payment timestamp")


class DataRecord(BaseModel):
    """Course data record stored in data collection"""
    reference: str = Field(..., description="Paystack transaction reference")
    index_number: str = Field(..., description="KCSE index number")
    education_type: str = Field(..., description="Education type")
    data: List[Dict[str, Any]] = Field(..., description="Array of course results")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Record creation timestamp")