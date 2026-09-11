from fastapi import FastAPI

app = FastAPI(
    title="Multilingual Healthcare Communication Assistant",
    version="0.1.0",
)


@app.get("/healthz")
def healthz() -> dict:
    """Liveness probe. No auth, no DB dependency - just proves the process is up."""
    return {"status": "ok"}


# Routers are mounted incrementally as each workstream (V, N, D, T, R, A, H) lands.
# e.g. from app.api.routes import voice; app.include_router(voice.router, prefix="/voice")
