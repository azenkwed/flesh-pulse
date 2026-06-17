"""OAuth provider registration and shared find-or-create logic."""
import logging
import os

from authlib.integrations.starlette_client import OAuth
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.utils import _mask
from backend.database.models import OAuthAccount, User

oauth = OAuth()
logger = logging.getLogger(__name__)

_G_ID,  _G_SEC  = os.getenv("GOOGLE_CLIENT_ID", ""),    os.getenv("GOOGLE_CLIENT_SECRET", "")
_LI_ID, _LI_SEC = os.getenv("LINKEDIN_CLIENT_ID", ""),  os.getenv("LINKEDIN_CLIENT_SECRET", "")
_TW_ID, _TW_SEC = os.getenv("TWITTER_CLIENT_ID", ""),   os.getenv("TWITTER_CLIENT_SECRET", "")
_MS_ID, _MS_SEC = os.getenv("MICROSOFT_CLIENT_ID", ""), os.getenv("MICROSOFT_CLIENT_SECRET", "")

ENABLED_PROVIDERS: set[str] = set()

if _G_ID and _G_SEC:
    oauth.register(
        name="google",
        client_id=_G_ID,
        client_secret=_G_SEC,
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )
    ENABLED_PROVIDERS.add("google")
    logger.info("OAuth provider enabled provider=google client_id=%s", _mask(_G_ID))

if _LI_ID and _LI_SEC:
    # LinkedIn is handled manually in auth/routes.py to avoid authlib OIDC validation
    # (LinkedIn returns an id_token without a nonce claim, which authlib rejects).
    # We only register in ENABLED_PROVIDERS so the sign-in button appears.
    ENABLED_PROVIDERS.add("linkedin")
    logger.info("OAuth provider enabled provider=linkedin client_id=%s", _mask(_LI_ID))

# X (Twitter) OAuth disabled — login unreliable, credentials still kept in env

if _MS_ID and _MS_SEC:
    oauth.register(
        name="microsoft",
        client_id=_MS_ID,
        client_secret=_MS_SEC,
        server_metadata_url="https://login.microsoftonline.com/common/v2.0/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )
    ENABLED_PROVIDERS.add("microsoft")
    logger.info("OAuth provider enabled provider=microsoft client_id=%s", _mask(_MS_ID))

if not ENABLED_PROVIDERS:
    logger.info("No OAuth providers enabled")


async def find_or_create_oauth_user(
    db: AsyncSession,
    provider: str,
    provider_user_id: str,
    email: str | None,
    display_name: str | None,
) -> User:
    # Existing OAuth link → return its user
    link_q = await db.execute(
        select(OAuthAccount).where(
            OAuthAccount.provider == provider,
            OAuthAccount.provider_user_id == provider_user_id,
        )
    )
    link = link_q.scalar_one_or_none()
    if link:
        user_q = await db.execute(select(User).where(User.id == link.user_id))
        return user_q.scalar_one()

    # Match by email to merge with an existing account
    user = None
    if email:
        user_q = await db.execute(select(User).where(User.email == email))
        user = user_q.scalar_one_or_none()

    if not user:
        # Twitter may not return an email — store a placeholder so the unique constraint holds
        user = User(
            email=email or f"{provider}_{provider_user_id}@sexhealthnews.local",
            password_hash="",          # OAuth-only accounts have no password
            display_name=display_name,
            email_verified=bool(email),
        )
        db.add(user)
        await db.flush()

    db.add(OAuthAccount(
        user_id=user.id,
        provider=provider,
        provider_user_id=provider_user_id,
        provider_email=email,
    ))
    await db.commit()
    await db.refresh(user)
    return user
