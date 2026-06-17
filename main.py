"""Sex Health News — entry point."""
import logging
import os
import sys
from contextlib import asynccontextmanager

from dotenv import load_dotenv

# Force UTF-8 output on Windows (cp1252 default can't handle emoji in log lines)
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if sys.stderr.encoding and sys.stderr.encoding.lower() != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.exceptions import HTTPException as StarletteHTTPException

load_dotenv()

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    force=True,
)
logger = logging.getLogger(__name__)


def _is_scheduler_instance() -> bool:
    """Only run the scheduler on the primary region machine to avoid duplicate jobs
    when multiple Fly.io instances are deployed. Locally always runs."""
    primary = os.getenv("PRIMARY_REGION", "")
    current = os.getenv("FLY_REGION", "")
    if not primary:
        return True  # no region guard configured — run locally or on all instances
    return current == primary


@asynccontextmanager
async def lifespan(app: FastAPI):
    from backend.database.db import init_db
    from backend.scheduler import create_scheduler

    await init_db()
    if _is_scheduler_instance():
        scheduler = create_scheduler()
        scheduler.start()
        logger.info("Scheduler started")
    else:
        scheduler = None
        logger.info(f"Scheduler skipped (region={os.getenv('FLY_REGION')} is not primary={os.getenv('PRIMARY_REGION')})")
    yield
    if scheduler:
        scheduler.shutdown()
        logger.info("Scheduler stopped")


app = FastAPI(
    title="Sex Health News",
    description="Independent reporting on sexual health, rights, and wellness for all",
    lifespan=lifespan,
)

app.mount("/static", StaticFiles(directory="frontend/static"), name="static")

from starlette.middleware.sessions import SessionMiddleware
app.add_middleware(SessionMiddleware, secret_key=os.getenv("JWT_SECRET_KEY", "dev-secret"))

from backend.routes import router, CATEGORIES
from backend.auth.routes import router as auth_router
from backend.payments.routes import router as payments_router

app.include_router(router)
app.include_router(auth_router)
app.include_router(payments_router)

_templates = Jinja2Templates(directory="frontend/templates")

_ERROR_TITLES = {
    400: "Bad request",
    403: "Access denied",
    404: "Page not found",
    405: "Method not allowed",
    422: "Invalid request",
    429: "Too many requests",
    500: "Something went wrong",
}

_ERROR_DETAILS = {
    400: "The request could not be understood by the server.",
    403: "You don't have permission to access this page.",
    404: "The page you're looking for doesn't exist or has been removed.",
    405: "This action isn't allowed here.",
    422: "The request contained invalid data.",
    429: "You're making too many requests. Please slow down.",
    500: "An unexpected error occurred on our end. Please try again shortly.",
}


async def _get_user(request: Request):
    from backend.auth.dependencies import get_optional_user
    from backend.database.db import get_db
    db_gen = get_db()
    db = await db_gen.__anext__()
    try:
        return await get_optional_user(request, db)
    except Exception:
        return None
    finally:
        try:
            await db_gen.aclose()
        except Exception:
            pass


def _error_response(request: Request, status_code: int, current_user=None):
    from datetime import datetime, timezone
    return _templates.TemplateResponse("error.html", {
        "request": request,
        "categories": CATEGORIES,
        "current_user": current_user,
        "last_updated": "",
        "now": datetime.now(timezone.utc),
        "status_code": status_code,
        "title": _ERROR_TITLES.get(status_code, "Error"),
        "detail": _ERROR_DETAILS.get(status_code, "An error occurred."),
    }, status_code=status_code)


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    current_user = await _get_user(request)
    return _error_response(request, exc.status_code, current_user)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception for %s %s", request.method, request.url)
    current_user = await _get_user(request)
    return _error_response(request, 500, current_user)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=os.getenv("APP_HOST", "0.0.0.0"),
        port=int(os.getenv("APP_PORT", "8000")),
        reload=os.getenv("DEBUG", "false").lower() == "true",
    )
