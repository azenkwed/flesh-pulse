"""Authentication and profile routes."""
import json
import logging
import os
import secrets
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from urllib.parse import parse_qsl, quote_plus, urlencode, urlsplit, urlunsplit

from authlib.integrations.starlette_client import OAuthError
from fastapi import APIRouter, Depends, Form, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.dependencies import get_optional_user
from backend.auth.oauth import ENABLED_PROVIDERS, find_or_create_oauth_user, oauth
from backend.auth.utils import (
    _mask,
    create_access_token,
    create_email_token,
    hash_password,
    verify_email_token,
    verify_password,
)
from backend.database.db import get_db
from backend.database.models import Article, SavedArticle, User
from backend.notifications.email import send_password_reset_email, send_verification_email

# Import shared list — routes.py does not import from this file, so no circular dep
from backend.routes import CATEGORIES

templates = Jinja2Templates(directory="frontend/templates")
templates.env.globals["now"] = lambda: datetime.now(timezone.utc)
router = APIRouter()

APP_URL = os.getenv("APP_URL", "http://localhost:8000")
_COOKIE_SECURE = os.getenv("APP_URL", "").startswith("https://")
_SSL_VERIFY = sys.platform != "win32"
_VALID_FREQUENCIES = frozenset({"daily", "weekly", "never"})
_VALID_MSGS = frozenset({
    "verify-email", "reset-expired", "password-reset", "oauth-failed",
    "provider-unavailable", "reset-sent", "saved", "welcome", "password-changed",
})


def _safe_msg(msg: str) -> str:
    return msg if msg in _VALID_MSGS else ""

_rl_store: dict[str, list[float]] = defaultdict(list)
_RL_WINDOW = 60
_RL_MAX = 10

logger = logging.getLogger(__name__)


def _rate_limited(key: str) -> bool:
    """Returns True if the key has exceeded the rate limit."""
    now = time.time()
    _rl_store[key] = [t for t in _rl_store[key] if now - t < _RL_WINDOW]
    if len(_rl_store[key]) >= _RL_MAX:
        return True
    _rl_store[key].append(now)
    return False


def _redact_url(url: str | None) -> str:
    if not url:
        return "<empty>"

    sensitive_keys = {"client_id", "client_secret", "code", "code_challenge", "state"}
    parts = urlsplit(url)
    query = []
    for key, value in parse_qsl(parts.query, keep_blank_values=True):
        query.append((key, _mask(value) if key in sensitive_keys else value))
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


def _safe_query_keys(request: Request) -> list[str]:
    return sorted(request.query_params.keys())


def _safe_next_url(next_url: str) -> str:
    if next_url.startswith("/") and not next_url.startswith("//"):
        return next_url
    return ""


def _store_next(request: Request, next_url: str) -> None:
    safe_next = _safe_next_url(next_url)
    if safe_next:
        request.session["_post_auth_next"] = safe_next


def _consume_next(request: Request) -> str:
    next_url = request.session.pop("_post_auth_next", "")
    return _safe_next_url(next_url)


def _ctx(request: Request, current_user=None, **kwargs) -> dict:
    return {
        "request": request,
        "categories": CATEGORIES,
        "last_updated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "current_user": current_user,
        "oauth_providers": ENABLED_PROVIDERS,
        **kwargs,
    }


def _article_summary(article: Article) -> dict:
    tags = article.tags if isinstance(article.tags, list) else []
    return {
        "id": article.id,
        "title": article.title,
        "url": article.url,
        "source_name": article.source_name,
        "published_at": article.published_at,
        "category": article.category,
        "tags_list": tags,
    }


# ─── Register ────────────────────────────────────────────────────────────────

@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request, next: str = ""):
    return templates.TemplateResponse("auth/register.html", _ctx(request, next=_safe_next_url(next)))


