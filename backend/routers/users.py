"""
User management routes for admin operations.
Provides CRUD operations for users with role-based access control.
"""

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from typing import List, Optional
from io import StringIO
import csv
import logging

from database import get_db
from models import User, UserRole, AuditLog, LoginAttempt
from services.auth_service import AuthService
from middleware.auth_middleware import require_admin, get_client_ip

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/users", tags=["users"])


class UserCreate(BaseModel):
    """User creation model."""

    username: str
    email: EmailStr
    password: str
    role: UserRole = UserRole.TRAINEE


class UserUpdate(BaseModel):
    """User update model."""

    email: Optional[EmailStr] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None


class UserResponse(BaseModel):
    """User response model."""

    id: int
    username: str
    email: str
    role: UserRole
    is_active: bool
    mfa_enabled: bool
    last_login: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UserDetailResponse(UserResponse):
    """Detailed user response with activity info."""

    failed_login_attempts: int
    locked_until: Optional[datetime]


class UserListResponse(BaseModel):
    """User list response with pagination."""

    total: int
    page: int
    page_size: int
    items: List[UserResponse]


@router.get("", response_model=UserListResponse)
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    search: Optional[str] = None,
    role: Optional[UserRole] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> dict:
    """
    List all users with pagination and filtering.

    Args:
        page: Page number
        page_size: Items per page
        search: Search by username or email
        role: Filter by role
        db: Database session
        current_user: Current admin user

    Returns:
        Paginated user list
    """
    query = db.query(User)

    # Search filter
    if search:
        query = query.filter(
            (User.username.ilike(f"%{search}%")) | (User.email.ilike(f"%{search}%"))
        )

    # Role filter
    if role:
        query = query.filter(User.role == role)

    # Count total
    total = query.count()

    # Pagination
    users = query.offset((page - 1) * page_size).limit(page_size).all()

    logger.info(f"Listed users: admin={current_user.id}, page={page}, search={search}")

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": users,
    }


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> User:
    """
    Create a new user.

    Args:
        user_data: User creation data
        db: Database session
        current_user: Current admin user

    Returns:
        Created user

    Raises:
        HTTPException: If user already exists or password policy violated
    """
    # Check if user exists
    existing_user = db.query(User).filter(
        (User.username == user_data.username) | (User.email == user_data.email)
    ).first()
    if existing_user:
        logger.warning(f"User creation failed: user already exists: {user_data.username}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this username or email already exists",
        )

    # Enforce password policy
    is_valid, error_msg = AuthService.enforce_password_policy(user_data.password)
    if not is_valid:
        logger.warning(f"User creation failed: password policy violation: {user_data.username}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg,
        )

    # Create user
    hashed_password = AuthService.hash_password(user_data.password)
    user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=hashed_password,
        role=user_data.role,
        is_active=True,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    # Log audit
    audit_log = AuditLog(
        user_id=current_user.id,
        action="CREATE",
        resource_type="User",
        resource_id=user.id,
        ip_address="127.0.0.1",
    )
    db.add(audit_log)
    db.commit()

    logger.info(f"User created: {user.username} by admin {current_user.id}")

    return user


