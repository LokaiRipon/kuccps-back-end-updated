# ============================================================================
# FILE: api/endpoints/clusterWeight.py (NEW)
# ============================================================================
"""Cluster Weight Calculator payment endpoints"""

from fastapi import APIRouter, HTTPException, status, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime
import logging
from typing import Dict, Optional
from pydantic import BaseModel, EmailStr, Field

from app_entry.core import globals as app_globals
from app_entry.core.config import settings
from app_entry.core.dependencies import get_db_by_name

logger = logging.getLogger(__name__)
router = APIRouter()

# ==================== REQUEST SCHEMAS ====================

class VerifyClusterPaymentRequest(BaseModel):
    """Verify cluster weight calculator payment"""
    reference: str = Field(..., description="Paystack transaction reference")
    email: EmailStr = Field(..., description="User email")
    product: str = Field(..., description="Product type (should be 'cluster_weight_calculator')")
    cluster_weights: Dict[str, float] = Field(..., description="All 20 cluster weights calculated")
    kcse_overall: str = Field(..., description="KCSE overall grade (e.g., 'B', 'B+', 'C+')")


# ==================== RESPONSE SCHEMAS ====================

class VerifyClusterPaymentResponse(BaseModel):
    """Response after successful cluster payment verification"""
    status: str = Field(..., description="Status (success/failed)")
    message: str = Field(..., description="Response message")
    reference: str = Field(..., description="Paystack transaction reference")
    email: str = Field(..., description="User email")
    product: str = Field(..., description="Product purchased")


# ==================== VERIFY CLUSTER WEIGHT PAYMENT ====================

@router.post("/verify-cluster", response_model=VerifyClusterPaymentResponse)
async def verify_cluster_payment(request: VerifyClusterPaymentRequest) -> VerifyClusterPaymentResponse:
    """
    Verify cluster weight calculator payment and save results
    
    Steps:
    1. Validate request (cluster weights should have all 20 clusters)
    2. Save to cluster_weights collection
    3. Return success
    
    Data structure saved:
    {
        "reference": "transaction_ref",
        "email": "user@email.com",
        "kcse_overall": "B+",
        "cluster_weights": {
            "cl1": 34.486,
            "cl2": 33.001,
            ...
            "cl20": 31.640
        },
        "timestamp": datetime,
        "product": "cluster_weight_calculator"
    }
    """
    try:
        logger.info(f"🔄 Verifying cluster payment for: {request.email} (Ref: {request.reference})")

        # Validate that we have all 20 clusters
        expected_clusters = {f"cl{i}" for i in range(1, 21)}
        provided_clusters = set(request.cluster_weights.keys())
        
        if provided_clusters != expected_clusters:
            missing = expected_clusters - provided_clusters
            extra = provided_clusters - expected_clusters
            error_msg = f"Invalid clusters. "
            if missing:
                error_msg += f"Missing: {missing}. "
            if extra:
                error_msg += f"Extra: {extra}"
            logger.error(f"❌ {error_msg}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg
            )

        # Validate product type
        if request.product != "cluster_weight_calculator":
            logger.error(f"❌ Invalid product type: {request.product}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid product type"
            )

        # Get the payments database dynamically
        if not app_globals.client:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database client unavailable"
            )
        
        payments_db = app_globals.client[settings.PAYMENTS_DB]
        cluster_weights_collection = payments_db["cluster_weights"]

        # Save cluster weights to database
        cluster_record = {
            "reference": request.reference,
            "email": request.email,
            "kcse_overall": request.kcse_overall,
            "cluster_weights": request.cluster_weights,
            "product": request.product,
            "status": "success",
            "amount_kes": 50,
            "timestamp": datetime.utcnow()
        }
        
        result = await cluster_weights_collection.insert_one(cluster_record)
        logger.info(f"✓ Saved cluster weights to database: {result.inserted_id}")

        # Log cluster weights for reference
        logger.info(f"📊 Cluster weights for {request.email}:")
        for cluster_id in sorted(request.cluster_weights.keys()):
            logger.info(f"  {cluster_id}: {request.cluster_weights[cluster_id]}")

        logger.info(f"✅ Cluster payment verification complete for {request.email}")

        return VerifyClusterPaymentResponse(
            status="success",
            message="Cluster weight calculator payment verified successfully!",
            reference=request.reference,
            email=request.email,
            product=request.product
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Cluster payment verification error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Cluster payment verification failed: {str(e)}"
        )


# ==================== GET USER CLUSTER WEIGHTS ====================

@router.get("/user-cluster-weights/{email}")
async def get_user_cluster_weights(email: str) -> Dict:
    """
    Retrieve stored cluster weights for a user
    
    Returns the latest cluster weight calculation for the user
    """
    try:
        logger.info(f"📊 Retrieving cluster weights for: {email}")

        if not app_globals.client:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database client unavailable"
            )
        
        payments_db = app_globals.client[settings.PAYMENTS_DB]
        cluster_weights_collection = payments_db["cluster_weights"]

        # Get the most recent record for this user
        record = await cluster_weights_collection.find_one(
            {"email": email, "status": "success"},
            sort=[("timestamp", -1)]
        )

        if not record:
            logger.error(f"❌ No cluster weights found for: {email}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No cluster weight records found for this user"
            )

        # Remove MongoDB's ObjectId for JSON serialization
        record.pop("_id", None)
        record["timestamp"] = record["timestamp"].isoformat()

        logger.info(f"✓ Retrieved cluster weights for {email}")
        return record

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error retrieving cluster weights: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve cluster weights: {str(e)}"
        )


# ==================== HEALTH CHECK ====================

@router.get("/cluster-health")
async def cluster_health_check():
    """Health check for cluster weights endpoint"""
    return {
        "status": "ok",
        "message": "Cluster Weights Calculator API is running",
        "product": "cluster_weight_calculator"
    }