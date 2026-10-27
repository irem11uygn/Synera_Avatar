# android/

Kotlin Android araç satış uygulaması: çevrimdışı satış, otomatik lot seçimi (ilk dolan ilk çıkar), yerel SQLite, sunucuyla eşitleme, geri çağrılan ve süresi geçen lotların satışının engellenmesi, gün sonu ve araç sayımı. Türkçe / English.

**Teknoloji:** Kotlin 2.4.21, Android Gradle Plugin 9.4.1 (Kotlin'i kendisi derler — built-in Kotlin), Gradle 9.8.2, Jetpack Compose (BOM 2026.09.00), Room 2.8.5 + KSP, Retrofit 3 + kotlinx.serialization (`docs/decisions/ADR-003`). compileSdk / targetSdk 37, minSdk 26.

**Durum (28 Ekim):** Giriş (dil seçimi); alt menü: **Satış** (bugünkü satış ve nakit, dikkat edilecek lotlar, bağlantı şeridi), **Stok** (arama, son kullanma ve satışa kapalı etiketleri), **Geçmiş** (gönderim durumu), **Gün sonu** (sunucudan özet, araç sayımı). Satış dört adım: müşteri → ürün (lot kendiliğinden seçilir) → ödeme türü → özet. Satış önce telefona (Room/SQLite, sürüm 4) kaydedilir; eşitleme önce gönderir (`/api/v1/sync/push`), sonra çeker (`/api/v1/sync/pull`). Bağlantı yoksa WorkManager bağlantı gelince gönderir. Sunucu sıfırlandıysa bekleyen satış gönderilmez, satıcıya bildirilir.

| Klasör | Amaç |
|---|---|
| `app/src/main/java/.../data/local` | Room tabloları ve DAO (para: kuruş, miktar: binde bir birim — ADR-006) |
| `.../data/remote` | Retrofit arayüzü, API veri sınıfları, Türkçe hata mesajı çevirisi |
| `.../data/repo` | Oturum saklama, sunucu yanıtının yerel tablolara çevrilmesi, depo (repository) |
| `.../ui` | Compose ekranları ve ViewModel'ler (giriş, ana ekran ve sekmeler, satış sihirbazı, gün sonu) |
| `.../sync` | Arka planda gönderim işi (WorkManager) |
| `.../util` | Para/miktar dönüşümleri, tarih biçimi, dil (`I18n.kt`, İngilizce sözlük `I18nEn.kt`), yerel ağ izni kararı |
| `app/src/test` | JVM birim testleri |

## Derleme ve test

Gereken: JDK 17 veya üstü (Android Studio'nun kendi JDK'si yeterli), Android SDK (platform 37, build-tools 36.0.0). `local.properties` dosyası Android Studio tarafından oluşturulur ya da elle yazılır: `sdk.dir=C:/Users/<kullanıcı>/AppData/Local/Android/Sdk`.

Windows'ta (Git Bash), Android Studio'nun JDK'siyle:

```bash
export JAVA_HOME="/c/Program Files/Android/Android Studio/jbr"
```

```bash
./gradlew assembleDebug testDebugUnitTest
```

APK: `app/build/outputs/apk/debug/app-debug.apk`. Android Studio'da `android/` klasörünü açıp "Run" ile de çalıştırılabilir.

## Çalıştırma

1. Sunucuyu başlatın (depo kökünde `docker compose up --build -d`).
2. Uygulamayı emülatörde açın. Sunucu adresi varsayılan olarak `http://10.0.2.2:8000` gelir (emülatörün bilgisayara eriştiği adres). Gerçek telefonda bilgisayarın yerel ağ adresini yazın (ör. `http://192.168.1.20:8000`).
3. `satis1` / `satis123` ile giriş yapın.

**Android 17 notu:** targetSdk 37 olan uygulamalar yerel ağdaki adreslere ancak `ACCESS_LOCAL_NETWORK` ("Yakındaki cihazlar") çalışma anı izniyle erişebilir; izin yoksa bağlantı zaman aşımına uğrar. Uygulama bu izni yalnız sunucu adresi yerel ağdaysa girişte ister. İnternetteki bir sunucu için izin gerekmez.

## Bilinen sınırlamalar (prototip)

- Sunucuyla HTTP konuşulur (`network_security_config.xml`); gerçek kurulumda HTTPS olmalı.
- Oturum belirteci uygulamaya özel alanda şifrelenmeden saklanır.
- Geliştirme bilgisayarındaki proje yolu ASCII dışı karakter içerdiği için `gradle.properties`'te `android.overridePathCheck=true` var; ASCII yolda etkisizdir.

İlgili gereksinimler: `docs/requirements.md` → FR-4xx, TR-001, TR-002, NFR-005.
