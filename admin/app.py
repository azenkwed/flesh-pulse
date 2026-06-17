"""Admin dashboard — runs separately on port 8081."""
import base64
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from backend.database.db import init_db
from admin.routes import router


class BasicAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        password = os.getenv("ADMIN_PASSWORD")
        if not password:
            return Response(
                status_code=401,
                headers={"WWW-Authenticate": 'Basic realm="Sex Health News Admin"'},
                content="ADMIN_PASSWORD is not configured.",
            )
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Basic "):
            try:
                decoded = base64.b64decode(auth[6:]).decode()
                _, pwd = decoded.split(":", 1)
                if pwd == password:
                    return await call_next(request)
            except Exception:
                pass
        return Response(
            status_code=401,
            headers={"WWW-Authenticate": 'Basic realm="Sex Health News Admin"'},
        )


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(title="Sex Health News Admin", lifespan=lifespan)
app.add_middleware(BasicAuthMiddleware)
app.mount("/static", StaticFiles(directory="admin/static"), name="static")
app.include_router(router)
