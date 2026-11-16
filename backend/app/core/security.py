from datetime import datetime, timedelta, timezone
import jwt
from pwdlib import PasswordHash
from app.core.config import get_settings

password_hash = PasswordHash.recommended()
def hash_password(password: str) -> str:
    return password_hash.hash(password)
def verify_password(password: str, hashed: str) -> bool:
    return password_hash.verify(password, hashed)
def create_access_token(subject: str) -> str:
    settings = get_settings()
    expires = datetime.now(timezone.utc) + timedelta(minutes=settings.AUTH_ACCESS_TOKEN_MINUTES)
    return jwt.encode({"sub": subject, "exp": expires, "type": "access"}, settings.AUTH_JWT_SECRET, algorithm="HS256")
def create_refresh_token(subject: str) -> str:
    settings = get_settings()
    expires = datetime.now(timezone.utc) + timedelta(days=settings.AUTH_REFRESH_TOKEN_DAYS)
    return jwt.encode({"sub": subject, "exp": expires, "type": "refresh"}, settings.AUTH_JWT_SECRET, algorithm="HS256")
def decode_token(token: str, expected_type: str):
    settings = get_settings()
    payload = jwt.decode(token, settings.AUTH_JWT_SECRET, algorithms=["HS256"])
    if payload.get("type") != expected_type or not payload.get("sub"):
        raise jwt.InvalidTokenError("Invalid token")
    return payload
