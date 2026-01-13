"""Payment endpoints - my basic implementation"""

from fastapi import APIRouter, HTTPException, status, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime
import logging

from app.core.dependencies import get_db
from app.schemas.payments import PaymentInitializeRequest, PaymentResponse

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/initialize", response_model=PaymentResponse)
async def initialize_payment(
    request: PaymentInitializeRequest,
    db: AsyncIOMotorDatabase = Depends(get_db)
) -> PaymentResponse:
    """
    Initialize payment session
    
    Frontend calls this when user clicks "Save & Get Certificate"
    
    Stores payment intent in database
    """
    try:
        logger.info(f"Initializing payment for {request.email}")
        
        # Create payment log entry
        payment_doc = {
            "email": request.email,
            "index_number": request.index_number,
            "education_type": request.education_type,
            "amount": request.amount,
            "status": "pending",
            "created_at": datetime.utcnow()
        }
        
        result = await db["payments_log"].insert_one(payment_doc)
        
        return PaymentResponse(
            payment_id=str(result.inserted_id),
            amount=request.amount,
            email=request.email
        )
    except Exception as e:
        logger.error(f"Payment initialization error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initialize payment"
        )


@router.post("/verify")
async def verify_payment(
    reference: str,
    type: str,
    db: AsyncIOMotorDatabase = Depends(get_db)
) -> dict:
    """
    Verify payment with Paystack
    
    After successful Paystack payment, frontend calls this
    to mark payment as completed in our database
    
    This converts the guest user to a saved user
    """
    try:
        logger.info(f"Verifying payment: {reference}")
        
        # TODO: Call Paystack API to verify payment is real
        # For now, assume it's valid
        
        # Mark payment as completed
        await db["payments_log"].update_one(
            {"_id": reference},
            {
                "$set": {
                    "status": "completed",
                    "verified_at": datetime.utcnow()
                }
            }
        )
        
        logger.info(f"✓ Payment verified: {reference}")
        
        return {
            "status": "verified",
            "message": "Payment successful!"
        }
    except Exception as e:
        logger.error(f"Payment verification error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Payment verification failed"
        )


@router.post("/save-user-info")
async def save_user_info(
    email: str,
    full_name: str,
    index_number: str,
    db: AsyncIOMotorDatabase = Depends(get_db)
) -> dict:
    """
    Save full name and complete registration
    
    Called after successful payment
    """
    try:
        logger.info(f"Saving user info for {email}")
        
        # Update or create user record with full name
        await db["payments"].update_one(
            {"$or": [{"email": email}, {"ksce_index": index_number}]},
            {
                "$set": {
                    "full_name": full_name,
                    "payment_completed_at": datetime.utcnow()
                }
            },
            upsert=True
        )
        
        return {
            "status": "success",
            "message": "User info saved successfully!"
        }
    except Exception as e:
        logger.error(f"Error saving user info: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save user info"
        )