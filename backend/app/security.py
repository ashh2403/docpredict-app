"""Password hashing, JWT handling and the authenticated-user dependency."""
from __future__ import annotations

import threading
import time
import uuid
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from .config import settings
from .database import get_db
from .models import RevokedToken, User

_bearer = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("ascii")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("ascii"))
    except ValueError:
        return False


# A real hash used to equalise timing when the e-mail address does not exist.
_DUMMY_HASH = hash_password(uuid.uuid4().hex)


def verify_password_or_dummy(password: str, user: User | None) -> bool:
    if user is None:
        verify_password(password, _DUMMY_HASH)
        return False
    return verify_password(password, user.password_hash)


def create_access_token(user_id: int) -> tuple[str, int]:
    expires_in = settings.token_expire_minutes * 60
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "jti": uuid.uuid4().hex,
        "iat": now,
        "exp": now + timedelta(seconds=expires_in),
        "type": "access",
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm), expires_in


def _unauthorized(detail: str = "Not authenticated") -> HTTPException:
    return HTTPException(status.HTTP_401_UNAUTHORIZED, detail=detail, headers={"WWW-Authenticate": "Bearer"})


def decode_token(token: str) -> dict:
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.jwt_algorithm],
            options={"require": ["sub", "jti", "exp"]},
        )
    except jwt.ExpiredSignatureError as exc:
        raise _unauthorized("Session expired. Please sign in again.") from exc
    except jwt.InvalidTokenError as exc:
        raise _unauthorized("Invalid authentication token.") from exc
    if payload.get("type") != "access":
        raise _unauthorized("Invalid authentication token.")
    return payload


def get_token_payload(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> dict:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise _unauthorized()
    payload = decode_token(credentials.credentials)
    if db.get(RevokedToken, payload["jti"]) is not None:
        raise _unauthorized("Session has been signed out.")
    return payload


def get_current_user(payload: dict = Depends(get_token_payload), db: Session = Depends(get_db)) -> User:
    try:
        user_id = int(payload["sub"])
    except (TypeError, ValueError) as exc:
        raise _unauthorized("Invalid authentication token.") from exc
    user = db.get(User, user_id)
    if user is None:
        raise _unauthorized("Account no longer exists.")
    return user


def revoke_token(db: Session, payload: dict) -> None:
    expires_at = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
    db.merge(RevokedToken(jti=payload["jti"], expires_at=expires_at))
    # Opportunistically purge entries that have expired anyway.
    db.execute(delete(RevokedToken).where(RevokedToken.expires_at < datetime.now(timezone.utc)))
    db.commit()


class LoginThrottle:
    """In-memory limiter for failed sign-ins per e-mail address (single-process only)."""

    def __init__(self, max_failures: int = 5, window_seconds: int = 900):
        self.max_failures = max_failures
        self.window = window_seconds
        self._failures: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def _prune(self, key: str, now: float) -> deque[float]:
        q = self._failures[key]
        while q and now - q[0] > self.window:
            q.popleft()
        return q

    def is_blocked(self, key: str) -> bool:
        with self._lock:
            return len(self._prune(key, time.monotonic())) >= self.max_failures

    def record_failure(self, key: str) -> None:
        with self._lock:
            now = time.monotonic()
            self._prune(key, now).append(now)

    def reset(self, key: str | None = None) -> None:
        with self._lock:
            if key is None:
                self._failures.clear()
            else:
                self._failures.pop(key, None)


login_throttle = LoginThrottle()


def user_exists(db: Session, email: str) -> bool:
    return db.scalar(select(User.id).where(User.email == email)) is not None
