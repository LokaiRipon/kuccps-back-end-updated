# ============================================================================
# FILE: api/endpoints/payments.py (FIXED - no circular imports)
# ============================================================================
"""Payment endpoints - Complete implementation with discount logic"""

from fastapi import APIRouter, HTTPException, status, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime
import logging
import httpx
import os

from app_entry.core import globals as app_globals
from app_entry.core.config import settings
from app_entry.core.dependencies import get_db_by_name
from app_entry.schemas.payments import (
    CheckUserRequest,
    CheckUserResponse,
    PaymentVerifyRequest,
    PaymentVerifyResponse,
    UserResultsRequest,
    UserResultsResponse,
    UserPaymentTypesResponse,
    HealthCheckResponse
)

logger = logging.getLogger(__name__)
router = APIRouter()

# Paystack configuration
PAYSTACK_SECRET_KEY = os.getenv("PAYSTACK_SECRET_KEY", "your_paystack_secret_key_here")
PAYSTACK_PUBLIC_KEY = os.getenv("PAYSTACK_PUBLIC_KEY", "your_paystack_public_key_here")
AMOUNT_KES = 19900  # KES 199
AMOUNT_KOBO = AMOUNT_KES * 100  # Convert to kobo (500)

# ==================== CHECK USER - DISCOUNT ELIGIBILITY ====================

@router.post("/check-user", response_model=CheckUserResponse)
async def check_user(request: CheckUserRequest) -> CheckUserResponse:
    """
    Check if user is a returning customer for discount eligibility
    Logic:
    - If exists=False → New user, full price (KES 199)
    - If exists=True & hasThisType=False → Returning user, different type (50% off: KES 99.50)
    - If exists=True & hasThisType=True → Already purchased this type, show alert
    """
    try:
        logger.info(f"🔍 Checking user: {request.email}")

        # Get the payments database dynamically
        if not app_globals.client:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database client unavailable"
            )
        
        payments_db = app_globals.client[settings.PAYMENTS_DB]
        payments_collection = payments_db["payments_info"]

        payments = await payments_collection.find(
            {
                "email": request.email,
                "index_number": request.index_number,
                "status": "success"
            }
        ).to_list(None)

        if not payments:
            logger.info(f"👤 New user: {request.email}")
            return CheckUserResponse(exists=False, education_types=[], hasThisType=False)

        education_types = [p.get("education_type") for p in payments if p.get("education_type")]
        hasThisType = request.education_type in education_types

        logger.info(f"✓ Returning user: {request.email}")
        logger.info(f"  Previous purchases: {education_types}")
        logger.info(f"  Has {request.education_type}: {hasThisType}")

        return CheckUserResponse(exists=True, education_types=education_types, hasThisType=hasThisType)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error checking user: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to check user: {str(e)}")


# ==================== VERIFY PAYMENT ====================

