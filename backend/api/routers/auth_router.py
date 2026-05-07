"""
api/routers/auth_router.py
===========================
JWT authentication for Zamin X.
Simple phone + password login (OTP simulation for dev).
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.config import settings
from src.database import get_db
from src.models import User

logger = logging.getLogger(__name__)
router = APIRouter()


class RegisterRequest(BaseModel):
    phone: str = Field(..., min_length=10, max_length=15)
    name: str = Field(default="")
    password: str = Field(..., min_length=4)
    language: str = Field(default="en")


class LoginRequest(BaseModel):
    phone: str = Field(..., min_length=10, max_length=15)
    password: str = Field(..., min_length=4)


class AuthResponse(BaseModel):
    success: bool
    token: Optional[str] = None
    user: Optional[dict] = None
    message: str = ""


def _create_token(user_id: str) -> str:
    """Create a simple JWT token."""
    import hashlib
    import base64
    import json
    payload = {
        "user_id": user_id,
        "exp": (datetime.utcnow() + timedelta(minutes=settings.jwt_expire_minutes)).isoformat(),
    }
    raw = json.dumps(payload) + settings.secret_key
    token = base64.urlsafe_b64encode(
        hashlib.sha256(raw.encode()).digest()
    ).decode()[:32]
    # Simple token = base64(payload) + "." + signature
    payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()
    return f"{payload_b64}.{token}"


def _hash_password(password: str) -> str:
    import hashlib
    return hashlib.sha256((password + settings.secret_key).encode()).hexdigest()


@router.post("/register", response_model=AuthResponse)
async def register(req: RegisterRequest, db: AsyncSession = Depends(get_db)):
    # Check if phone already exists
    result = await db.execute(select(User).where(User.phone == req.phone))
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="Phone number already registered")

    user = User(
        phone=req.phone,
        name=req.name,
        password_hash=_hash_password(req.password),
        language=req.language,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    token = _create_token(user.user_id)

    return AuthResponse(
        success=True,
        token=token,
        user={
            "user_id": user.user_id,
            "phone": user.phone,
            "name": user.name,
            "language": user.language,
        },
        message="Registration successful",
    )


@router.post("/login", response_model=AuthResponse)
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.phone == req.phone))
    user = result.scalar_one_or_none()

    if not user or user.password_hash != _hash_password(req.password):
        raise HTTPException(status_code=401, detail="Invalid phone or password")

    token = _create_token(user.user_id)

    return AuthResponse(
        success=True,
        token=token,
        user={
            "user_id": user.user_id,
            "phone": user.phone,
            "name": user.name,
            "language": user.language,
        },
        message="Login successful",
    )
