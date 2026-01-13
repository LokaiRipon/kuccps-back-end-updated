
# app/schemas/auth.py

"""Authentication-related schemas"""

from pydantic import BaseModel, EmailStr, Field

class RegisterRequest(BaseModel):
    """User registration request"""
    email: EmailStr = Field(..., description="User email")
    index_number: str = Field(..., description="KCSE index number")
    
    class Config:
        example = {
            "email": "user@example.com",
            "index_number": "12345/001"
        }

class AuthResponse(BaseModel):
    """Authentication response"""
    token: str = Field(..., description="JWT access token")
    email: str = Field(..., description="User email")
    is_new_user: bool = Field(..., description="Whether this is a new user registration")

class TokenPayload(BaseModel):
    """JWT token payload"""
    sub: str = Field(..., description="Subject (email)")
    index_number: str = Field(..., description="Index number")
    exp: int = Field(..., description="Expiration time")
    iat: int = Field(..., description="Issued at time")