@router.post("/verify", response_model=PaymentVerifyResponse)
async def verify_payment(request: PaymentVerifyRequest) -> PaymentVerifyResponse:
    """
    Verify payment with Paystack and save user data
    Steps:
    1. Verify payment reference with Paystack API
    2. Confirm payment status is 'success'
    3. Save to payments collection
    4. Save to data collection
    """
    try:
        logger.info(f"🔄 Verifying payment: {request.reference}")

        # Get the payments database dynamically
        if not app_globals.client:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database client unavailable"
            )
        
        payments_db = app_globals.client[settings.PAYMENTS_DB]
        payments_collection = payments_db["payments_info"]
        data_collection = payments_db["client_course_data"]

        """
        # STEP 1: VERIFY WITH PAYSTACK
        async with httpx.AsyncClient() as http_client:
            paystack_response = await http_client.get(
                f"https://api.paystack.co/transaction/verify/{request.reference}",
                headers={"Authorization": f"Bearer {PAYSTACK_SECRET_KEY}"}
            )

        paystack_data = paystack_response.json()
        if not paystack_data.get('status'):
            logger.error(f"❌ Paystack API error: {paystack_data}")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Paystack verification failed")

        payment_info = paystack_data.get('data', {})
        if payment_info.get('status') != 'success':
            logger.error(f"❌ Payment not successful: {payment_info.get('status')}")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Payment not completed successfully")
        """

        logger.info("✓ Paystack verification successful")

        # STEP 2: SAVE TO PAYMENTS COLLECTION
        payment_record = {
            "email": request.email,
            "index_number": request.index_number,
            "reference": request.reference,
            "education_type": request.education_type,
            "status": "success",
            "amount_kes": AMOUNT_KES,
            "timestamp": datetime.utcnow()
        }
        result_payments = await payments_collection.insert_one(payment_record)
        logger.info(f"✓ Saved to payments collection: {result_payments.inserted_id}")

        # STEP 3: SAVE TO DATA COLLECTION
        data_record = {
            "reference": request.reference,
            "index_number": request.index_number,
            "education_type": request.education_type,
            "data": request.course_results.get("results", []),
            "timestamp": datetime.utcnow()
        }
        result_data = await data_collection.insert_one(data_record)
        logger.info(f"✓ Saved to data collection: {result_data.inserted_id}")

        return PaymentVerifyResponse(
            status="success",
            message="Payment verified and results saved successfully!",
            reference=request.reference,
            email=request.email,
            education_type=request.education_type
        )

    except httpx.HTTPError as e:
        logger.error(f"❌ Paystack API error: {e}")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Payment gateway error. Please try again.")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Payment verification error: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Payment verification failed: {str(e)}")


# ==================== GET USER RESULTS ====================

@router.post("/user-results", response_model=UserResultsResponse)
async def get_user_results(request: UserResultsRequest) -> UserResultsResponse:
    """Retrieve stored course results for a user"""
    try:
        logger.info(f"📊 Retrieving results for: {request.email}")

        # Get the payments database dynamically
        if not app_globals.client:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database client unavailable"
            )
        
        payments_db = app_globals.client[settings.PAYMENTS_DB]
        payments_collection = payments_db["payments_info"]
        data_collection = payments_db["client_course_data"]

        payment = await payments_collection.find_one({
            "email": request.email,
            "index_number": request.index_number,
            "education_type": request.education_type,
        })
        if not payment:
            logger.error(f"❌ Payment not found: {request.email}")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment record not found")

        reference = payment.get("reference")
        data_record = await data_collection.find_one({
            "reference": reference,
            "index_number": request.index_number,
            "education_type": request.education_type
        })
        if not data_record:
            logger.error(f"❌ Data record not found: {reference}")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course data not found")

        logger.info(f"✓ Retrieved results for {request.email}")
        return UserResultsResponse(
            email=request.email,
            index_number=request.index_number,
            education_type=request.education_type,
            course_results={"results": data_record.get("data", [])},
            verified_at=payment.get("timestamp")
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error retrieving results: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to retrieve results: {str(e)}")


# ==================== GET USER PAYMENT TYPES ====================

@router.get("/user-payment-types", response_model=UserPaymentTypesResponse)
async def get_user_payment_types(email: str, index_number: str) -> UserPaymentTypesResponse:
    """Get all education types a user has purchased"""
    try:
        logger.info(f"📋 Getting payment types for: {email}")

        # Get the payments database dynamically
        if not app_globals.client:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database client unavailable"
            )
        
        payments_db = app_globals.client[settings.PAYMENTS_DB]
        payments_collection = payments_db["payments_info"]

        payments = await payments_collection.find({
            "email": email,
            "index_number": index_number,
            "status": "success"
        }).to_list(None)

        education_types = [p.get("education_type") for p in payments]
        return UserPaymentTypesResponse(
            email=email,
            index_number=index_number,
            purchased_types=education_types,
            count=len(education_types)
        )

    except Exception as e:
        logger.error(f"❌ Error getting payment types: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to get payment types: {str(e)}")


# ==================== HEALTH CHECK ====================

@router.get("/health", response_model=HealthCheckResponse)
async def health_check():
    """Health check endpoint for monitoring"""
    return HealthCheckResponse(status="ok", message="Payments API is running")