# Karar Kayıtları (ADR)

Önemli teknik ve mimari kararlar burada, her biri ayrı bir dosyada tutulur: `ADR-001-kisa-baslik.md`.

Bir karar değişirse eski kayıt silinmez; durumu "Yerini aldı: ADR-00x" olarak güncellenir.

## Dizin

| No | Başlık | Durum | Tarih |
|---|---|---|---|
| [ADR-001](ADR-001-sunucu-python-fastapi.md) | Sunucu Python + FastAPI; YZ aynı Python projesinde | Kabul edildi | 24.10.2026 |
| [ADR-002](ADR-002-web-react-vite-antd.md) | Web arayüzü React + Vite + TypeScript + Ant Design | Kabul edildi | 24.10.2026 |
| [ADR-003](ADR-003-android-compose-room.md) | Android Kotlin + Compose + Room + WorkManager + Retrofit | Kabul edildi | 24.10.2026 |
| [ADR-004](ADR-004-senkronizasyon.md) | SQLite ↔ MySQL senkronizasyonu | Kabul edildi | 24.10.2026 |
| [ADR-005](ADR-005-yapay-zeka-yaklasimi.md) | Yapay zekâ yaklaşımı ve değerlendirme | Kabul edildi | 24.10.2026 |
| [ADR-006](ADR-006-para-ve-miktar.md) | Para ve miktar gösterimi, yuvarlama | Kabul edildi | 24.10.2026 |
| [ADR-007](ADR-007-calistirma-docker-compose.md) | Çalıştırma Docker Compose ile; MySQL 8.4 | Kabul edildi | 24.10.2026 |
| [ADR-008](ADR-008-stok-defteri.md) | Stok defteri: değişmez hareketler, kilitli özetler, lot düzeyinde değerleme | Kabul edildi | 24.10.2026 |

## Şablon

```markdown
# ADR-00X: <Kısa başlık>

- Durum: Önerildi | Kabul edildi | Yerini aldı: ADR-00Y
- Tarih: GG.AA.YYYY
- İlgili gereksinimler: FR-…, NFR-…, TR-…

## Bağlam
Hangi problemi çözüyoruz, hangi kısıtlar var?

## Seçenekler
1. … — artıları / eksileri
2. … — artıları / eksileri

## Karar
Seçilen seçenek ve gerekçesi.

## Sonuçlar
Bu kararın getirdiği kazanımlar, maliyetler ve riskler.
```
