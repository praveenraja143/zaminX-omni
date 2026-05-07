"""
api/auth.py
===========
JWT-based authentication for Zamin X API.

- Phone OTP login via Firebase Authentication
- JWT access tokens (HS256, 24h expiry)
- Role-based access: free | basic | premium | b2b
- FastAPI dependency injection for protected routes
"""

import logging
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from fastapi import Depends, Header, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from api.schemas import TokenResponse, UserResponse
from src.config import settings
from src.database import get_db
from src.models import User

logger = logging.getLogger(__name__)

# ── Crypto ────────────────────────────────────────────────────────────────────
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer(auto_error=False)

# ── JWT helpers ───────────────────────────────────────────────────────────────
def create_access_token(user_id: str, subscription_tier: str) -> str:
    """Create a signed JWT access token."""
    payload = {
        "sub": str(user_id),
        "tier": subscription_tier,
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(minutes=settings.jwt_expire_minutes),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict:
    """Decode and validate JWT. Raises HTTPException on failure."""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
        return payload
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired token: {e}",
            headers={"WWW-Authenticate": "Bearer"},
        )


# ── FastAPI Dependencies ───────────────────────────────────────────────────────
async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """
    Optional auth dependency — returns User if token is valid, None if anonymous.
    Use for endpoints that work for both authenticated and anonymous users.
    """
    if not credentials:
        return None

    payload = decode_access_token(credentials.credentials)
    user_id = payload.get("sub")
    if not user_id:
        return None

    stmt = select(User).where(User.user_id == UUID(user_id), User.is_active == True)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    return user


async def require_user(
    credentials: HTTPAuthorizationCredentials = Security(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Required auth dependency — raises 401 if not authenticated."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_access_token(credentials.credentials)
    user_id = payload.get("sub")

    stmt = select(User).where(User.user_id == UUID(user_id), User.is_active == True)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


async def require_b2b(
    user: User = Depends(require_user),
) -> User:
    """Require B2B subscription tier for bulk API access."""
    if user.subscription_tier != "b2b":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="B2B API access requires a B2B subscription. Contact sales@zaminx.in",
        )
    return user


def check_search_quota(user: Optional[User]) -> None:
    """
    Enforce freemium search quota.
    Free users: 3 searches/month
    Basic: 30/month | Premium: unlimited | B2B: unlimited
    """
    if user is None:
        return  # anonymous users can do 1 search (handled at IP level by rate limiter)

    limits = {"free": 3, "basic": 30, "premium": 99999, "b2b": 99999}
    limit = limits.get(user.subscription_tier, 3)

    if user.searches_this_month >= limit:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=(
                f"Monthly search limit reached ({limit} searches for {user.subscription_tier} plan). "
                "Upgrade your plan at zaminx.in/upgrade"
            ),
        )


# ── Firebase Token Verification (optional — used in production) ────────────────
async def verify_firebase_token(firebase_id_token: str) -> dict:
    """
    Verify Firebase ID token and return decoded claims.
    Used during registration / login to validate phone OTP.
    Falls back to mock in development.
    """
    if settings.environment == "development":
        # Mock verification for development
        return {
            "uid": f"mock_uid_{firebase_id_token[:8]}",
            "phone_number": "+919876543210",
        }

    try:
        import firebase_admin
        from firebase_admin import auth as firebase_auth

        decoded = firebase_auth.verify_id_token(firebase_id_token)
        logger.info("Firebase token verified for uid=%s", decoded.get("uid"))
        return decoded
    except Exception as e:
        logger.error("Firebase token verification failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Firebase authentication token",
        )
