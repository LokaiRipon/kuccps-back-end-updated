
# app/core/config.py

"""Application configuration from environment variables"""

from pydantic_settings import BaseSettings # type: ignore
from typing import List
import os
from pathlib import Path

class Settings(BaseSettings):
    """Application settings from environment variables"""
    
    # Database
    MONGO_URI: str = os.getenv(
        'MONGO_URI',
        'mongodb://localhost:27017'
    )
    DEGREE_DB: str = 'courses_2'
    DP_COURSES_DB: str = 'dp_courses'
    CERT_COURSES_DB: str = 'cert_courses'
    KMTC_COURSES_DB: str = 'kmtc'
    PAYMENTS_DB: str = 'payments_db'
    
    # API
    API_TITLE: str = 'KUCCPS Course Checker'
    API_VERSION: str = '2.0.0'
    
    # Security - This is just for security purposes for the server
    SECRET_KEY: str = os.getenv('SECRET_KEY', 'change-me-in-production-now')
    ALGORITHM: str = 'HS256'
    ACCESS_TOKEN_EXPIRE_HOURS: int = 24
    
    # CORS
    CORS_ORIGINS: List[str] = [
        'http://localhost:3000',
        'http://localhost:5173',
        'http://127.0.0.1:3000',
        'http://127.0.0.1:5173',
        'https://kuccps-courses.netlify.app/'
    ]
    
    # Paystack
    PAYSTACK_SECRET_KEY: str = os.getenv('PAYSTACK_SECRET_KEY', '')
    PAYSTACK_API_URL: str = 'https://api.paystack.co'
    PAYSTACK_PUBLIC_KEY: str = os.getenv('PAYSTACK_PUBLIC_KEY', '')
    
    # Cache - in hours
    CACHE_TTL_HOURS: int = 6
    
    # Logging
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')
    
    class Config:
        env_file = '.env'
        case_sensitive = True

settings = Settings()
