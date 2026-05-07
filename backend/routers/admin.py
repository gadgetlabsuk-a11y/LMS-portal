"""
Admin dashboard routes.
Provides summary statistics and audit log for the admin dashboard.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta, timezone
from typing import Optional

from database import get_db
from models import User, Course, Enrollment, AuditLog, ApiUsage, UserRole
from middleware.auth_middleware import get_current_user, require_role

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/stats")
async def get_dashboard_stats(
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    """Get dashboard KPI statistics."""
    total_users = db.query(func.count(User.id)).scalar() or 0
    active_courses = (
        db.query(func.count(Course.id))
        .filter(Course.status == "published")
        .scalar()
        or 0
    )
    total_enrollments = db.query(func.count(Enrollment.id)).scalar() or 0
    completed_enrollments = (
        db.query(func.count(Enrollment.id))
        .filter(Enrollment.completed == True)
        .scalar()
        or 0
    )
    completion_rate = (
        round((completed_enrollments / total_enrollments) * 100, 1)
        if total_enrollments > 0
        else 0
    )

    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    api_calls_today = (
        db.query(func.count(ApiUsage.id))
        .filter(ApiUsage.timestamp >= today)
        .scalar()
        or 0
    )

    return {
        "total_users": total_users,
        "active_courses": active_courses,
        "completion_rate": completion_rate,
        "api_calls_today": api_calls_today,
        "total_enrollments": total_enrollments,
    }


@router.get("/audit-log")
async def get_audit_log(
    limit: int = Query(default=20, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    """Get recent audit log entries."""
    logs = (
        db.query(AuditLog)
        .order_by(AuditLog.timestamp.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return [
        {
            "id": log.id,
            "user_id": log.user_id,
            "action": log.action,
            "resource_type": log.resource_type,
            "resource_id": log.resource_id,
            "details": log.details,
            "ip_address": log.ip_address,
            "timestamp": log.timestamp.isoformat() if log.timestamp else None,
        }
        for log in logs
    ]
