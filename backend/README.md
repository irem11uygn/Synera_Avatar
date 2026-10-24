# backend/

Merkezi sunucu: REST API, iş kuralları (maliyet, stok, lot, geri çağırma), MySQL erişimi, Android senkronizasyon uçları ve YZ tahminlerinin sunulması.

**Teknoloji:** Python 3.12 + FastAPI + SQLAlchemy 2 + Alembic + PyMySQL (`docs/decisions/ADR-001`). Bağımlılıklar `requirements.txt` ve `requirements-dev.txt` içinde sürümleri sabitlenmiş olarak durur.

**Durum:** Şema, örnek kayıtlar (T-06), stok defteri, lot ağı ve maliyet motoru (T-07, T-08) hazır. Uç nokta olarak yalnız `GET /api/v1/health` var; iş uçları T-09'dan itibaren eklenecek.

| Dosya / klasör | Amaç |
|---|---|
| `app/main.py` | Uygulama, router kaydı, hata işleyicileri |
| `app/config.py` | Ortam değişkenleri |
| `app/db.py` | Bağlantı, oturum, ORM taban sınıfı, kısıt adlandırma kuralı, veritabanı bekleme |
| `app/errors.py` | İş kuralı hataları (sabit kod + Türkçe mesaj) |
| `app/models/` | 31 tablo (`data_model.md`); `types.py` ortak sütun tipleri, `enums.py` durum değerleri, `sync.py` değişiklik numarası |
| `app/domain/` | Veritabanısız saf hesaplar: `money` (yuvarlama), `costing` (EKP, kâr, değerli çıkış), `allocation` (dağıtım), `balance` (ağırlık dengesi), `graph` (lot ağında gezinme) |
| `app/services/` | İş akışları: `ledger` (deftere **tek** yazma yolu), `lot_graph`, `purchasing`, `numbering`, `integrity` (değişmezler I-1…I-8) |
| `app/seed.py` | Boş veritabanına örnek kayıt yükleme (`python -m app.seed`); alışlar defter üzerinden yazılır |
| `app/security.py` | Parola özeti (scrypt) |
| `app/api/` | Uç noktalar ve hata yanıtı biçimi |
| `migrations/` | Alembic şema göçleri (ilk göç tetikleyicileri de kurar) |
| `tests/` | pytest testleri; ayrı `avatar_test` veritabanında çalışır |
| `start.sh` | Konteyner açılışı: veritabanını bekle → şema göçü → örnek kayıtlar → sunucu |

Yeni şema göçü üretmek (model değiştirildikten sonra, depo kökünde, PowerShell):

```powershell
docker compose run --rm --no-deps -v "${PWD}\backend:/app" api alembic revision --autogenerate -m "aciklama"
```

Çalıştırma ve test komutları kök dizindeki `README.md`'de.

İlgili gereksinimler: `docs/requirements.md` → FR-1xx, FR-2xx, FR-3xx, FR-6xx, TR-004.