@router.post("/register")
async def register(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
    display_name: str = Form(""),
    next: str = Form(""),
    db: AsyncSession = Depends(get_db),
):
    email = email.strip().lower()
    display_name = display_name.strip()

    if _rate_limited(f"register:{request.client.host if request.client else 'unknown'}"):
        return templates.TemplateResponse(
            "auth/register.html",
            _ctx(request, error="Too many attempts. Please try again in a minute.", email=email, display_name=display_name, next=_safe_next_url(next)),
        )

    if len(password) < 8:
        return templates.TemplateResponse(
            "auth/register.html",
            _ctx(request, error="Password must be at least 8 characters.", email=email, display_name=display_name, next=_safe_next_url(next)),
        )
    if password != confirm_password:
        return templates.TemplateResponse(
            "auth/register.html",
            _ctx(request, error="Passwords do not match.", email=email, display_name=display_name, next=_safe_next_url(next)),
        )

    existing = await db.execute(select(User).where(User.email == email))
    if existing.scalar_one_or_none():
        return templates.TemplateResponse(
            "auth/register.html",
            _ctx(request, error="An account with this email already exists.", email=email, display_name=display_name, next=_safe_next_url(next)),
        )

    user = User(
        email=email,
        password_hash=hash_password(password),
        display_name=display_name or None,
        email_verified=False,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    token = create_email_token({"user_id": user.id, "action": "verify"})
    send_verification_email(email, token)

    login_url = "/login?msg=verify-email"
    safe_next = _safe_next_url(next)
    if safe_next:
        login_url += f"&next={quote_plus(safe_next)}"
    return RedirectResponse(url=login_url, status_code=303)


# ─── Login ───────────────────────────────────────────────────────────────────

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, msg: str = "", next: str = ""):
    return templates.TemplateResponse("auth/login.html", _ctx(request, msg=_safe_msg(msg), next=_safe_next_url(next)))


@router.post("/login")
async def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    next: str = Form(""),
    db: AsyncSession = Depends(get_db),
):
    email = email.strip().lower()

    if _rate_limited(f"login:{request.client.host if request.client else 'unknown'}"):
        return templates.TemplateResponse(
            "auth/login.html",
            _ctx(request, error="Too many attempts. Please try again in a minute.", email=email, next=_safe_next_url(next)),
        )

    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if not user:
        return templates.TemplateResponse(
            "auth/login.html",
            _ctx(request, error="Invalid email or password.", email=email, next=_safe_next_url(next)),
        )

    if not user.password_hash:
        return templates.TemplateResponse(
            "auth/login.html",
            _ctx(request, error="This account uses social sign-in. Use the Google, LinkedIn, or Microsoft button below.", email=email, next=_safe_next_url(next)),
        )

    if not verify_password(password, user.password_hash):
        return templates.TemplateResponse(
            "auth/login.html",
            _ctx(request, error="Invalid email or password.", email=email, next=_safe_next_url(next)),
        )

    if not user.email_verified:
        return templates.TemplateResponse(
            "auth/login.html",
            _ctx(request, error="Please verify your email before signing in.", email=email, next=_safe_next_url(next)),
        )

    user.last_login = datetime.now(timezone.utc)
    await db.commit()

    token = create_access_token(user.id)
    redirect_url = _safe_next_url(next) or "/profile?msg=welcome"
    response = RedirectResponse(url=redirect_url, status_code=303)
    response.set_cookie(
        "access_token",
        token,
        httponly=True,
        samesite="lax",
        max_age=60 * 60 * 24 * 30,
        secure=_COOKIE_SECURE,
    )
    return response


# ─── Logout ──────────────────────────────────────────────────────────────────

@router.post("/logout")
async def logout():
    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie("access_token")
    return response


# ─── Email verification ───────────────────────────────────────────────────────

@router.get("/auth/verify/{token}", response_class=HTMLResponse)
async def verify_email(request: Request, token: str, db: AsyncSession = Depends(get_db)):
    data = verify_email_token(token, max_age=86400)
    if not data or data.get("action") != "verify":
        return templates.TemplateResponse(
            "auth/verify_email.html",
            _ctx(request, success=False, msg="This verification link is invalid or has expired."),
        )

    result = await db.execute(select(User).where(User.id == data["user_id"]))
    user = result.scalar_one_or_none()
    if not user:
        return templates.TemplateResponse(
            "auth/verify_email.html",
            _ctx(request, success=False, msg="Account not found."),
        )

    user.email_verified = True
    await db.commit()

    return RedirectResponse(url="/login?msg=email-verified", status_code=303)


# ─── Forgot / reset password ──────────────────────────────────────────────────

@router.get("/auth/forgot-password", response_class=HTMLResponse)
async def forgot_password_page(request: Request, msg: str = ""):
    return templates.TemplateResponse("auth/forgot_password.html", _ctx(request, msg=_safe_msg(msg)))


