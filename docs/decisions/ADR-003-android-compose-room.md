# ADR-003: Android Kotlin + Jetpack Compose + Room + WorkManager + Retrofit

- Durum: **Kabul edildi** (ekip onayı: 24.10.2026)
- Tarih: 24.10.2026
- İlgili gereksinimler: TR-001, TR-002, FR-401–405, NFR-005, NFR-001
- Ayrıntı: `docs/technical_research.md` §4 (D-03)

## Bağlam
Kotlin ve SQLite zorunlu. Uygulama lot bazlı satış yapmalı, çevrimdışı çalışabilmeli, sunucuyla senkronize olmalı ve geri çağrılan lotları engellemeli.

## Seçenekler
- Arayüz: **Jetpack Compose** / XML görünümleri
- Yerel veritabanı: **Room** / SQLDelight / doğrudan SQLiteOpenHelper
- Ağ: **Retrofit + kotlinx.serialization** / Ktor istemcisi
- Arka planda senkron: **WorkManager** / elle yazılmış servis
- Bağımlılık kurulumu: **elle** / Hilt

## Karar
Kalın yazılı seçenekler. Tek aktivite, ViewModel + StateFlow, depo (repository) katmanı. Uyumlu sürümleri Android Studio'nun yeni proje şablonu belirler. Tutarlar SQLite'ta **tamsayı kuruş**, miktarlar **tamsayı gram/adet** olarak saklanır (ADR-006).

## Sonuçlar
- Room verileri SQLite'ta tutar → TR-002 karşılanır; sorgular derleme anında denetlenir.
- WorkManager, ağ geldiğinde gönderimi kendiliğinden yeniden dener.
- Ekip XML görünümlerine daha hâkimse arayüz katmanı onunla yazılabilir; diğer kararlar değişmez.
- Bu bilgisayarda Android Studio ve SDK kurulu değil; kurulum (birkaç GB) gerekiyor. (24.10.2026: kuruldu.)

## Uygulamada görülenler (T-13, 24.10.2026)
- **AGP 9 built-in Kotlin:** AGP 9.4.1 Kotlin'i kendisi derler; `kotlin-android` eklentisi eklenmez. AGP'nin içindeki Kotlin 2.2.10'dur. Compose derleyici eklentisi 2.4.21 ile eklenince derleme Kotlin 2.4.21 ile yapılıyor (doğrulandı: `kotlinCompilerClasspath`).
- **Android 17 yerel ağ koruması:** targetSdk 37'de yerel ağ adreslerine erişim `ACCESS_LOCAL_NETWORK` çalışma anı iznine bağlı. targetSdk'yı 36'ya düşürmek yerine izin, yalnız sunucu yerel ağdaysa isteniyor. Gerçek kurulumda internetteki HTTPS sunucusu için izin gerekmez.
- **Gradle 9.8.2** (AGP 9.4 için en az 9.6); wrapper dağıtımın SHA-256 özetini doğrular.
