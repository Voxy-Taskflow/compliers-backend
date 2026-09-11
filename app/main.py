"""FastAPI application entrypoint - F-03: API Gateway / BFF skeleton."""
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.exceptions import AppError
from app.middleware.auth import AuthMiddleware
from app.api.routes import narratives, documents, followups, review_queue, auth as auth_routes
from app.routers import narratives
from app.routers import summaries

settings = get_settings()


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
    allow_origins=settings.cors_origins,
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
app.include_router(narratives.router)
app.include_router(summaries.router)
