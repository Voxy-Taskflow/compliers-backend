@'
"""FastAPI application entrypoint â€” F-03: API Gateway / BFF skeleton."""
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.exceptions import AppError
from app.middleware.auth import AuthMiddleware
from app.api.routes import narratives, documents, followups, review_queue, auth as auth_routes


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(
    title="Healthcare Communication Assistant API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(AuthMiddleware)


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.code, "message": exc.message},
    )


@app.exception_handler(Exception)
async def unhandled_error_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"error": "internal_error", "message": "Something went wrong. Staff notified."},
    )


@app.get("/health")
async def health():
    return {"status": "ok"}


app.include_router(auth_routes.router, prefix="/auth", tags=["auth"])
app.include_router(narratives.router, prefix="/narratives", tags=["narratives"])
app.include_router(documents.router, prefix="/documents", tags=["documents"])
app.include_router(followups.router, prefix="/followups", tags=["followups"])
app.include_router(review_queue.router, prefix="/review-queue", tags=["review-queue"])
'@ | Set-Content -Encoding UTF8 -Path "app\main.py"

@'
"""Custom exception types."""


class AppError(Exception):
    status_code: int = 400
    code: str = "app_error"

    def __init__(self, message: str, status_code: int | None = None, code: str | None = None):
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        if code is not None:
            self.code = code
        super().__init__(message)


class NotFoundError(AppError):
    status_code = 404
    code = "not_found"


class UnauthorizedError(AppError):
    status_code = 401
    code = "unauthorized"


class ForbiddenError(AppError):
    status_code = 403
    code = "forbidden"


class ValidationError(AppError):
    status_code = 422
    code = "validation_error"
'@ | Set-Content -Encoding UTF8 -Path "app\core\exceptions.py"

@'
"""Auth middleware."""
import jwt
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.core.config import settings

PUBLIC_PATHS = {"/health", "/auth/otp/request", "/auth/otp/verify", "/docs", "/openapi.json"}


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path in PUBLIC_PATHS:
            return await call_next(request)

        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return JSONResponse(status_code=401, content={"error": "unauthorized", "message": "Missing token."})

        token = auth_header.removeprefix("Bearer ").strip()
        try:
            payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
        except jwt.PyJWTError:
            return JSONResponse(status_code=401, content={"error": "unauthorized", "message": "Invalid or expired token."})

        request.state.actor_id = payload.get("sub")
        request.state.actor_type = payload.get("actor_type")
        request.state.role = payload.get("role")

        return await call_next(request)
'@ | Set-Content -Encoding UTF8 -Path "app\middleware\auth.py"

New-Item -ItemType Directory -Force -Path "app\api\routes" | Out-Null

foreach ($r in "narratives","documents","followups","review_queue","auth") {
@"
from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def placeholder():
    return {"detail": "$r router alive"}
"@ | Set-Content -Encoding UTF8 -Path "app\api\routes\$r.py"
}

New-Item -ItemType File -Force -Path "app\api\__init__.py","app\api\routes\__init__.py","app\middleware\__init__.py" | Out-Null

Write-Host "--- files created ---"
Get-ChildItem app\api\routes, app\middleware, app\core -Recurse -File
