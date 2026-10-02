import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.logging import request_id_var, resolve_request_id, setup_logging

setup_logging(settings.log_level, settings.log_json)
logger = logging.getLogger("app.request")


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
    expose_headers=["X-Request-ID"],
)

# polled by load balancers / compose healthchecks; logging them buries real traffic
QUIET_PATHS = ("/health",)


@app.middleware("http")
async def request_logging(request: Request, call_next):
    request_id = resolve_request_id(request.headers.get("x-request-id"))
    token = request_id_var.set(request_id)
    start = time.perf_counter()
    status = 500
    try:
        response = await call_next(request)
        status = response.status_code
        response.headers["X-Request-ID"] = request_id
        return response
    except Exception:
        logger.exception("unhandled error on %s %s", request.method, request.url.path)
        raise
    finally:
        elapsed_ms = round((time.perf_counter() - start) * 1000, 1)
        if request.url.path not in QUIET_PATHS or status >= 400:
            level = (
                logging.ERROR if status >= 500
                else logging.WARNING if status >= 400
                else logging.INFO
            )
            # path only: query strings can carry search terms and redirect targets
            logger.log(
                level,
                "%s %s %s %.1fms",
                request.method,
                request.url.path,
                status,
                elapsed_ms,
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "status": status,
                    "duration_ms": elapsed_ms,
                    "client_ip": request.client.host if request.client else None,
                },
            )
        request_id_var.reset(token)

app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.get("/health", tags=["meta"])
async def health_check() -> dict[str, str]:
    return {"status": "ok"}
