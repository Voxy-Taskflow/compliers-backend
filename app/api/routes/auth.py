"""Auth routes."""
from datetime import datetime, timedelta

import jwt
from fastapi import APIRouter, HTTPException

from app.core.config import get_settings

settings = get_settings()

router = APIRouter()


@router.get("/")
async def placeholder():
    return {"detail": "auth router alive"}


@router.post("/dev-login")
async def dev_login():
    """DEV/DEMO ONLY. Mints a fake staff token without OTP.
    Disabled automatically when settings.debug is False.
    Real F-04 (OTP + role-based auth) still owed before production —
    this route is a shortcut for testing/demo, not a replacement.
    """
    if not settings.debug:
        raise HTTPException(404, "Not found")

    payload = {
        "sub": "demo-staff-id",
        "actor_type": "staff",
        "role": "admin",
        "exp": datetime.utcnow() + timedelta(hours=24),
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return {"access_token": token, "token_type": "bearer"}