# ADR-007: Çalıştırma Docker Compose ile; MySQL 8.4

- Durum: **Kabul edildi** (ekip onayı: 24.10.2026)
- Tarih: 24.10.2026
- İlgili gereksinimler: NFR-006, CR-011, TR-003, AS-009, R-08, R-09
- Ayrıntı: `docs/technical_research.md` §9 (D-08)

## Bağlam
Değerlendirici prototipi kendi bilgisayarında çalıştırabilmeli. Geliştirme bilgisayarında Windows Uygulama Denetimi bazı Python paketlerini engelleyebiliyor.

## Seçenekler
1. **Docker Compose:** `mysql:8.4` + `api` (Python 3.12) + `web` (React derlemesi + statik sunucu)
2. Elle kurulum (Python, Node, MySQL ayrı ayrı) — her bilgisayarda farklı sorun çıkar.
3. Bulutta canlı yayın — hesap ve maliyet gerektirir; değerlendirme son commit üzerinden yapılıyor.

## Karar
Seçenek 1. Tek komut `docker compose up --build`. API açılışta şema göçlerini uygular ve veritabanı boşsa örnek kayıtları yükler. MySQL için sabit `8.4` etiketi kullanılır; `latest` artık 26.x serisini gösteriyor ve `lts` etiketinin hedefi netleşmedi. Android APK GitHub "Release" ekine konur. Elle kurulum adımları README'de yedek olarak yazılır.

## Sonuçlar
- Python paketleri Linux konteynerinde çalışır; Windows Uygulama Denetimi sorunu geliştirme dışında kalır.
- Windows'ta Docker Desktop + WSL2 gerekir; bu bilgisayarda kurulu ama kapalı.