@router.get("/{user_id}", response_model=UserDetailResponse)
async def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> User:
    """
    Get user details by ID.

    Args:
        user_id: User ID
        db: Database session
        current_user: Current admin user

    Returns:
        User details

    Raises:
        HTTPException: If user not found
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        logger.warning(f"User not found: {user_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return user


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> User:
    """
    Update user details.

    Args:
        user_id: User ID
        user_data: Update data
        db: Database session
        current_user: Current admin user

    Returns:
        Updated user

    Raises:
        HTTPException: If user not found or update fails
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        logger.warning(f"User update failed: user not found: {user_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Update fields
    if user_data.email:
        # Check email uniqueness
        existing = db.query(User).filter(
            (User.email == user_data.email) & (User.id != user_id)
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already in use",
            )
        user.email = user_data.email

    if user_data.role is not None:
        user.role = user_data.role

    if user_data.is_active is not None:
        user.is_active = user_data.is_active

    user.updated_at = datetime.now(timezone.utc)

    db.add(user)
    db.commit()
    db.refresh(user)

    # Log audit
    audit_log = AuditLog(
        user_id=current_user.id,
        action="UPDATE",
        resource_type="User",
        resource_id=user.id,
        ip_address="127.0.0.1",
    )
    db.add(audit_log)
    db.commit()

    logger.info(f"User updated: {user.username} by admin {current_user.id}")

    return user


@router.delete("/{user_id}")
async def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> dict:
    """
    Deactivate a user (soft delete).

    Args:
        user_id: User ID
        db: Database session
        current_user: Current admin user

    Returns:
        Success message

    Raises:
        HTTPException: If user not found
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        logger.warning(f"User delete failed: user not found: {user_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Prevent deleting self
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account",
        )

    user.is_active = False
    user.updated_at = datetime.now(timezone.utc)

    db.add(user)
    db.commit()

    # Log audit
    audit_log = AuditLog(
        user_id=current_user.id,
        action="DELETE",
        resource_type="User",
        resource_id=user.id,
        ip_address="127.0.0.1",
    )
    db.add(audit_log)
    db.commit()

    logger.info(f"User deactivated: {user.username} by admin {current_user.id}")

    return {"message": "User deactivated successfully"}


@router.post("/{user_id}/reset-password")
async def reset_password(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> dict:
    """
    Reset user password to a temporary password.

    Args:
        user_id: User ID
        db: Database session
        current_user: Current admin user

    Returns:
        Temporary password

    Raises:
        HTTPException: If user not found
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        logger.warning(f"Password reset failed: user not found: {user_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Generate temporary password
    import secrets
    import string

    temp_password = "".join(
        secrets.choice(string.ascii_letters + string.digits + "!@#$%^&*")
        for _ in range(12)
    )

    user.hashed_password = AuthService.hash_password(temp_password)
    user.updated_at = datetime.now(timezone.utc)

    db.add(user)
    db.commit()

    # Log audit
    audit_log = AuditLog(
        user_id=current_user.id,
        action="RESET_PASSWORD",
        resource_type="User",
        resource_id=user.id,
        ip_address="127.0.0.1",
    )
    db.add(audit_log)
    db.commit()

    logger.info(f"Password reset: {user.username} by admin {current_user.id}")

    return {
        "message": "Password reset successfully",
        "temporary_password": temp_password,
        "user_id": user.id,
    }


@router.post("/{user_id}/toggle-mfa")
async def toggle_mfa(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> dict:
    """
    Toggle MFA for a user.

    Args:
        user_id: User ID
        db: Database session
        current_user: Current admin user

    Returns:
        MFA status and setup URI if enabling

    Raises:
        HTTPException: If user not found
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        logger.warning(f"MFA toggle failed: user not found: {user_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if user.mfa_enabled:
        # Disable MFA
        user.mfa_enabled = False
        user.mfa_secret = None
        message = "MFA disabled"
    else:
        # Enable MFA
        secret = AuthService.generate_totp_secret()
        user.mfa_secret = secret
        user.mfa_enabled = True

        provisioning_uri = AuthService.get_totp_provisioning_uri(
            secret, user.username, "LMS Course Builder"
        )
        qr_code = AuthService.generate_totp_qr_code(provisioning_uri)

        user.updated_at = datetime.now(timezone.utc)
        db.add(user)
        db.commit()

        logger.info(f"MFA enabled: {user.username} by admin {current_user.id}")

        return {
            "mfa_enabled": True,
            "message": "MFA enabled. User must scan QR code.",
            "qr_code": qr_code,
            "secret": secret,
        }

    user.updated_at = datetime.now(timezone.utc)
    db.add(user)
    db.commit()

    # Log audit
    audit_log = AuditLog(
        user_id=current_user.id,
        action="TOGGLE_MFA",
        resource_type="User",
        resource_id=user.id,
        ip_address="127.0.0.1",
    )
    db.add(audit_log)
    db.commit()

    logger.info(f"MFA disabled: {user.username} by admin {current_user.id}")

    return {"mfa_enabled": user.mfa_enabled, "message": message}


@router.post("/bulk-import")
async def bulk_import_users(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> dict:
    """
    Bulk import users from CSV file.
    CSV format: username,email,password,role

    Args:
        file: CSV file
        db: Database session
        current_user: Current admin user

    Returns:
        Import results

    Raises:
        HTTPException: If file parsing fails
    """
    try:
        contents = await file.read()
        csv_reader = csv.DictReader(StringIO(contents.decode("utf-8")))

        created = 0
        failed = 0
        errors = []

        for row_num, row in enumerate(csv_reader, start=2):
            try:
                username = row.get("username", "").strip()
                email = row.get("email", "").strip()
                password = row.get("password", "").strip()
                role = row.get("role", "trainee").strip().lower()

                # Validate
                if not username or not email or not password:
                    errors.append(f"Row {row_num}: Missing required fields")
                    failed += 1
                    continue

                # Check if user exists
                if db.query(User).filter(
                    (User.username == username) | (User.email == email)
                ).first():
                    errors.append(f"Row {row_num}: User already exists")
                    failed += 1
                    continue

                # Validate password policy
                is_valid, error_msg = AuthService.enforce_password_policy(password)
                if not is_valid:
                    errors.append(f"Row {row_num}: {error_msg}")
                    failed += 1
                    continue

                # Create user
                user_role = UserRole(role) if role in [r.value for r in UserRole] else UserRole.TRAINEE
                user = User(
                    username=username,
                    email=email,
                    hashed_password=AuthService.hash_password(password),
                    role=user_role,
                    is_active=True,
                )

                db.add(user)
                created += 1

            except Exception as e:
                errors.append(f"Row {row_num}: {str(e)}")
                failed += 1

        db.commit()

        # Log audit
        audit_log = AuditLog(
            user_id=current_user.id,
            action="BULK_IMPORT",
            resource_type="User",
            details={"created": created, "failed": failed},
            ip_address="127.0.0.1",
        )
        db.add(audit_log)
        db.commit()

        logger.info(f"Bulk import: {created} created, {failed} failed by admin {current_user.id}")

        return {
            "created": created,
            "failed": failed,
            "errors": errors[:10],  # Return first 10 errors
        }

    except Exception as e:
        logger.error(f"Bulk import failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File parsing failed: {str(e)}",
        )


@router.get("/{user_id}/activity")
async def get_user_activity(
    user_id: int,
    limit: int = Query(50, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> dict:
    """
    Get user activity log.

    Args:
        user_id: User ID
        limit: Number of log entries to return
        db: Database session
        current_user: Current admin user

    Returns:
        Login attempts and audit logs

    Raises:
        HTTPException: If user not found
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Get login attempts
    login_attempts = (
        db.query(LoginAttempt)
        .filter(LoginAttempt.user_id == user_id)
        .order_by(LoginAttempt.timestamp.desc())
        .limit(limit)
        .all()
    )

    # Get audit logs
    audit_logs = (
        db.query(AuditLog)
        .filter(AuditLog.user_id == user_id)
        .order_by(AuditLog.timestamp.desc())
        .limit(limit)
        .all()
    )

    return {
        "user_id": user_id,
        "login_attempts": login_attempts,
        "audit_logs": audit_logs,
    }
