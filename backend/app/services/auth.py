"""Giriş ve oturum belirteçleri (architecture.md §8). Sunucuda belirtecin yalnız SHA-256 özeti tutulur."""

import hashlib
import secrets
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.errors import Unauthorized
from app.models import AuthSession, User
from app.models.types import utcnow
from app.security import verify_password

SESSION_LIFETIME = timedelta(hours=12)


def login(session: Session, username: str, password: str) -> tuple[str, User]:
    """Doğru kullanıcı adı ve parolaya yeni bir oturum belirteci verir."""
    user = session.scalars(select(User).where(User.username == username)).one_or_none()
    if user is None or not user.active or not verify_password(password, user.password_hash):
        raise Unauthorized("Kullanıcı adı veya parola hatalı.")
    token = secrets.token_urlsafe(32)
    session.add(
        AuthSession(token_hash=_digest(token), user_id=user.id, expires_at=utcnow() + SESSION_LIFETIME)
    )
    session.flush()
    return token, user


def user_for_token(session: Session, token: str) -> User | None:
    auth_session = session.get(AuthSession, _digest(token))
    if auth_session is None or auth_session.expires_at <= utcnow():
        return None
    user = session.get(User, auth_session.user_id)
    return user if user is not None and user.active else None


def _digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()
