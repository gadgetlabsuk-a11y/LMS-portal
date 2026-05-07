"""
Authentication service for JWT token management and password handling.
Provides secure password hashing, token creation/verification, and TOTP support.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple
from passlib.context import CryptContext
from jose import JWTError, jwt
from pydantic import BaseModel
import asyncio
import functools
import uuid
import pyotp
import qrcode
from io import BytesIO
import base64
from config import settings
import logging

logger = logging.getLogger(__name__)

# Password hashing context
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12,
)


class TokenData(BaseModel):
    """JWT token payload data."""

    sub: str
    user_id: int
    exp: datetime
    role: str


class AuthService:
    """Service for authentication-related operations."""

    @staticmethod
    def hash_password(password: str) -> str:
        """
        Hash a password using bcrypt.

        Args:
            password: Plain text password

        Returns:
            Hashed password
        """
        return pwd_context.hash(password)

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """
        Verify a plain password against a hashed password.
        Synchronous version — use verify_password_async from async contexts.

        Args:
            plain_password: Plain text password
            hashed_password: Hashed password from database

        Returns:
            True if password matches, False otherwise
        """
        return pwd_context.verify(plain_password, hashed_password)

    @staticmethod
    async def verify_password_async(plain_password: str, hashed_password: str) -> bool:
        """
        Async-safe bcrypt verification.
        Runs the CPU-bound bcrypt work in the default thread-pool executor so it
        doesn't block the event loop while other requests are being served.
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            functools.partial(pwd_context.verify, plain_password, hashed_password),
        )

    @staticmethod
    async def hash_password_async(password: str) -> str:
        """Async-safe bcrypt hashing — offloads CPU work to a thread pool."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            functools.partial(pwd_context.hash, password),
        )

    @staticmethod
    def enforce_password_policy(password: str) -> Tuple[bool, Optional[str]]:
        """
        Enforce password policy requirements.

        Requirements:
        - Minimum 8 characters
        - At least one uppercase letter
        - At least one lowercase letter
        - At least one digit
        - At least one special character

        Args:
            password: Password to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if len(password) < 8:
            return False, "Password must be at least 8 characters long"

        if not any(c.isupper() for c in password):
            return False, "Password must contain at least one uppercase letter"

        if not any(c.islower() for c in password):
            return False, "Password must contain at least one lowercase letter"

        if not any(c.isdigit() for c in password):
            return False, "Password must contain at least one digit"

        special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"
        if not any(c in special_chars for c in password):
            return False, "Password must contain at least one special character"

        return True, None

    @staticmethod
    def create_access_token(
        user_id: int,
        username: str,
        role: str,
        expires_delta: Optional[timedelta] = None,
    ) -> str:
        """
        Create a JWT access token.

        Args:
            user_id: User ID
            username: Username
            role: User role
            expires_delta: Custom expiration time

        Returns:
            JWT token string
        """
        if expires_delta is None:
            expires_delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

        expire = datetime.now(timezone.utc) + expires_delta
        to_encode = {
            "sub": username,
            "user_id": user_id,
            "role": role,
            "exp": expire,
            "type": "access",
            # jti (JWT ID) guarantees uniqueness even when multiple tokens are
            # issued for the same user within the same second — preventing
            # UNIQUE constraint violations on the sessions.token column.
            "jti": str(uuid.uuid4()),
        }

        encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        return encoded_jwt

    @staticmethod
    def create_refresh_token(user_id: int, username: str) -> str:
        """
        Create a JWT refresh token.

        Args:
            user_id: User ID
            username: Username

        Returns:
            JWT refresh token string
        """
        expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        to_encode = {
            "sub": username,
            "user_id": user_id,
            "exp": expire,
            "type": "refresh",
            "jti": str(uuid.uuid4()),
        }

        encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        return encoded_jwt

    @staticmethod
    def verify_token(token: str) -> Optional[dict]:
        """
        Verify and decode a JWT token.

        Args:
            token: JWT token string

        Returns:
            Token payload dict if valid, None otherwise
        """
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            username: str = payload.get("sub")
            user_id: int = payload.get("user_id")
            token_type: str = payload.get("type", "access")

            if username is None or user_id is None:
                return None

            return {
                "username": username,
                "user_id": user_id,
                "role": payload.get("role"),
                "type": token_type,
            }
        except JWTError as e:
            logger.warning(f"Token verification failed: {str(e)}")
            return None

    @staticmethod
    def generate_totp_secret() -> str:
        """
        Generate a new TOTP secret for MFA.

        Returns:
            Base32 encoded secret
        """
        return pyotp.random_base32()

    @staticmethod
    def get_totp_provisioning_uri(secret: str, username: str, issuer: str) -> str:
        """
        Get the provisioning URI for TOTP QR code.

        Args:
            secret: TOTP secret
            username: Username for display
            issuer: Issuer name

        Returns:
            Provisioning URI
        """
        totp = pyotp.TOTP(secret)
        return totp.provisioning_uri(name=username, issuer_name=issuer)

    @staticmethod
    def generate_totp_qr_code(provisioning_uri: str) -> str:
        """
        Generate a QR code for TOTP provisioning.

        Args:
            provisioning_uri: Provisioning URI from get_totp_provisioning_uri

        Returns:
            Base64 encoded QR code image
        """
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(provisioning_uri)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)

        return base64.b64encode(buffer.getvalue()).decode()

    @staticmethod
    def verify_totp(secret: str, code: str, window: int = 1) -> bool:
        """
        Verify a TOTP code.

        Args:
            secret: TOTP secret
            code: 6-digit TOTP code
            window: Number of windows to check (allows for clock skew)

        Returns:
            True if valid, False otherwise
        """
        try:
            totp = pyotp.TOTP(secret)
            return totp.verify(code, valid_window=window)
        except Exception as e:
            logger.warning(f"TOTP verification failed: {str(e)}")
            return False

    @staticmethod
    def get_account_lockout_duration() -> timedelta:
        """
        Get the account lockout duration.

        Returns:
            Timedelta for lockout duration
        """
        return timedelta(minutes=settings.LOCKOUT_DURATION_MINUTES)

    @staticmethod
    def is_account_locked(locked_until: Optional[datetime]) -> bool:
        """
        Check if an account is currently locked.

        Args:
            locked_until: DateTime until which account is locked

        Returns:
            True if locked, False otherwise
        """
        if locked_until is None:
            return False

        # SQLite stores DateTime without timezone info; treat naive datetimes as UTC
        # so the comparison doesn't raise TypeError.
        if locked_until.tzinfo is None:
            locked_until = locked_until.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) < locked_until
