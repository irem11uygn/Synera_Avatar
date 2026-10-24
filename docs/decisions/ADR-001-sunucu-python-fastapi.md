# ADR-001: Sunucu Python + FastAPI; YZ aynı Python projesinde

- Durum: **Kabul edildi** (ekip onayı: 24.10.2026)
- Tarih: 24.10.2026
- İlgili gereksinimler: TR-004, TR-006, CR-008, CON-008, NFR-001
- Ayrıntı: `docs/technical_research.md` §2 (D-01)

## Bağlam
Şartname "Go veya uygun modern teknoloji; REST API" istiyor. Ekip Go bilmiyor, Kotlin ve Python biliyor. YZ modelleri pratikte Python ile yazılacak. Süre 8 gün.

## Seçenekler
1. **Python + FastAPI + SQLAlchemy 2 + Alembic + PyMySQL** — tek dil, sunucu ve YZ tek serviste, OpenAPI belgesi otomatik; dinamik tip riski testlerle azaltılır.
2. Kotlin + Ktor + ayrı Python YZ servisi — güçlü tipler, Android ile aynı dil; fazladan bir servis, iki derleme sistemi ve servisler arası bağlantı.
3. Kotlin + Spring Boot + ayrı Python YZ servisi — olgun ama ağır; öğrenme maliyeti yüksek.

## Karar
Seçenek 1. Sunucu kodu `backend/`, YZ kodu `ml/` altında ayrı bir Python paketi olarak durur. Sunucu bu paketi içe aktarır ve tahminleri kendi API'si üzerinden sunar (`/api/v1/ai/...`). Veritabanı sürücüsü olarak saf Python ile yazılmış PyMySQL seçilir; derlenmiş eklenti gerektirmez.

## Sonuçlar
- Çalışan servis sayısı en aza iner (MySQL + API/YZ + web).
- API belgesi (CR-008) koddan üretilir.
- Android ile sunucu farklı dillerde; senkron sözleşmesi küçük ve sabit tutulmalı.
- Bu öneri, sunucuyu yazacak kişinin Python'a yeterince hâkim olduğu varsayımına dayanır. Değilse seçenek 2'ye geçilir.
