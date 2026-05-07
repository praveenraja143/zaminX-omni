"""
api/routers/auth.py
===================
POST /api/auth/register  — Register with phone OTP (Firebase)
POST /api/auth/login     — Get JWT from Firebase token
GET  /api/auth/me        — Current user profile
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from api.auth import (
    create_access_token, require_user, verify_firebase_token
)
from api.schemas import TokenResponse, UserRegisterRequest, UserResponse
from src.database import get_db
from src.models import User

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register New User",
)
async def register(
    request: UserRegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Register using Firebase phone OTP token.
    Creates user account and returns JWT access token.
    """
    # Verify Firebase token
    firebase_claims = await verify_firebase_token(request.firebase_token or "")
    firebase_uid = firebase_claims.get("uid", "")

    # Check if already registered
    stmt = select(User).where(User.phone == request.phone)
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()

    if existing:
        # Return token for existing user
        token = create_access_token(str(existing.user_id), existing.subscription_tier)
        return TokenResponse(
            access_token=token,
            expires_in_seconds=86400,
            user=UserResponse.model_validate(existing),
        )

    # Create new user
    user = User(
        phone=request.phone,
        name=request.name,
        state=request.state,
        language=request.language,
        firebase_uid=firebase_uid,
        subscription_tier="free",
        searches_this_month=0,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    token = create_access_token(str(user.user_id), user.subscription_tier)
    logger.info("New user registered: phone=%s user_id=%s", request.phone, user.user_id)

    return TokenResponse(
        access_token=token,
        expires_in_seconds=86400,
        user=UserResponse.model_validate(user),
    )


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login with Firebase Token",
)
async def login(firebase_token: str, db: AsyncSession = Depends(get_db)):
    """Exchange a Firebase ID token for a Zamin X JWT."""
    claims = await verify_firebase_token(firebase_token)
    phone = claims.get("phone_number", "")

    stmt = select(User).where(User.phone == phone, User.is_active == True)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found. Please register first.")

    token = create_access_token(str(user.user_id), user.subscription_tier)
    return TokenResponse(
        access_token=token,
        expires_in_seconds=86400,
        user=UserResponse.model_validate(user),
    )


@router.get("/me", response_model=UserResponse, summary="Current User Profile")
async def get_me(current_user: User = Depends(require_user)):
    return UserResponse.model_validate(current_user)
