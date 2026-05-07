"""
Developer tools routes for monitoring and debugging.
Provides system health, error logs, API usage tracking, and feature flags.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
from typing import List, Optional
import logging
import psutil
import os
from pathlib import Path

from database import get_db, engine
from models import User, ErrorLog, ApiUsage, FeatureFlag
from middleware.auth_middleware import require_admin
from config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/dev", tags=["dev"])


class ErrorLogResponse(BaseModel):
    """Error log response model."""

    id: int
    request_id: str
    error_type: str
    message: str
    endpoint: Optional[str]
    method: Optional[str]
    timestamp: datetime

    class Config:
        from_attributes = True


class ErrorLogListResponse(BaseModel):
    """Error log list response with pagination."""

    total: int
    page: int
    page_size: int
    items: List[ErrorLogResponse]


class HealthResponse(BaseModel):
    """System health response model."""

    status: str
    uptime_seconds: float
    cpu_percent: float
    memory_percent: float
    memory_available_mb: float
    disk_percent: float
    database_size_mb: float
    timestamp: datetime


class ApiUsageStats(BaseModel):
    """API usage statistics."""

    total_requests: int
    total_tokens: int
    total_cost: float
    average_tokens_per_request: float
    timestamp: datetime


class FeatureFlagResponse(BaseModel):
    """Feature flag response model."""

    id: int
    name: str
    enabled: bool
    description: Optional[str]
    updated_at: datetime

    class Config:
        from_attributes = True


class FeatureFlagCreate(BaseModel):
    """Feature flag creation model."""

    name: str
    enabled: bool = False
    description: Optional[str] = None


class FeatureFlagUpdate(BaseModel):
    """Feature flag update model."""

    enabled: bool


class EnvInfoResponse(BaseModel):
    """Environment info response model."""

    app_version: str
    environment: str
    python_version: str
    database_url: str
    upload_dir: str


# Store startup time
_startup_time = datetime.now(timezone.utc)


@router.get("/errors", response_model=ErrorLogListResponse)
async def get_error_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    error_type: Optional[str] = None,
    endpoint: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> dict:
    """
    Get paginated error logs.

    Args:
        page: Page number
        page_size: Items per page
        error_type: Filter by error type
        endpoint: Filter by endpoint
        db: Database session
        current_user: Current admin user

    Returns:
        Paginated error logs
    """
    query = db.query(ErrorLog)

    if error_type:
        query = query.filter(ErrorLog.error_type == error_type)

    if endpoint:
        query = query.filter(ErrorLog.endpoint.ilike(f"%{endpoint}%"))

    total = query.count()

    logs = (
        query
        .order_by(ErrorLog.timestamp.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    logger.info(f"Error logs accessed by admin {current_user.id}")

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": logs,
    }


@router.get("/health", response_model=HealthResponse)
async def get_health(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> dict:
    """
    Get system health information.

    Args:
        db: Database session
        current_user: Current admin user

    Returns:
        System health metrics
    """
    try:
        # Calculate uptime
        uptime = (datetime.now(timezone.utc) - _startup_time).total_seconds()

        # Get CPU and memory info
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage("/")

        # Get database size
        db_size_mb = 0
        try:
            if os.path.exists("./lms.db"):
                db_size_mb = os.path.getsize("./lms.db") / (1024 * 1024)
        except Exception as e:
            logger.warning(f"Could not get database size: {str(e)}")

        logger.info(f"Health check accessed by admin {current_user.id}")

        return {
            "status": "healthy",
            "uptime_seconds": uptime,
            "cpu_percent": cpu_percent,
            "memory_percent": memory.percent,
            "memory_available_mb": memory.available / (1024 * 1024),
            "disk_percent": disk.percent,
            "database_size_mb": db_size_mb,
            "timestamp": datetime.now(timezone.utc),
        }

    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return {
            "status": "error",
            "uptime_seconds": 0,
            "cpu_percent": 0,
            "memory_percent": 0,
            "memory_available_mb": 0,
            "disk_percent": 0,
            "database_size_mb": 0,
            "timestamp": datetime.now(timezone.utc),
        }


@router.get("/api-usage", response_model=ApiUsageStats)
async def get_api_usage(
    days: int = Query(7, ge=1, le=90),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> dict:
    """
    Get Claude API usage statistics.

    Args:
        days: Number of days to analyze
        db: Database session
        current_user: Current admin user

    Returns:
        API usage statistics
    """
    since = datetime.now(timezone.utc) - timedelta(days=days)

    query = db.query(ApiUsage).filter(ApiUsage.timestamp >= since)

    total_requests = query.count()
    total_tokens = sum(u.tokens_used for u in query.all()) if total_requests > 0 else 0
    total_cost = sum(u.cost_estimate for u in query.all()) if total_requests > 0 else 0.0
    average_tokens = total_tokens / total_requests if total_requests > 0 else 0

    logger.info(f"API usage accessed by admin {current_user.id}")

    return {
        "total_requests": total_requests,
        "total_tokens": total_tokens,
        "total_cost": total_cost,
        "average_tokens_per_request": average_tokens,
        "timestamp": datetime.now(timezone.utc),
    }


@router.get("/feature-flags", response_model=List[FeatureFlagResponse])
async def get_feature_flags(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> List[FeatureFlag]:
    """
    Get all feature flags.

    Args:
        db: Database session
        current_user: Current admin user

    Returns:
        List of feature flags
    """
    flags = db.query(FeatureFlag).order_by(FeatureFlag.updated_at.desc()).all()

    logger.info(f"Feature flags accessed by admin {current_user.id}")

    return flags


@router.post("/feature-flags", response_model=FeatureFlagResponse, status_code=status.HTTP_201_CREATED)
async def create_feature_flag(
    flag_data: FeatureFlagCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> FeatureFlag:
    """
    Create a new feature flag.

    Args:
        flag_data: Feature flag data
        db: Database session
        current_user: Current admin user

    Returns:
        Created feature flag

    Raises:
        HTTPException: If flag already exists
    """
    # Check if flag exists
    existing = db.query(FeatureFlag).filter(FeatureFlag.name == flag_data.name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Feature flag already exists",
        )

    flag = FeatureFlag(
        name=flag_data.name,
        enabled=flag_data.enabled,
        description=flag_data.description,
        updated_by=current_user.id,
    )

    db.add(flag)
    db.commit()
    db.refresh(flag)

    logger.info(f"Feature flag created: {flag_data.name} by admin {current_user.id}")

    return flag


@router.put("/feature-flags/{flag_id}", response_model=FeatureFlagResponse)
async def update_feature_flag(
    flag_id: int,
    flag_data: FeatureFlagUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> FeatureFlag:
    """
    Update a feature flag.

    Args:
        flag_id: Feature flag ID
        flag_data: Update data
        db: Database session
        current_user: Current admin user

    Returns:
        Updated feature flag

    Raises:
        HTTPException: If flag not found
    """
    flag = db.query(FeatureFlag).filter(FeatureFlag.id == flag_id).first()
    if not flag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Feature flag not found",
        )

    flag.enabled = flag_data.enabled
    flag.updated_at = datetime.now(timezone.utc)
    flag.updated_by = current_user.id

    db.add(flag)
    db.commit()
    db.refresh(flag)

    logger.info(f"Feature flag updated: {flag.name} enabled={flag_data.enabled} by admin {current_user.id}")

    return flag


@router.get("/env-info", response_model=EnvInfoResponse)
async def get_env_info(
    current_user: User = Depends(require_admin),
) -> dict:
    """
    Get environment information.

    Args:
        current_user: Current admin user

    Returns:
        Environment info
    """
    import sys

    logger.info(f"Environment info accessed by admin {current_user.id}")

    return {
        "app_version": settings.APP_VERSION,
        "environment": os.getenv("ENVIRONMENT", "development"),
        "python_version": sys.version,
        "database_url": settings.DB_URL,
        "upload_dir": settings.UPLOAD_DIR,
    }