@router.post("/auth/forgot-password")
async def forgot_password(
    request: Request,
    email: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    email = email.strip().lower()

    if _rate_limited(f"forgot:{request.client.host if request.client else 'unknown'}"):
        return RedirectResponse(url="/auth/forgot-password?msg=reset-sent", status_code=303)

    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if user and user.email_verified:
        version = user.password_reset_token_version or 0
        token = create_email_token({"user_id": user.id, "action": "reset", "version": version})
        send_password_reset_email(email, token)

    # Always redirect to prevent email enumeration
    return RedirectResponse(url="/auth/forgot-password?msg=reset-sent", status_code=303)


@router.get("/auth/reset-password/{token}", response_class=HTMLResponse)
async def reset_password_page(request: Request, token: str, db: AsyncSession = Depends(get_db)):
    data = verify_email_token(token, max_age=3600)
    valid = False
    if data and data.get("action") == "reset":
        result = await db.execute(select(User).where(User.id == data["user_id"]))
        user = result.scalar_one_or_none()
        if user and (user.password_reset_token_version or 0) == data.get("version", 0):
            valid = True
    return templates.TemplateResponse(
        "auth/reset_password.html",
        _ctx(request, valid=valid, token=token),
    )


@router.post("/auth/reset-password/{token}")
async def reset_password(
    request: Request,
    token: str,
    password: str = Form(...),
    confirm_password: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    data = verify_email_token(token, max_age=3600)
    if not data or data.get("action") != "reset":
        return RedirectResponse(url="/login?msg=reset-expired", status_code=303)

    if len(password) < 8:
        return templates.TemplateResponse(
            "auth/reset_password.html",
            _ctx(request, valid=True, token=token, error="Password must be at least 8 characters."),
        )
    if password != confirm_password:
        return templates.TemplateResponse(
            "auth/reset_password.html",
            _ctx(request, valid=True, token=token, error="Passwords do not match."),
        )

    result = await db.execute(select(User).where(User.id == data["user_id"]))
    user = result.scalar_one_or_none()
    if not user or (user.password_reset_token_version or 0) != data.get("version", 0):
        return RedirectResponse(url="/login?msg=reset-expired", status_code=303)

    user.password_hash = hash_password(password)
    user.password_reset_token_version = (user.password_reset_token_version or 0) + 1
    await db.commit()
    return RedirectResponse(url="/login?msg=password-reset", status_code=303)


# ─── Profile ─────────────────────────────────────────────────────────────────

@router.get("/profile", response_class=HTMLResponse)
async def profile_page(request: Request, db: AsyncSession = Depends(get_db), msg: str = ""):
    current_user = await get_optional_user(request, db)
    if not current_user:
        return RedirectResponse(url="/login", status_code=303)

    try:
        user_categories = json.loads(current_user.categories or "[]")
    except (json.JSONDecodeError, TypeError):
        user_categories = []

    count_q = await db.execute(
        select(func.count()).select_from(SavedArticle).where(SavedArticle.user_id == current_user.id)
    )
    saved_count = count_q.scalar_one()

    return templates.TemplateResponse(
        "profile.html",
        _ctx(
            request,
            current_user=current_user,
            user_categories=user_categories,
            msg=_safe_msg(msg),
            saved_count=saved_count,
        ),
    )


@router.get("/saved", response_class=HTMLResponse)
async def saved_articles_page(
    request: Request,
    page: int = Query(1, ge=1),
    db: AsyncSession = Depends(get_db),
):
    current_user = await get_optional_user(request, db)
    if not current_user:
        return RedirectResponse(url="/login?next=/saved", status_code=303)

    per_page = 20
    offset = (page - 1) * per_page

    total_q = await db.execute(
        select(func.count()).select_from(SavedArticle).where(SavedArticle.user_id == current_user.id)
    )
    total = total_q.scalar_one()

    saved_q = await db.execute(
        select(Article, SavedArticle.created_at)
        .join(SavedArticle, SavedArticle.article_id == Article.id)
        .where(SavedArticle.user_id == current_user.id)
        .order_by(SavedArticle.created_at.desc())
        .offset(offset)
        .limit(per_page)
    )
    saved_articles = []
    for article, saved_at in saved_q.fetchall():
        item = _article_summary(article)
        item["saved_at"] = saved_at
        saved_articles.append(item)

    return templates.TemplateResponse(
        "saved.html",
        _ctx(
            request,
            current_user=current_user,
            saved_articles=saved_articles,
            page=page,
            total=total,
            per_page=per_page,
            total_pages=max(1, -(-total // per_page)),
        ),
    )


@router.post("/profile")
async def update_profile(
    request: Request,
    db: AsyncSession = Depends(get_db),
    display_name: str = Form(""),
    newsletter_frequency: str = Form("weekly"),
):
    current_user = await get_optional_user(request, db)
    if not current_user:
        return RedirectResponse(url="/login", status_code=303)

    form_data = await request.form()
    selected = form_data.getlist("categories")
    valid_categories = [c for c in selected if c in CATEGORIES]

    if newsletter_frequency not in _VALID_FREQUENCIES:
        newsletter_frequency = "weekly"
    current_user.display_name = display_name.strip() or None
    current_user.newsletter_frequency = newsletter_frequency
    current_user.categories = json.dumps(valid_categories)
    await db.commit()

    return RedirectResponse(url="/profile?msg=saved", status_code=303)


@router.post("/profile/change-password")
async def change_password(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_password: str = Form(...),
    new_password: str = Form(...),
    confirm_new_password: str = Form(...),
):
    current_user = await get_optional_user(request, db)
    if not current_user:
        return RedirectResponse(url="/login", status_code=303)

    try:
        user_categories = json.loads(current_user.categories or "[]")
    except (json.JSONDecodeError, TypeError):
        user_categories = []

    if not verify_password(current_password, current_user.password_hash):
        return templates.TemplateResponse(
            "profile.html",
            _ctx(request, current_user=current_user, user_categories=user_categories, pw_error="Current password is incorrect."),
        )
    if len(new_password) < 8:
        return templates.TemplateResponse(
            "profile.html",
            _ctx(request, current_user=current_user, user_categories=user_categories, pw_error="New password must be at least 8 characters."),
        )
    if new_password != confirm_new_password:
        return templates.TemplateResponse(
            "profile.html",
            _ctx(request, current_user=current_user, user_categories=user_categories, pw_error="New passwords do not match."),
        )

    current_user.password_hash = hash_password(new_password)
    await db.commit()
    return RedirectResponse(url="/profile?msg=password-changed", status_code=303)


# ─── OAuth social login ───────────────────────────────────────────────────────

@router.get("/auth/{provider}/login")
async def oauth_login(request: Request, provider: str, next: str = ""):
    if provider not in ENABLED_PROVIDERS:
        logger.warning(
            "OAuth login requested for unavailable provider=%s enabled=%s",
            provider,
            sorted(ENABLED_PROVIDERS),
        )
        return RedirectResponse(url="/login?msg=provider-unavailable", status_code=303)
    _store_next(request, next)
    redirect_uri = f"{APP_URL}/auth/{provider}/callback"
    logger.info(
        "OAuth login start provider=%s app_url=%s redirect_uri=%s enabled=%s",
        provider,
        APP_URL,
        redirect_uri,
        sorted(ENABLED_PROVIDERS),
    )

    if provider == "linkedin":
        state = secrets.token_urlsafe(32)
        request.session["_li_state"] = state
        qs = urlencode({
            "response_type": "code",
            "client_id": os.getenv("LINKEDIN_CLIENT_ID", ""),
            "redirect_uri": redirect_uri,
            "scope": "openid email profile",
            "state": state,
        })
        authorize_url = f"https://www.linkedin.com/oauth/v2/authorization?{qs}"
        logger.info("OAuth redirect provider=linkedin url=%s", _redact_url(authorize_url))
        return RedirectResponse(authorize_url)

    client = oauth.create_client(provider)
    response = await client.authorize_redirect(request, redirect_uri)
    logger.info(
        "OAuth redirect provider=%s status=%s location=%s",
        provider,
        response.status_code,
        _redact_url(response.headers.get("location")),
    )
    return response


@router.get("/auth/{provider}/callback")
async def oauth_callback(request: Request, provider: str, db: AsyncSession = Depends(get_db)):
    if provider not in ENABLED_PROVIDERS:
        logger.warning(
            "OAuth callback for unavailable provider=%s query_keys=%s",
            provider,
            _safe_query_keys(request),
        )
        return RedirectResponse(url="/login", status_code=303)
    logger.info(
        "OAuth callback received provider=%s query_keys=%s",
        provider,
        _safe_query_keys(request),
    )

    provider_user_id: str | None = None
    email: str | None = None
    display_name: str | None = None

    if provider == "linkedin":
        # LinkedIn handled manually — authlib rejects LinkedIn's id_token because
        # LinkedIn omits the nonce claim that authlib's OIDC validation requires.
        import httpx as _httpx

        state = request.query_params.get("state")
        if not state or state != request.session.pop("_li_state", None):
            logger.warning("OAuth linkedin state mismatch query_keys=%s", _safe_query_keys(request))
            return RedirectResponse(url="/login?msg=oauth-failed", status_code=303)

        code = request.query_params.get("code")
        if not code:
            logger.warning("OAuth linkedin callback missing code query_keys=%s", _safe_query_keys(request))
            return RedirectResponse(url="/login?msg=oauth-failed", status_code=303)

        redirect_uri = f"{APP_URL}/auth/linkedin/callback"
        async with _httpx.AsyncClient(verify=_SSL_VERIFY) as hc:
            tok_resp = await hc.post(
                "https://www.linkedin.com/oauth/v2/accessToken",
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": redirect_uri,
                    "client_id": os.getenv("LINKEDIN_CLIENT_ID", ""),
                    "client_secret": os.getenv("LINKEDIN_CLIENT_SECRET", ""),
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            token_data = tok_resp.json()
            logger.info("OAuth linkedin token response status=%s keys=%s", tok_resp.status_code, sorted(token_data.keys()))

        li_access_token = token_data.get("access_token")
        if not li_access_token:
            logger.warning("OAuth linkedin token exchange failed response=%s", token_data)
            return RedirectResponse(url="/login?msg=oauth-failed", status_code=303)

        async with _httpx.AsyncClient(verify=_SSL_VERIFY) as hc:
            ui_resp = await hc.get(
                "https://api.linkedin.com/v2/userinfo",
                headers={"Authorization": f"Bearer {li_access_token}"},
            )
            info = ui_resp.json()
            logger.info("OAuth linkedin userinfo response status=%s keys=%s", ui_resp.status_code, sorted(info.keys()))

        provider_user_id = info.get("sub")
        email = info.get("email")
        display_name = info.get("name")
        if not provider_user_id:
            logger.warning("OAuth linkedin missing sub userinfo=%s", info)
            return RedirectResponse(url="/login?msg=oauth-failed", status_code=303)

    else:
        client = oauth.create_client(provider)
        try:
            token = await client.authorize_access_token(request)
        except OAuthError as exc:
            logger.exception("OAuth token exchange failed provider=%s error=%s", provider, exc)
            existing = await get_optional_user(request, db)
            if existing:
                return RedirectResponse(url="/profile", status_code=303)
            return RedirectResponse(url="/login?msg=oauth-failed", status_code=303)
        logger.info("OAuth token exchange succeeded provider=%s token_keys=%s", provider, sorted(token.keys()))

        if provider in ("google", "microsoft"):
            info = token.get("userinfo") or {}
            provider_user_id = info.get("sub")
            email = info.get("email")
            display_name = info.get("name")

        elif provider == "twitter":
            resp = await client.get(
                "users/me",
                token=token,
                params={"user.fields": "id,name,username"},
            )
            payload = resp.json()
            logger.info(
                "OAuth twitter users/me response status=%s payload_keys=%s",
                resp.status_code,
                sorted(payload.keys()),
            )
            data = payload.get("data", {})
            if not data:
                logger.warning("OAuth twitter users/me failed payload=%s", payload)
            provider_user_id = data.get("id")
            display_name = data.get("name") or data.get("username")

    if not provider_user_id:
        logger.warning("OAuth missing provider_user_id provider=%s", provider)
        return RedirectResponse(url="/login?msg=oauth-failed", status_code=303)

    user = await find_or_create_oauth_user(db, provider, str(provider_user_id), email, display_name)
    user.last_login = datetime.now(timezone.utc)
    await db.commit()
    logger.info(
        "OAuth login complete provider=%s user_id=%s has_email=%s",
        provider,
        user.id,
        bool(email),
    )

    access_token = create_access_token(user.id)
    next_url = _consume_next(request)
    response = RedirectResponse(url=next_url or "/profile", status_code=303)
    response.set_cookie(
        "access_token",
        access_token,
        httponly=True,
        samesite="lax",
        max_age=60 * 60 * 24 * 30,
        secure=_COOKIE_SECURE,
    )
    return response
