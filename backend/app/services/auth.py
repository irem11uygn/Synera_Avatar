"""Giriş, oturum belirteçleri ve şifre işlemleri (architecture.md §8).

- Sunucuda belirtecin kendisi değil yalnız SHA-256 özeti tutulur; oturum 12 saat geçerlidir.
- Kaba kuvvete karşı: aynı kullanıcı adı ya da aynı adres için 5 dakikada en çok 10 hatalı deneme;
  sonra 429 (bellek içi, tek sunucu süreci için yeterli).
- Kullanıcı adı yoksa da parola özeti hesaplanır: yanıt süresinden kullanıcının var olup olmadığı
  anlaşılmasın.
- Yönetici şifreyi sıfırlarsa kullanıcı ilk girişte yeni şifre belirlemek zorundadır.
"""

import hashlib
import secrets
import threading
import time
from collections import defaultdict, deque
from datetime import timedelta

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.errors import InvalidInput, TooManyAttempts, Unauthorized
from app.models import AuthSession, User
from app.models.types import utcnow
from app.security import hash_password, verify_password

SESSION_LIFETIME = timedelta(hours=12)
MIN_PASSWORD_LENGTH = 8
MAX_FAILURES = 10
FAILURE_WINDOW_S = 300
_DUMMY_HASH = hash_password("kullanici-yok-ornek")


class LoginLimiter:
    """Anahtar başına (kullanıcı adı, adres) son FAILURE_WINDOW_S saniyedeki hatalı denemeler."""

    def __init__(self, max_failures: int = MAX_FAILURES, window_s: float = FAILURE_WINDOW_S) -> None:
        self.max_failures = max_failures
        self.window_s = window_s
        self._failures: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def _recent(self, key: str, now: float) -> deque[float]:
        attempts = self._failures[key]
        while attempts and now - attempts[0] > self.window_s:
            attempts.popleft()
        return attempts

    def check(self, *keys: str) -> None:
        now = time.monotonic()
        with self._lock:
            if any(len(self._recent(key, now)) >= self.max_failures for key in keys):
                raise TooManyAttempts(
                    "Çok fazla hatalı giriş denemesi. Birkaç dakika bekleyip yeniden deneyin.",
                    retry_after_s=int(self.window_s),
                )

    def failed(self, *keys: str) -> None:
        now = time.monotonic()
        with self._lock:
            for key in keys:
                self._recent(key, now).append(now)

    def succeeded(self, *keys: str) -> None:
        with self._lock:
            for key in keys:
                self._failures.pop(key, None)

    def reset(self) -> None:
        with self._lock:
            self._failures.clear()


limiter = LoginLimiter()


def login(session: Session, username: str, password: str, client: str = "?") -> tuple[str, User]:
    """Doğru kullanıcı adı ve parolaya yeni bir oturum belirteci verir."""
    keys = (f"u:{username.strip().lower()}", f"a:{client}")
    limiter.check(*keys)
    user = session.scalars(select(User).where(User.username == username.strip())).one_or_none()
    valid = verify_password(password, user.password_hash if user else _DUMMY_HASH)
    if user is None or not user.active or not valid:
        limiter.failed(*keys)
        raise Unauthorized("Kullanıcı adı veya parola hatalı.")
    limiter.succeeded(*keys)
    _purge_expired(session)
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


def logout(session: Session, token: str) -> None:
    """Oturumu sunucuda kapatır; belirteç bundan sonra geçersizdir."""
    auth_session = session.get(AuthSession, _digest(token))
    if auth_session is not None:
        session.delete(auth_session)
        session.flush()


def check_new_password(password: str) -> None:
    if len(password) < MIN_PASSWORD_LENGTH:
        raise InvalidInput(f"Şifre en az {MIN_PASSWORD_LENGTH} karakter olmalı.")
    if password.isdigit() or password.isalpha():
        raise InvalidInput("Şifrede hem harf hem rakam olmalı.")


def change_password(session: Session, user: User, current: str, new: str, keep_token: str) -> None:
    """Kullanıcı kendi şifresini değiştirir; bu oturum dışındaki bütün oturumları kapanır."""
    if not verify_password(current, user.password_hash):
        raise InvalidInput("Mevcut şifre yanlış.")
    if current == new:
        raise InvalidInput("Yeni şifre eskisiyle aynı olamaz.")
    check_new_password(new)
    user.password_hash = hash_password(new)
    user.must_change_password = False
    session.execute(
        delete(AuthSession).where(
            AuthSession.user_id == user.id, AuthSession.token_hash != _digest(keep_token)
        )
    )
    session.flush()


def end_all_sessions(session: Session, user_id: int) -> None:
    session.execute(delete(AuthSession).where(AuthSession.user_id == user_id))
    session.flush()


def _purge_expired(session: Session) -> None:
    """Süresi dolmuş oturum kayıtları girişte temizlenir (tablo büyümesin)."""
    session.execute(delete(AuthSession).where(AuthSession.expires_at <= utcnow()))


def _digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()
