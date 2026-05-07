"""
Authentication middleware and dependencies.
Provides JWT extraction, role-based access control, and rate limiting.
"""

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from datetime import datetime, timezone
import logging
from typing import Optional, Callable
from functools import wraps
from sqlalchemy.orm import Session
from database import get_db
from models import User, UserRole
from services.auth_service import AuthService

logger = logging.getLogger(__name__)

security = HTTPBearer()

# Rate limiting state (in production, use Redis)
rate_limit_store = {}


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    """
    Dependency to get the current authenticated user from JWT token.

    Args:
        credentials: HTTP Bearer credentials
        db: Database session

    Returns:
        Current user object

    Raises:
        HTTPException: If token is invalid or user not found
    """
    token = credentials.credentials

    # Verify token
    token_data = AuthService.verify_token(token)
    if token_data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Get user from database
    user = db.query(User).filter(User.id == token_data["user_id"]).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User is inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Dependency to ensure current user is active.

    Args:
        current_user: Current user from get_current_user

    Returns:
        Active user object
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is inactive",
        )
    return current_user


def require_role(*allowed_roles: UserRole):
    """
    Dependency factory for role-based access control.

    Args:
        allowed_roles: Tuple of allowed UserRole values

    Returns:
        Dependency function
    """

    async def role_checker(current_user: User = Depends(get_current_active_user)) -> User:
        """Check if user has required role."""
        if current_user.role not in allowed_roles:
            logger.warning(
                f"Access denied for user {current_user.id} with role {current_user.role}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required role: {[r.value for r in allowed_roles]}",
            )
        return current_user

    return role_checker


def require_admin(current_user: User = Depends(get_current_active_user)) -> User:
    """
    Dependency to require admin role.

    Args:
        current_user: Current user

    Returns:
        User if admin, raises exception otherwise
    """
    if current_user.role != UserRole.ADMIN:
        logger.warning(f"Admin access denied for user {current_user.id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user


def require_creator(current_user: User = Depends(get_current_active_user)) -> User:
    """
    Dependency to require creator or admin role.

    Args:
        current_user: Current user

    Returns:
        User if creator or admin, raises exception otherwise
    """
    if current_user.role not in (UserRole.CREATOR, UserRole.ADMIN):
        logger.warning(f"Creator access denied for user {current_user.id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Creator access required",
        )
    return current_user


async def get_client_ip(request: Request) -> str:
    """
    Extract client IP address from request.

    Args:
        request: FastAPI request object

    Returns:
        Client IP address
    """
    # Check for X-Forwarded-For header (proxy)
    if "x-forwarded-for" in request.headers:
        return request.headers["x-forwarded-for"].split(",")[0].strip()

    # Fall back to direct connection
    return request.client.host if request.client else "0.0.0.0"


async def get_user_agent(request: Request) -> Optional[str]:
    """
    Extract user agent from request.

    Args:
        request: FastAPI request object

    Returns:
        User agent string or None
    """
    return request.headers.get("user-agent")


async def rate_limit(
    request: Request,
    max_requests: int = 100,
    window_seconds: int = 60,
) -> bool:
    """
    Simple in-memory rate limiting.
    In production, use Redis for distributed rate limiting.

    Args:
        request: FastAPI request object
        max_requests: Maximum requests allowed in window
        window_seconds: Time window in seconds

    Returns:
        True if within limit, False if rate limited

    Raises:
        HTTPException: If rate limit exceeded
    """
    client_ip = await get_client_ip(request)
    now = datetime.now(timezone.utc)

    # Initialize or get client's request history
    if client_ip not in rate_limit_store:
        rate_limit_store[client_ip] = []

    # Remove requests outside the window
    rate_limit_store[client_ip] = [
        req_time
        for req_time in rate_limit_store[client_ip]
        if (now - req_time).total_seconds() < window_seconds
    ]

    # Check if limit exceeded
    if len(rate_limit_store[client_ip]) >= max_requests:
        logger.warning(f"Rate limit exceeded for IP {client_ip}")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests",
        )

    # Record this request
    rate_limit_store[client_ip].append(now)
    return True


async def optional_user(
    request: Request,
    db: Session = Depends(get_db),
) -> Optional[User]:
    """
    Optional dependency to get current user if authenticated.
    Does not raise exception if not authenticated.

    Args:
        request: FastAPI request object
        db: Database session

    Returns:
        User object if authenticated, None otherwise
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return None

    token = auth_header.split(" ")[1]
    token_data = AuthService.verify_token(token)

    if token_data is None:
        return None

    user = db.query(User).filter(User.id == token_data["user_id"]).first()
    return user if user and user.is_active else None
