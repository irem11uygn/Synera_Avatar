"""Kullanıcının elle gönderdiği e-postaların kuralları: açık posta rölesi yok, gönderim sınırı var.

- Alıcı yalnız şunlardan biri olabilir: sistemdeki aktif bir kullanıcının e-postası, (izin verilen
  uçlarda) kayıtlı bir carinin (müşteri, tedarikçi, dış üretici) e-postası ya da ALLOWED_EMAIL_DOMAINS'teki
  bir alan adı. Başka adres 422; izinsiz adreslerin hepsi birden bildirilir.
- Kullanıcı başına dakikada en çok 5 gönderim; rapor e-postası ve serbest e-posta aynı sayaçtan düşer
  (biri ötekini atlatamaz). Bir toplu gönderim (ör. müşterilere ayrı ayrı geri çağırma bildirimi) tek
  gönderim sayılır. Sayaç süreç belleğindedir (tek sunucu süreci için yeterli).
"""

import threading
import time
from collections import defaultdict, deque
from collections.abc import Iterable

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.errors import InvalidInput, TooManyAttempts
from app.models import Partner, User
from app.services.mail import clean_recipients

MAX_PER_WINDOW = 5
WINDOW_S = 60


class SendLimiter:
    """Anahtar (kullanıcı) başına son WINDOW_S saniyedeki gönderimler."""

    def __init__(self, max_events: int = MAX_PER_WINDOW, window_s: float = WINDOW_S) -> None:
        self.max_events = max_events
        self.window_s = window_s
        self._events: dict[int, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def check(self, user_id: int) -> None:
        now = time.monotonic()
        with self._lock:
            events = self._events[user_id]
            while events and now - events[0] > self.window_s:
                events.popleft()
            if len(events) >= self.max_events:
                wait = int(self.window_s - (now - events[0])) + 1
                raise TooManyAttempts(
                    f"Dakikada en çok {self.max_events} e-posta gönderimi yapabilirsiniz; "
                    f"{wait} saniye sonra yeniden deneyin.",
                    retry_after_s=wait,
                )

    def record(self, user_id: int) -> None:
        with self._lock:
            self._events[user_id].append(time.monotonic())

    def reset(self) -> None:
        with self._lock:
            self._events.clear()


limiter = SendLimiter()


def allowed_recipients(session: Session, addresses: Iterable[str], *, partners: bool = False) -> list[str]:
    """Biçimi doğru ve izinli alıcılar. `partners`: kayıtlı cari e-postaları da izinli."""
    recipients = clean_recipients(addresses)
    known = {
        email
        for email in session.scalars(
            select(func.lower(User.email)).where(User.active, User.email.is_not(None))
        )
        if email
    }
    if partners:
        known |= {
            email
            for email in session.scalars(select(func.lower(Partner.email)).where(Partner.email.is_not(None)))
            if email
        }
    domains = get_settings().allowed_email_domains
    rejected = [
        address
        for address in recipients
        if address.lower() not in known and address.rpartition("@")[2].lower() not in domains
    ]
    if rejected:
        who = (
            "sistemde kayıtlı aktif bir kullanıcı ya da kayıtlı bir cari (müşteri, tedarikçi, dış üretici)"
            if partners
            else "sistemde kayıtlı aktif bir kullanıcı"
        )
        raise InvalidInput(
            f"Bu adreslere e-posta gönderilemez: {', '.join(rejected)}. Alıcı {who} olmalı ya da adresin "
            "alan adı izinli listede (ALLOWED_EMAIL_DOMAINS) bulunmalı.",
            rejected=rejected,
        )
    return recipients
