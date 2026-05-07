"""
Security management routes for admin operations.
Provides session management, login monitoring, and audit logging.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from typing import List, Optional
import logging

from database import get_db
from models import (
    User,
    Session as DBSession,
    AuditLog,
    LoginAttempt,
    IpAllowlist,
)
from middleware.auth_middleware import require_admin

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/security", tags=["security"])


class SessionResponse(BaseModel):
    """Active session response model."""

    id: int
    user_id: int
    ip_address: str
    user_agent: Optional[str]
    created_at: datetime
    expires_at: datetime
    is_active: bool

    class Config:
        from_attributes = True


class LoginAttemptResponse(BaseModel):
    """Login attempt response model."""

    id: int
    username: str
    ip_address: str
    success: bool
    timestamp: datetime

    class Config:
        from_attributes = True


class AuditLogResponse(BaseModel):
    """Audit log response model."""

    id: int
    user_id: Optional[int]
    action: str
    resource_type: str
    resource_id: Optional[int]
    ip_address: str
    timestamp: datetime

    class Config:
        from_attributes = True


class AuditLogListResponse(BaseModel):
    """Audit log list response with pagination."""

    total: int
    page: int
    page_size: int
    items: List[AuditLogResponse]


class SecurityDashboardResponse(BaseModel):
    """Security dashboard summary."""

    active_sessions: int
    failed_logins_24h: int
    locked_accounts: int
    recent_login_attempts: List[LoginAttemptResponse]
    recent_audit_logs: List[AuditLogResponse]


class IpAllowlistItem(BaseModel):
    """IP allowlist item."""

    id: int
    ip_address: str
    description: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class IpAllowlistCreate(BaseModel):
    """Create IP allowlist item."""

    ip_address: str
    description: Optional[str] = None


@router.get("/dashboard", response_model=SecurityDashboardResponse)
async def get_security_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> dict:
    """
    Get security dashboard summary.

    Args:
        db: Database session
        current_user: Current admin user

    Returns:
        Security dashboard data
    """
    from datetime import timedelta

    now = datetime.now(timezone.utc)
    yesterday = now - timedelta(hours=24)

    # Count active sessions
    active_sessions = db.query(DBSession).filter(
        DBSession.is_active == True,
        DBSession.expires_at > now,
    ).count()

    # Count failed logins in last 24 hours
    failed_logins = db.query(LoginAttempt).filter(
        LoginAttempt.success == False,
        LoginAttempt.timestamp >= yesterday,
    ).count()

    # Count locked accounts
    locked_accounts = db.query(User).filter(
        User.locked_until > now,
    ).count()

    # Get recent login attempts
    recent_attempts = (
        db.query(LoginAttempt)
        .order_by(LoginAttempt.timestamp.desc())
        .limit(10)
        .all()
    )

    # Get recent audit logs
    recent_logs = (
        db.query(AuditLog)
        .order_by(AuditLog.timestamp.desc())
        .limit(10)
        .all()
    )

    logger.info(f"Security dashboard accessed by admin {current_user.id}")

    return {
        "active_sessions": active_sessions,
        "failed_logins_24h": failed_logins,
        "locked_accounts": locked_accounts,
        "recent_login_attempts": recent_attempts,
        "recent_audit_logs": recent_logs,
    }


@router.get("/sessions", response_model=List[SessionResponse])
async def list_sessions(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    user_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> List[DBSession]:
    """
    List active sessions.

    Args:
        page: Page number
        page_size: Items per page
        user_id: Filter by user ID
        db: Database session
        current_user: Current admin user

    Returns:
        List of active sessions
    """
    query = db.query(DBSession).filter(DBSession.is_active == True)

    if user_id:
        query = query.filter(DBSession.user_id == user_id)

    sessions = (
        query
        .order_by(DBSession.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    logger.info(f"Sessions listed by admin {current_user.id}")

    return sessions


@router.delete("/sessions/{session_id}")
async def kill_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> dict:
    """
    Kill a user session.

    Args:
        session_id: Session ID
        db: Database session
        current_user: Current admin user

    Returns:
        Success message

    Raises:
        HTTPException: If session not found
    """
    session = db.query(DBSession).filter(DBSession.id == session_id).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )

    session.is_active = False
    db.add(session)
    db.commit()

    logger.info(f"Session {session_id} killed by admin {current_user.id}")

    return {"message": "Session terminated"}


@router.get("/login-attempts", response_model=List[LoginAttemptResponse])
async def get_login_attempts(
    limit: int = Query(100, ge=1, le=1000),
    username: Optional[str] = None,
    success: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> List[LoginAttempt]:
    """
    Get recent login attempts.

    Args:
        limit: Number of attempts to return
        username: Filter by username
        success: Filter by success/failure
        db: Database session
        current_user: Current admin user

    Returns:
        List of login attempts
    """
    query = db.query(LoginAttempt)

    if username:
        query = query.filter(LoginAttempt.username.ilike(f"%{username}%"))

    if success is not None:
        query = query.filter(LoginAttempt.success == success)

    attempts = (
        query
        .order_by(LoginAttempt.timestamp.desc())
        .limit(limit)
        .all()
    )

    logger.info(f"Login attempts accessed by admin {current_user.id}")

    return attempts


@router.get("/audit-log", response_model=AuditLogListResponse)
async def get_audit_log(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    action: Optional[str] = None,
    resource_type: Optional[str] = None,
    user_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> dict:
    """
    Get paginated audit log.

    Args:
        page: Page number
        page_size: Items per page
        action: Filter by action (CREATE, UPDATE, DELETE, etc.)
        resource_type: Filter by resource type (User, Course, etc.)
        user_id: Filter by user ID
        db: Database session
        current_user: Current admin user

    Returns:
        Paginated audit log
    """
    query = db.query(AuditLog)

    if action:
        query = query.filter(AuditLog.action == action.upper())

    if resource_type:
        query = query.filter(AuditLog.resource_type == resource_type)

    if user_id:
        query = query.filter(AuditLog.user_id == user_id)

    total = query.count()

    logs = (
        query
        .order_by(AuditLog.timestamp.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    logger.info(f"Audit log accessed by admin {current_user.id}")

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": logs,
    }


@router.get("/ip-allowlist", response_model=List[IpAllowlistItem])
async def get_ip_allowlist(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> List[IpAllowlist]:
    """
    Get IP allowlist.

    Args:
        db: Database session
        current_user: Current admin user

    Returns:
        List of allowed IPs
    """
    ips = db.query(IpAllowlist).order_by(IpAllowlist.created_at.desc()).all()

    logger.info(f"IP allowlist accessed by admin {current_user.id}")

    return ips


@router.post("/ip-allowlist", response_model=IpAllowlistItem, status_code=status.HTTP_201_CREATED)
async def add_ip_allowlist(
    ip_data: IpAllowlistCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> IpAllowlist:
    """
    Add IP to allowlist.

    Args:
        ip_data: IP address and description
        db: Database session
        current_user: Current admin user

    Returns:
        Created allowlist entry

    Raises:
        HTTPException: If IP already exists
    """
    # Check if IP already exists
    existing = db.query(IpAllowlist).filter(
        IpAllowlist.ip_address == ip_data.ip_address
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="IP already in allowlist",
        )

    ip_allowlist = IpAllowlist(
        ip_address=ip_data.ip_address,
        description=ip_data.description,
    )

    db.add(ip_allowlist)
    db.commit()
    db.refresh(ip_allowlist)

    logger.info(f"IP {ip_data.ip_address} added to allowlist by admin {current_user.id}")

    return ip_allowlist


@router.delete("/ip-allowlist/{ip_id}")
async def remove_ip_allowlist(
    ip_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> dict:
    """
    Remove IP from allowlist.

    Args:
        ip_id: IP allowlist entry ID
        db: Database session
        current_user: Current admin user

    Returns:
        Success message

    Raises:
        HTTPException: If entry not found
    """
    ip_entry = db.query(IpAllowlist).filter(IpAllowlist.id == ip_id).first()
    if not ip_entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="IP allowlist entry not found",
        )

    db.delete(ip_entry)
    db.commit()

    logger.info(f"IP {ip_entry.ip_address} removed from allowlist by admin {current_user.id}")

    return {"message": "IP removed from allowlist"}
