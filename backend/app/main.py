from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(
    title=settings.app_name,
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

# JSON-only API: forbid MIME sniffing, framing and referrer leakage, and keep
# per-user responses (tokens, profiles, notifications) out of shared caches.
SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Cache-Control": "no-store",
}
API_CSP = "default-src 'none'; frame-ancestors 'none'"
# Swagger/ReDoc pages load their UI from a CDN, so they can't take the strict CSP
DOCS_PATHS = ("/docs", "/redoc", "/openapi.json")


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    for key, value in SECURITY_HEADERS.items():
        response.headers.setdefault(key, value)
    if not request.url.path.startswith(DOCS_PATHS):
        response.headers.setdefault("Content-Security-Policy", API_CSP)
    return response


app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.get("/health", tags=["meta"])
async def health_check() -> dict[str, str]:
    return {"status": "ok"}
