"""Auth middleware."""
import jwt
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.core.config import get_settings

settings = get_settings()

PUBLIC_PATHS = {"/health", "/auth/otp/request", "/auth/otp/verify", "/auth/dev-login", "/docs", "/openapi.json"}


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path in PUBLIC_PATHS:
            return await call_next(request)

        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return JSONResponse(status_code=401, content={"error": "unauthorized", "message": "Missing token."})

        token = auth_header.removeprefix("Bearer ").strip()
        try:
            payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        except jwt.PyJWTError:
            return JSONResponse(status_code=401, content={"error": "unauthorized", "message": "Invalid or expired token."})

        request.state.actor_id = payload.get("sub")
        request.state.actor_type = payload.get("actor_type")
        request.state.role = payload.get("role")

        return await call_next(request)
