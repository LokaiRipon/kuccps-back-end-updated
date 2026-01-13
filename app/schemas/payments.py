
# app/schemas/payment.py

"""Payment-related schemas"""

from pydantic import BaseModel, Field
from typing import Optional

class PaymentInitializeRequest(BaseModel):
    """Initialize payment request"""
    email: str = Field(..., description="User email")
    index_number: str = Field(..., description="User's KCSE index number")
    education_type: str = Field(..., description="Type of programme")
    amount: int = Field(199000, description="Amount in cents")

class PaymentVerifyRequest(BaseModel):
    """Verify payment request"""
    reference: str = Field(..., description="Paystack payment reference")
    type: str = Field(..., description="Type of programme")

class PaymentResponse(BaseModel):
    """Payment response"""
    payment_id: str = Field(..., description="Unique payment ID")
    amount: int = Field(..., description="Amount in cents")
    email: str = Field(..., description="User email")

