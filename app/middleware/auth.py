"""Development access middleware."""
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Authentication is intentionally disabled for local development.
        # Restore JWT validation before exposing this service beyond localhost.
        return await call_next(request)
