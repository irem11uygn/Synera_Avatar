"""İlk yöneticiyi açar (SEED_PROFILE=none ile sıfırdan kurulum için).

Kullanım (sunucu konteynerinde):
    docker compose exec api python -m app.create_admin <kullanici_adi> "<Ad Soyad>" [e-posta]

Şifre komut satırına ya da ortam değişkenine yazılmaz: tek kullanımlık geçici şifre üretilir, yalnız bir
kez ekrana basılır; kullanıcı ilk girişte kendi şifresini belirlemeden hiçbir işlem yapamaz. Kullanıcı adı
zaten varsa hiçbir şey değişmez.
"""

import sys

from app.db import get_sessionmaker
from app.errors import InvalidInput
from app.models.enums import UserRole
from app.services import audit
from app.services.users import create_user, temporary_password


def main(argv: list[str]) -> int:
    if len(argv) not in (2, 3):
        print(__doc__)
        return 2
    username, full_name = argv[0], argv[1]
    email = argv[2] if len(argv) == 3 else None
    password = temporary_password()
    try:
        with get_sessionmaker()() as session, session.begin():
            user = create_user(
                session,
                username=username,
                full_name=full_name,
                role=UserRole.YONETICI,
                password=password,
                email=email,
            )
            name = user.username
            audit.log(session, "KULLANICI", f"İlk yönetici komut satırından açıldı: {name}", username=name)
    except InvalidInput as error:
        print(f"Yönetici açılamadı: {error.message}")
        return 1
    print(f"Yönetici açıldı: {name}")
    print(f"Geçici şifre (bir kez gösterilir): {password}")
    print("İlk girişte yeni şifre belirlenmeden hiçbir işlem yapılamaz.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
