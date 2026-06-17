"""Auth utilities — password hashing, JWT tokens, signed email tokens."""
import base64
import hashlib
import hmac
import os
from datetime import datetime, timedelta, timezone

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from jose import JWTError, jwt

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-secret-change-in-production")


def _mask(value: str | None, visible: int = 6) -> str:
    if not value:
        return "<empty>"
    if len(value) <= visible * 2:
        return "<set>"
    return f"{value[:visible]}...{value[-visible:]}"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 30
_PBKDF2_ITERS = 480_000


def hash_password(password: str) -> str:
    salt = os.urandom(32)
    key = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _PBKDF2_ITERS)
    return base64.b64encode(salt + key).decode()


def verify_password(password: str, hashed: str) -> bool:
    try:
        decoded = base64.b64decode(hashed.encode())
        salt, stored = decoded[:32], decoded[32:]
        key = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _PBKDF2_ITERS)
        return hmac.compare_digest(key, stored)
    except Exception:
        return False


def create_access_token(user_id: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    return jwt.encode({"sub": str(user_id), "exp": expire}, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> int | None:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return int(payload["sub"])
    except (JWTError, KeyError, ValueError):
        return None


def create_email_token(data: dict) -> str:
    s = URLSafeTimedSerializer(SECRET_KEY)
    return s.dumps(data)


def verify_email_token(token: str, max_age: int = 86400) -> dict | None:
    s = URLSafeTimedSerializer(SECRET_KEY)
    try:
        return s.loads(token, max_age=max_age)
    except (SignatureExpired, BadSignature):
        return None
