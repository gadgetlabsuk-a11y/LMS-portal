"""
Authentication routes for login, logout, token refresh, and MFA.
Handles user authentication and session management.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
from database import get_db
from models import User, Session as DBSession, LoginAttempt
from services.auth_service import AuthService
from middleware.auth_middleware import (
    get_current_user,
    get_current_active_user,
    get_client_ip,
    get_user_agent,
)
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginRequest(BaseModel):
    """Login request model."""

    username: str
    password: str


class LoginResponse(BaseModel):
    """Login response model."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    """Refresh token request model."""

    refresh_token: str


class VerifyMFARequest(BaseModel):
    """MFA verification request model."""

    code: str


class CurrentUserResponse(BaseModel):
    """Current user response model."""

    id: int
    username: str
    email: str
    role: str
    is_active: bool
    mfa_enabled: bool
    last_login: datetime

    class Config:
        from_attributes = True


@router.post("/login", response_model=LoginResponse)
async def login(
    request: Request,
    login_data: LoginRequest,
    db: Session = Depends(get_db),
) -> dict:
    """
    Authenticate user and return JWT tokens.

    Args:
        request: HTTP request
        login_data: Username and password
        db: Database session

    Returns:
        Access token, refresh token, and token type

    Raises:
        HTTPException: If credentials invalid or account locked
    """
    client_ip = await get_client_ip(request)
    user_agent = await get_user_agent(request)

    # Find user
    user = db.query(User).filter(User.username == login_data.username).first()

    # Record login attempt
    login_attempt = LoginAttempt(
        username=login_data.username,
        user_id=user.id if user else None,
        ip_address=client_ip,
        success=False,
        timestamp=datetime.now(timezone.utc),
    )

    # Check if account is locked
    if user and AuthService.is_account_locked(user.locked_until):
        db.add(login_attempt)
        db.commit()
        logger.warning(f"Login attempt for locked account: {login_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is locked due to too many failed login attempts",
        )

    # Verify user exists and password is correct
    if not user or not AuthService.verify_password(login_data.password, user.hashed_password):
        if user:
            user.failed_login_attempts += 1

            # Lock account if max attempts exceeded
            if user.failed_login_attempts >= 5:
                user.locked_until = datetime.now(timezone.utc) + AuthService.get_account_lockout_duration()
                logger.warning(f"Account locked: {user.username}")

            db.add(user)

        db.add(login_attempt)
        db.commit()
        logger.warning(f"Failed login attempt: {login_data.username} from {client_ip}")

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    # Check if user is active
    if not user.is_active:
        db.add(login_attempt)
        db.commit()
        logger.warning(f"Login attempt for inactive user: {login_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User is inactive",
        )

    # Reset failed attempts on successful login
    user.failed_login_attempts = 0
    user.locked_until = None
    user.last_login = datetime.now(timezone.utc)

    # Create tokens
    access_token = AuthService.create_access_token(
        user_id=user.id,
        username=user.username,
        role=user.role.value,
    )
    refresh_token = AuthService.create_refresh_token(
        user_id=user.id,
        username=user.username,
    )

    # Create session
    session = DBSession(
        user_id=user.id,
        token=access_token,
        ip_address=client_ip,
        user_agent=user_agent,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=30),
        is_active=True,
    )

    # Record successful login
    login_attempt.success = True

    db.add(user)
    db.add(session)
    db.add(login_attempt)
    db.commit()

    logger.info(f"Successful login: {user.username}")

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


@router.post("/refresh", response_model=LoginResponse)
async def refresh_token(
    refresh_data: RefreshRequest,
    db: Session = Depends(get_db),
) -> dict:
    """
    Refresh access token using refresh token.

    Args:
        refresh_data: Refresh token
        db: Database session

    Returns:
        New access token and refresh token

    Raises:
        HTTPException: If refresh token invalid
    """
    # Verify refresh token
    token_data = AuthService.verify_token(refresh_data.refresh_token)
    if token_data is None or token_data.get("type") != "refresh":
        logger.warning("Invalid refresh token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    # Get user
    user = db.query(User).filter(User.id == token_data["user_id"]).first()
    if not user or not user.is_active:
        logger.warning(f"Refresh token for invalid user: {token_data.get('user_id')}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    # Create new tokens
    access_token = AuthService.create_access_token(
        user_id=user.id,
        username=user.username,
        role=user.role.value,
    )
    new_refresh_token = AuthService.create_refresh_token(
        user_id=user.id,
        username=user.username,
    )

    logger.info(f"Token refreshed for user: {user.username}")

    return {
        "access_token": access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer",
    }


@router.post("/logout")
async def logout(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> dict:
    """
    Logout user by deactivating all sessions.

    Args:
        request: HTTP request
        current_user: Current authenticated user
        db: Database session

    Returns:
        Success message
    """
    # Get auth token from header
    auth_header = request.headers.get("Authorization", "")
    token = auth_header.replace("Bearer ", "") if auth_header.startswith("Bearer ") else ""

    # Deactivate all sessions for user
    sessions = db.query(DBSession).filter(
        DBSession.user_id == current_user.id,
        DBSession.is_active == True,
    )
    for session in sessions:
        session.is_active = False

    db.commit()
    logger.info(f"User logged out: {current_user.username}")

    return {"message": "Logged out successfully"}


@router.post("/verify-mfa")
async def verify_mfa(
    mfa_data: VerifyMFARequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """
    Verify TOTP code for MFA.

    Args:
        mfa_data: TOTP code
        current_user: Current user
        db: Database session

    Returns:
        Verification result

    Raises:
        HTTPException: If MFA code invalid
    """
    if not current_user.mfa_enabled or not current_user.mfa_secret:
        logger.warning(f"MFA verification for user without MFA enabled: {current_user.id}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFA not enabled for this user",
        )

    if not AuthService.verify_totp(current_user.mfa_secret, mfa_data.code):
        logger.warning(f"Failed MFA verification: {current_user.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid MFA code",
        )

    logger.info(f"MFA verified for user: {current_user.username}")

    return {"verified": True, "message": "MFA code verified"}


@router.get("/me", response_model=CurrentUserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user),
) -> User:
    """
    Get current authenticated user information.

    Args:
        current_user: Current authenticated user

    Returns:
        Current user details
    """
    return current_user
