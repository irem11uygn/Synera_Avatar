# Güvenlik, kalite ve ürün denetimi

Tarih: 31 Ekim 2026. Kapsam: sunucu (FastAPI + MySQL), web (React + nginx), Android, e-posta, Docker, yedekleme, CI.
Denemeler yalnız bu bilgisayardaki yerel kurulumlarda yapıldı: geliştirme (`avatar`), demo (`avatar-yeni`: web 18380, API 18300) ve kabul testi kopyası (`avatar-kabul`). Hiçbir dış sisteme istek atılmadı.

Rapora şifre, belirteç ya da gerçek kişi verisi yazılmadı. README'deki demo hesapları yalnız yerel demo içindir.

**Durum etiketleri:**

| Etiket | Anlamı |
|---|---|
| **GEÇTİ** (PASS) | Kontrol yapıldı ve kanıtı var. |
| **KISMİ** (PARTIAL) | Bir kısmı sağlanıyor; eksik kısım "Not" sütununda. |
| **KALDI** (FAIL) | Sağlanmıyor. |
| **UYGULANAMAZ** (NOT APPLICABLE) | Sistem bu özelliği kullanmıyor. |
| **DOĞRULANMADI** (NOT VERIFIED) | Yazıldı ama çalıştığı gösterilemedi. |

Hiçbir alan "%100 güvenli" değildir. "GEÇTİ", yalnız tabloda yazan denemeyi geçti demektir.

## Özet

- **Önceki bulgular düzeltildi.** Dördü yüksek önemdeydi:
  - API ve Mailpit bütün ağa açıktı.
  - Demo dışı kurulumda örnek şifreler bilinen değerlerle açılıyordu.
  - Telefon oturum belirtecini şifresiz saklıyordu.
- **Yetki denetimi tam:** Bütün API uçlarının yetkisi koddan okunup sınanıyor:
  - 95 uç var.
  - Girişsiz istek denemesi: 93, hepsi 401.
  - Rol dışı istek denemesi: 223, hepsi 403.
  - Bu denemelerde yeni bir yetki açığı bulunmadı.
- **Testler:**

  | Bölüm | Sonuç |
  |---|---|
  | Sunucu | 274/274 |
  | Web | 32/32 |
  | Android | 26/26 |
  | Kabul | 23/23 |
  | Yapay zekâ | 4/4 |
  | Canlı saldırı denemesi | 27/27 reddedildi |

- **Yedekleme:** Yedek alındı, ayrı veritabanına geri yüklendi ve içerik bire bir aynı çıktı.
- **Bağımlılık ve gizli bilgi taraması:**
  - npm audit: 0 açık.
  - pip-audit: 0 açık.
  - gitleaks: git geçmişi (45 commit) ve çalışma ağacında bulgu yok.
- **En önemli kalan risk:** HTTPS yok; sistem yerel ağ demosu olarak HTTP ile çalışıyor.
- **GitHub Actions:** İş akışı yazıldı ama GitHub'da hiç çalışmadı, bu yüzden "doğrulanmadı" sayılır.

## A. Güvenlik kontrol tablosu

### A1. Yirmi temel kontrol

| # | Kontrol | Durum | Kanıt | Not |
|---|---|---|---|---|
| 1 | Kimlik doğrulama | **GEÇTİ** | `tests/test_auth.py`, `tests/test_access_matrix.py::test_every_non_public_endpoint_requires_login` (93 uç → 401), `::test_forged_or_expired_token_is_rejected`. Canlı: girişsiz 5 uç ve sahte belirteç → 401 | Şifre scrypt ile özetlenir. Belirteç sunucuda SHA-256 özetiyle saklanır, 12 saatte biter, çıkışta kapanır. Şifre değişince ya da sıfırlanınca diğer oturumlar kapanır. MFA yok. |
| 2 | Yetkilendirme (rol) | **GEÇTİ** | `app/access_matrix.py` + `tests/test_access_matrix.py`: 6 rol, 223 rol dışı istek → 403 `FORBIDDEN`. Belge: [api_yetki_matrisi.md](api_yetki_matrisi.md). Canlı: 6 deneme → 403 | Matris koddan üretilir; elle yazılmadığı için kodla ayrışmaz. Web'de rol dışı yönetici ekranına adresle gidilince 403 sayfası çıkar (`web/src/lib/roles.test.ts`). |
| 3 | Girdi doğrulama | **GEÇTİ** | `tests/test_security.py::test_server_side_validation_rejects_bad_input`. Canlı: geçersiz düzeltme ve 501 karakterlik neden → 422 | Pydantic şemaları: pozitif miktar, uzunluk, rol listesi, tarih. Hatalı istek veriyi değiştirmez. |
| 4 | SQL enjeksiyonu | **GEÇTİ** | `test_sql_injection_payloads_are_plain_text`. Canlı: `' OR '1'='1` → boş liste; `' OR 1=1 --` → 404 | ORM ve parametreli sorgu kullanılır. `text()` sorguları (`services/integrity.py`) sabit metindir. |
| 5 | XSS | **GEÇTİ** | `test_stored_markup_is_returned_as_text_and_escaped_in_mail`. Kodda `dangerouslySetInnerHTML` yok. CSP `script-src 'self'` | React çıktıyı kaçışlar; e-posta HTML'i kaçışlıdır. Kalan risk: web belirteci `sessionStorage`'da (C-2). |
| 6 | CSRF | **UYGULANAMAZ** | Çerez kullanılmıyor; belirteç `Authorization: Bearer` başlığıyla gider | Tarayıcı belirteci kendiliğinden göndermediği için CSRF saldırı yolu yok. |
| 7 | CORS | **GEÇTİ** | `test_cross_origin_requests_get_no_cors_permission`. Canlı: başka kökenden ön istek → izin başlığı yok | Web ile API aynı adresten sunulur (nginx), CORS ara katmanı yok. |
| 8 | HTTPS | **KISMİ** | Android yayın derlemesi yalnız HTTPS kabul eder (`src/main/res/xml/network_security_config.xml`) | Sistem yerel demo olarak HTTP ile çalışır; TLS sonlandırma ve HSTS yok (C-1). Teslim edilen APK debug derlemesidir ve HTTP'ye izin verir. |
| 9 | Çerez güvenliği | **UYGULANAMAZ** | Uygulama çerez kullanmıyor | — |
| 10 | Hız sınırlama | **KISMİ** | `tests/test_users_roles.py::test_repeated_wrong_passwords_are_throttled`. Canlı: sahte `X-Real-IP` başlıklarıyla 10 denemeden sonra 429. E-posta: kullanıcı başına dakikada 5 (`tests/test_email_notifications.py`) | Genel API hız sınırı yok. Sınırlar sunucu belleğinde tutulur, tek süreç içindir (C-3). |
| 11 | IDOR (başkasının kaydına erişim) | **GEÇTİ** | `tests/test_sync_push.py::test_sales_only_from_own_van_and_only_by_sales_users`; sayımda "yalnız kendi aracı" kuralı (`services/stock_count.py`) | Tek şirketli sistem: ofis rolleri kayıtları okuyabilir (tasarım gereği), yazma rolle sınırlıdır. Satış elemanı yalnız kendi aracının verisini çeker ve gönderir. |
| 12 | Gizli bilgi yönetimi | **KISMİ** | `.env` git dışında. gitleaks v8.21.2: 45 commit ve çalışma ağacı temiz | `.env` yoksa veritabanı şifresi bilinen yerel varsayılanla açılır (C-4). Demo profili kasıtlı olarak bilinen şifrelerle gelir. Demo dışı profillerde geçici şifre uygulanır (B-3). |
| 13 | Dosya yükleme | **UYGULANAMAZ** | Dosya yükleme ucu yok (`UploadFile` kullanılmıyor). "Faturadan doldur" yalnız metin alır | İstek gövdesi nginx'te 1 MB ile sınırlı: canlı denemede 2 MB → 413. |
| 14 | Genel hata yakalama | **GEÇTİ** | `test_unexpected_error_reveals_no_internal_detail` | Beklenmeyen hata `INTERNAL_ERROR` döner; iz, SQL ve iç ayrıntı sızmaz. |
| 15 | Güvenlik başlıkları | **GEÇTİ** | Canlı (nginx): CSP (`frame-ancestors 'none'`), `X-Frame-Options: DENY`, `nosniff`, `Referrer-Policy`, `Permissions-Policy`, `Server: nginx` (sürüm yok). API: `Cache-Control: no-store` (`test_api_responses_are_not_cached`) | HSTS, HTTPS olmadığı için yok. API portu artık yalnız bu bilgisayara açık; dışarıdan başlıksız erişim yok (B-1). |
| 16 | Denetim kayıtları | **GEÇTİ** | `tests/test_alarms_audit_mail.py`. Canlı: kaba kuvvet denemesinden sonra "Art arda hatalı giriş" alarmı açıldı ve yöneticiye `[AVATAR UYARI]` e-postası gitti (Mailpit) | Kimin ne zaman ne yaptığı: giriş hataları, kullanıcı işlemleri, alarm onayı, e-posta gönderimi. CSV dışa aktarılır. |
| 17 | Bağımlılık taraması | **KISMİ** | `npm audit`: 0 açık. `pip-audit 2.10.1 -r backend/requirements.txt`: 0 açık. CI ikisini her push'ta yineler | Android (Gradle) bağımlılıkları taranmadı (C-10). |
| 18 | Veritabanı güvenliği | **KISMİ** | DB portu dışarı açık değil (`docker compose config`). Stok defteri tetikleyicilerle korunur (UPDATE/DELETE engelli, ADR-008) | Uygulama kullanıcısı kendi veritabanında tam yetkili (en az yetki değil). Veri diskte şifresiz (C-5). |
| 19 | Yedekleme ve kurtarma | **GEÇTİ** | `sh scripts/yedek_denemesi.sh`: 38 tablo ve 2 tetikleyici geri yüklendi; döküm yedekle bire bir aynı çıktı. Reddedilenler: yarım yedek, `` avatar`; DROP… `` gibi veritabanı adı, onaysız canlı yükleme | Zamanlama (cron / Görev Zamanlayıcı) ve başka diske kopya kurulumu işletmeye kalır. Yedekler şifresiz (C-8). |
| 20 | CI/CD taraması | **DOĞRULANMADI** | `.github/workflows/ci.yml`: ruff, pytest (MySQL), yapay zekâ testleri, pip-audit, oxlint, vitest, derleme, npm audit, Android testleri + APK, gitleaks. Komutlar yerelde tek tek çalıştırıldı ve geçti | GitHub'da henüz hiç çalışmadı. İlk push'tan sonra Actions sekmesinde yeşil olduğu görülmeli. |

### A2. Hesap açma ve roller

"Üye ol" düğmesi bilerek yok. Bu, işletmenin kapalı iç sistemidir:

- Hesabı yönetici **Kullanıcılar** ekranından açar ve sistem geçici bir şifre verir. Kullanıcı ilk girişte kendi şifresini belirlemeden hiçbir işlem yapamaz (`PASSWORD_CHANGE_REQUIRED`).
- Sıfırdan kurulumda ilk yönetici komut satırından açılır. Şifre ekrana bir kez basılır:

  ```bash
  docker compose exec api python -m app.create_admin <kullanici_adi> "<Ad Soyad>"
  ```

Uygulama ve giriş ekranı tek, ama menü, düğmeler ve izin verilen uçlar role göre değişir:

| Rol | Ne görür |
|---|---|
| Yönetici | Her şeyi; ayrıca kullanıcılar, ürün ve fiyatlar, alarm ayarları, denetim günlüğü. |
| Depo, üretim, kalite, mağaza | Yalnız kendi işlerinin ekranlarını. |
| Satış elemanı | Yalnız telefon uygulamasını; web girişi reddedilir. |

### A3. Mobil (Android)

| Kontrol | Durum | Kanıt / not |
|---|---|---|
| Oturum belirtecinin saklanması | **GEÇTİ** | Android Keystore'da üretilen AES-256 anahtarıyla AES-GCM (`data/repo/TokenCipher.kt`). `TokenCipherTest` 4 test: geri açma, düz metin geçmemesi, değiştirilmiş içerik, başka anahtar. Emülatörde: güncellemeden önce düz `token` (43 karakter) vardı; güncellemeden sonra silindi. Girişten sonra yalnız `token_sifreli` (`v1:…`) var. Uygulama kapatılıp açılınca oturum sürdü; çökme yok. |
| Şifresiz HTTP | **KISMİ** | Yayın derlemesi yalnız HTTPS; debug derlemesi yerel demo için HTTP'ye izin verir (birleştirilmiş kaynaklarda doğrulandı). Teslim APK'sı debug'dur. |
| Yedeğe veri sızması | **GEÇTİ** | `android:allowBackup="false"` |
| Dışa açık bileşenler | **GEÇTİ** | Yalnız başlatıcı etkinlik `exported="true"`; servis, alıcı ve sağlayıcı yok. |
| Günlüğe gizli bilgi | **GEÇTİ** | HTTP günlük ara katmanı yok; tek `Log.w` bağlantı hatasını yazar. |
| Yerel veritabanı | **KISMİ** | Satış ve müşteri adları uygulamaya özel alanda, şifresiz (C-9). |
| Sertifika sabitleme, root tespiti | **UYGULANAMAZ** | Yerel ağ demosu; sabitlenecek sertifika yok. |

### A4. Web

| Kontrol | Durum | Kanıt / not |
|---|---|---|
| Yetkisiz ekran | **GEÇTİ** | `canOpenPage` (`web/src/lib/roles.ts`). Tarayıcıda `depo1` ile `/kullanicilar` → "Bu ekrana yetkiniz yok"; `/users` isteği hiç gitmedi; konsolda hata yok. |
| Satış elemanının web'e girmesi | **GEÇTİ** | `WEB_ROLES` girişte reddeder. Sunucu da bütün ofis uçlarında 403 verir (matris). |
| Oturum belirteci | **KISMİ** | `sessionStorage`'da (sekme kapanınca biter). XSS olursa okunabilir; CSP ve React kaçışı bu riski azaltır (C-2). |
| Tıklama hırsızlığı (clickjacking) | **GEÇTİ** | `X-Frame-Options: DENY` + `frame-ancestors 'none'` (canlı). |

### A5. API güvenlik matrisi

[api_yetki_matrisi.md](api_yetki_matrisi.md) koddan üretilir (`python -m app.access_matrix`). Uçlar şöyle dağılır:

| Uç türü | Sayı | Örnek |
|---|---|---|
| Herkese açık | 2 | `GET /health`, `POST /auth/login` |
| Giriş yeterli | 3 | Kendi hesabı ve çıkış |
| Rolle sınırlı | 90 | Diğer bütün uçlar |

Okuma uçları beş ofis rolüne açıktır; yazma uçları işin sahibine. Kullanıcı ve denetim kayıtlarını yalnız yönetici okur. Satış elemanı (telefon) yalnız eşitleme ve sayım uçlarına erişir.

### A6. E-posta

| Kontrol | Durum | Kanıt / not |
|---|---|---|
| Açık posta rölesi | **GEÇTİ** | Yalnız aktif kullanıcı, kayıtlı cari ya da `ALLOWED_EMAIL_DOMAINS`. Canlı: kayıtsız alıcı → 422. |
| Başlık enjeksiyonu | **GEÇTİ** | `test_mail_header_injection_is_neutralised`: konudaki satır sonu silinir, `Bcc` eklenemez; alıcıda CRLF → 422 (canlı da). |
| Gönderim sınırı | **GEÇTİ** | Kullanıcı başına dakikada 5; 6. gönderim 429 (test + 29 Ekim canlı denemesi). |
| Mailpit erişimi | **GEÇTİ** | Arayüz ve SMTP yalnız `127.0.0.1` (B-2). |
| SMTP şifreleme, SPF/DKIM | **KISMİ** | `SMTP_USER` doluysa STARTTLS + giriş; 465'te TLS. SPF, DKIM ve DMARC alan adı kurulumu işidir. |

### A7. Docker ve CI

| Kontrol | Durum | Kanıt / not |
|---|---|---|
| Portlar | **GEÇTİ** | DB yayımlanmıyor. API ve Mailpit yalnız `127.0.0.1` (`docker ps`: `127.0.0.1:18300->8000`). Web (nginx) yerel ağa açık, telefon bu adresle bağlanır (emülatörde doğrulandı: giriş 200, eşitleme 200). |
| Kapsayıcı kullanıcısı | **GEÇTİ** | API `appuser` (root değil). |
| İmaj sabitleme | **KISMİ** | Sürüm etiketiyle sabit (`mysql:8.4`, `axllent/mailpit:v1.32.0`); digest değil (C-7). |
| CI eylemleri | **DOĞRULANMADI** | Commit SHA'sıyla sabit (`actions/checkout` v7.0.1, `setup-node` v7.1.0, `setup-java` v6.1.0); izin `contents: read`, `persist-credentials: false`. GitHub'da çalışmadı. |

## B. Düzeltilen sorunlar

Her düzeltmeden sonra ilgili testler, en sonda bütün testler çalıştırıldı (bkz. "Son test çalıştırması").

| # | Önem | Sorun | Düzeltme (dosyalar) | Kanıt |
|---|---|---|---|---|
| B-1 | Yüksek | API portu bütün ağ arayüzlerine açıktı (`0.0.0.0`). Yerel ağdaki biri nginx'i atlayıp API'ye doğrudan gidebilirdi: güvenlik başlıkları olmadan ve `X-Real-IP`'yi kendisi yazarak adrese göre giriş sınırını aşarak (kullanıcı adına göre sınır yine geçerliydi). | `docker-compose.yml` (`${API_BIND:-127.0.0.1}`), `.env.example` (`API_BIND`). Telefon web portunu kullanır: `android/README.md`, `README.md` | `docker compose config` ve `docker ps` → `127.0.0.1`. Canlı: nginx üzerinden sahte IP başlıklarıyla 10 denemeden sonra 429. Emülatör nginx portundan giriş yaptı ve eşitledi. |
| B-2 | Yüksek | Mailpit arayüzü (8025) ve SMTP (1025) ağa açıktı. Yerel ağdaki herkes giden bütün e-postaları okuyabilirdi: CSV ekli raporlar, müşteri bilgisi, geri çağırma bildirimleri. | `docker-compose.yml` (iki port `127.0.0.1`) | `docker ps` → `127.0.0.1:8025`, `127.0.0.1:1025` |
| B-3 | Yüksek | `SEED_PROFILE=base` kurulumunda örnek kullanıcılar README'de yazan şifrelerle, değiştirme zorunluluğu olmadan açılıyordu. `none` profilinde ilk yöneticiyi açmanın güvenli yolu yoktu. | `backend/app/seed.py`: demo dışında geçici şifre; demo profilinde açılışta uyarı. `backend/app/create_admin.py` (yeni): tek kullanımlık şifreyle ilk yönetici. `backend/app/services/users.py` (`temporary_password`) | `test_seed_users_get_temporary_passwords_outside_demo` (giriş olur, `/stock` → `PASSWORD_CHANGE_REQUIRED`), `test_create_admin_command_prints_one_time_password` (aynı ad → 1, eksik argüman → 2) |
| B-4 | Orta | Telefon oturum belirteci SharedPreferences'ta düz metindi. | `android/.../data/repo/TokenCipher.kt` (yeni), `SessionStore.kt` (şifreli yazma, eski düz değeri taşıyıp silme, bellekte önbellek; Keystore çalışmazsa diske hiç yazmama) | `TokenCipherTest` (4). Emülatör kanıtı A3'te. |
| B-5 | Orta | Android'in her derlemesi şifresiz HTTP'ye izinliydi. | `src/main/res/xml/network_security_config.xml` (yalnız HTTPS), `src/debug/res/xml/network_security_config.xml` (yeni, demo için HTTP) | Birleştirilmiş kaynaklar: release `cleartextTrafficPermitted="false"`, debug `true` |
| B-6 | Orta | API yanıtlarında önbellek yasağı yoktu; raporlar, kullanıcı listesi ve CSV tarayıcıda ya da ara vekilde kalabilirdi. | `backend/app/main.py` (`/api/` altına `Cache-Control: no-store`) | `test_api_responses_are_not_cached`; canlı `no-store` |
| B-7 | Orta | Yetki yalnız seçilmiş uçlarda sınanıyordu; yeni uç eklenince unutulabilirdi. | `backend/app/access_matrix.py` (yeni), `backend/tests/test_access_matrix.py` (yeni), `docs/guvenlik/api_yetki_matrisi.md` | 9 test: 95 uç, 93 → 401, 223 → 403. Yetki hatası bulunmadı; yeni uçlar artık kendiliğinden sınanır. |
| B-8 | Orta | Yedekleme ve geri yükleme yöntemi yoktu. | `scripts/yedekle.sh`, `scripts/geri_yukle.sh`, `scripts/yedek_denemesi.sh` (yeni), `.gitignore` (`yedekler/`) | Bire bir eşleşme; yarım yedek, kötü veritabanı adı ve onaysız yükleme reddedildi. Canlı veriye dokunulmadı. |
| B-9 | Orta | CI ve otomatik güvenlik taraması yoktu. | `.github/workflows/ci.yml` (yeni) | Adımlar yerelde geçti; GitHub'da **doğrulanmadı**. |
| B-10 | Düşük | Rol dışı yönetici ekranı adres çubuğundan açılınca sayfa çerçevesiyle "Veri alınamadı" hata kutusu çıkıyordu (sunucu zaten reddediyordu). | `web/src/lib/roles.ts` (`canOpenPage`), `web/src/App.tsx` (403 sayfası), `web/src/i18n/en.ts`, `web/src/lib/roles.test.ts` (yeni) | 2 test; tarayıcıda doğrulandı. Alarm bağlantılarının açtığı ekranlar (ör. kalite → `/uretim/5`) açık kaldı. |
| B-11 | Kalite | 4 sunucu testi sabit tarih ("28 Ekim") yüzünden 31 Ekim'de düşüyordu: test alışı, kurulumdaki "dünkü" alıştan önceye düşüyordu. Jüri testleri 1 Kasım'dan sonra çalıştırsa da düşecekti. | `backend/tests/test_alarms_audit_mail.py`, `backend/tests/test_email_notifications.py` (`business_today()`) | 274/274 |
| B-12 | Düşük | gitleaks, test dosyasındaki uydurma bir değeri gizli anahtar sandı; CI'da yanlış alarm verecekti. | `android/.../TokenCipherTest.kt` | gitleaks: bulgu yok |

Ek olarak `scripts/guvenlik_denemesi.py` ve `.sh` eklendi. Videodaki saldırı denemesini tek komutla yineler (27 deneme; Docker ağı içinden, nginx üzerinden).

## C. Kalan riskler

Önem sırasıyla:

1. **HTTPS yok.**
   - Sistem yerel ağ demosu olarak HTTP ile çalışır.
   - Gerçek kurulumda nginx'in önüne TLS sonlandıran bir ters vekil (sertifikayla) ve HSTS gerekir.
   - Telefon yayın derlemesi o zaman `https://` adresiyle çalışır.
2. **Web belirteci `sessionStorage`'da.**
   - Bir XSS açığı olursa belirteç okunabilir. CSP `script-src 'self'` ve React kaçışı riski azaltır.
   - `HttpOnly` çerez + CSRF koruması daha güçlü olurdu. Bu bir mimari değişiklik olduğu için yapılmadı.
3. **Genel API hız sınırı yok.**
   - Yalnız giriş ve e-posta sınırlı. Sınırlar sunucu belleğinde, tek süreç içindir.
   - Birden çok sunucu sürecinde ortak bir depo gerekir (ör. Redis).
4. **Varsayılan veritabanı şifreleri.** `.env` yoksa bilinen yerel değerler kullanılır. DB portu dışarı açık olmadığı için risk yereldir, ama gerçek kurulumda `.env` zorunlu tutulmalı.
5. **Veritabanı kullanıcısı tam yetkili.**
   - Uygulama kullanıcısı kendi veritabanında her şeyi yapabilir (göçler de aynı kullanıcıyla çalışır).
   - Diskteki veri şifresiz.
6. **API imajında geliştirme araçları var** (pytest, ruff). Ayrı bir üretim imajı yok; kapsayıcı root değil.
7. **Kapsayıcı imajları digest ile değil, sürüm etiketiyle sabit.**
8. **Yedekler şifresiz.** Zamanlama ve başka diske kopyalama kurulumu işletmeye kalır.
9. **Telefonun yerel veritabanı şifresiz.** Uygulamaya özel alandadır ve yedeğe alınmaz.
10. **Android bağımlılıkları taranmadı.** Dependabot da yok.
11. **CI GitHub'da çalışmadı.** Android işi ilk çalıştırmada SDK 37 indirmek zorunda kalabilir; süre ve başarı görülmeli.
12. **MFA yok.** Şifre kuralı en az 8 karakter, harf ve rakam.
13. **Demo profili bilinen şifrelerle açılır.** Jüri demosu için kasıtlıdır. Açılış günlüğü uyarır; gerçek kurulumda `SEED_PROFILE=base` ya da `none` kullanılmalı.

## D. Video senaryosu: güvenlik bölümü (yaklaşık 2,5 dakika)

**Hazırlık:**

- Demo sistemi açık olsun: `docker compose up -d`.
- Tarayıcıda iki sekme olsun: web arayüzü ve Mailpit (http://localhost:8025).
- Bir terminal depo kökünde açık olsun.
- `guvenlik_denemesi.sh` çekimden en az 5 dakika önce çalıştırılmamış olsun.

| Süre | Ekran | Ne yapılır | Ne kanıtlar | Söylenecek cümle | Kanıt |
|---|---|---|---|---|---|
| 0:00–0:15 | Giriş ekranı | Ekranı göster; "Üye ol" yok | Kapalı sistem: hesabı yönetici açar | "Bu bir işletmenin iç sistemi; dışarıdan kayıt yok. Hesabı yönetici açar, geçici şifre verir; ilk girişte değiştirmeden hiçbir işlem yapılamaz." | `test_users_roles.py::test_new_user_must_change_password_before_working` |
| 0:15–0:40 | Web, `depo1` | Gir; menünün sadeleştiğini göster. Adres çubuğuna `/kullanicilar` yaz | Rol bazlı yetki, ekranda ve sunucuda | "Depo sorumlusu yalnız kendi işini görür. Yönetici ekranını adresten açmaya çalışsa bile 'yetkiniz yok' çıkar; sunucu da isteği reddeder." | `roles.test.ts`, `test_access_matrix.py` |
| 0:40–1:15 | Terminal | `sh scripts/guvenlik_denemesi.sh` çalıştır; çıktıyı kaydır | Saldırılar engellendi: girişsiz 401, rol dışı 403, SQL enjeksiyonu, açık posta rölesi, 2 MB gövde, kaba kuvvet | "Burada sisteme 27 saldırı isteği atıyoruz: sahte belirteç, başka rolün işi, SQL enjeksiyonu, dışarıya e-posta, kaba kuvvet. Hepsi reddedildi: 27'de 27." | Terminal çıktısı |
| 1:15–1:35 | Web, `yonetici` → Alarm merkezi; Mailpit | "Art arda hatalı giriş" alarmını göster; Mailpit'te `[AVATAR UYARI]` e-postasını aç | Saldırı fark edilir ve bildirilir | "Kaba kuvvet denemesi alarm açtı ve yöneticiye anında e-posta gitti." | Mailpit |
| 1:35–1:50 | Web → Denetim günlüğü | Hatalı giriş kayıtlarını süz | İz bırakır: kim, ne zaman, nereden | "Her deneme denetim günlüğünde; CSV olarak da alınır." | `test_alarms_audit_mail.py` |
| 1:50–2:10 | Editör: `docs/guvenlik/api_yetki_matrisi.md` | Tabloyu kaydır | Bütün API'nin yetkisi belgeli ve otomatik sınanıyor | "95 ucun her biri koddan okunup sınanıyor: girişsiz 93 deneme, rol dışı 223 deneme; hepsi reddedildi." | `test_access_matrix.py` |
| 2:10–2:30 | Terminal | `sh scripts/yedek_denemesi.sh` | Yedek gerçekten geri yükleniyor | "Yedek alıp ayrı bir veritabanına geri yüklüyoruz; içerik bire bir aynı. Çalışan sisteme dokunulmuyor." | Çıktıdaki "Aynı" satırı |
| 2:30–2:45 | Bu belgenin C bölümü | Kalan riskleri göster | Dürüstlük: kanıtlanmayanı iddia etmiyoruz | "Kanıtlayamadığımızı iddia etmiyoruz: HTTPS gerçek kurulumun işi, burada yerel demo çalışıyor." | Bu belge |

## E. Son karar

1. **Demo için hazır mı?**
   - Yerel demo için **evet**. Sıfırdan kurulum, kabul testleri (23/23), canlı saldırı denemesi (27/27) ve yedek denemesi bu kodla geçti.
   - Koşullar:
     - Demo profiliyle açılmalı.
     - Telefon web portuna (`http://<bilgisayar>:8080`) bağlanmalı.
     - CI, GitHub'a gönderildikten sonra kontrol edilmeli.
2. **En güçlü özellikler:**
   - Lot izleme ve geri çağırma tek işlemde (ileri izleme 0,02–0,04 sn).
   - Kuruşu kuruşuna maliyet ve parçalama dağıtımı.
   - Çevrimdışı çalışan telefon satışı ve güvenli eşitleme.
   - Alarm + e-posta + denetim günlüğü.
   - Bütün API'nin rol yetkisinin otomatik sınanması.
3. **En büyük eksikler:**
   - HTTPS yok.
   - CI hiç çalışmadı.
   - Web belirteci `sessionStorage`'da.
   - Genel hız sınırı yok.
   - Yapay zekâ verisi sentetik.
4. **Teslime kadar ilk 3 iyileştirme:**
   1. GitHub'a gönderip Actions'ın yeşil olduğunu görmek. Kırmızıysa düzeltmek.
   2. Videoya yukarıdaki güvenlik bölümünü eklemek.
   3. README'de gerçek kurulum için "HTTPS + `.env` + `SEED_PROFILE=base`" kontrol listesini öne çıkarmak.
5. **Öne çıkarılacaklar:**
   - Şartname senaryosu uçtan uca, kanıtlı.
   - 95 uç × 6 rol otomatik yetki testi.
   - Canlı saldırı denemesinin 27/27 reddedilmesi.
   - Saldırının alarm ve e-postayla bildirilmesi.
   - Yedeğin geri yüklenebildiğinin gösterilmesi.
   - Telefon belirtecinin Keystore ile şifrelenmesi.
6. **Yapılmaması gereken güvenlik iddiaları:**
   - "%100 güvenli", "hacklenemez".
   - "Uçtan uca şifreli" ya da "HTTPS ile çalışıyor".
   - "Sızma testinden geçti": yapılan, kendi yerel denememizdir; bağımsız bir test değildir.
   - "KVKK/GDPR uyumlu", "OWASP Top 10'un tamamı karşılanıyor", "üretime hazır".
   - "CI'da bütün testler geçiyor": GitHub'da çalışana kadar söylenmez.
   - "Telefondaki bütün veri şifreli": yalnız oturum belirteci şifreli.
   - "Yedekler otomatik alınıyor": betik var, zamanlama kurulumu yok.

## Son test çalıştırması (31 Ekim 2026)

| Bölüm | Komut | Sonuç |
|---|---|---|
| Sunucu | `docker compose run --rm --no-deps api pytest -q` | **274 geçti** |
| Biçim | `ruff format --check` + `ruff check` | Temiz |
| Yapay zekâ | `… api sh -c "cd /ml && pytest -q"` | 4 geçti |
| Web | `npm test`, `npx tsc -b`, `npm run lint` | 32 geçti; tip ve lint temiz |
| Android | `./gradlew testDebugUnitTest assembleDebug` | 26 geçti; APK derlendi |
| Kabul (sıfırdan kurulum) | `sh scripts/kabul_testleri.sh` | 23/23 |
| Canlı saldırı (demo, nginx) | `sh scripts/guvenlik_denemesi.sh` | 27/27 reddedildi |
| Yedek | `sh scripts/yedek_denemesi.sh` | Bire bir aynı |
| Bağımlılık | `npm audit --audit-level=moderate`, `pip-audit -r requirements.txt` | 0 açık, 0 açık |
| Gizli bilgi | gitleaks v8.21.2 (`git` ve `dir`) | Bulgu yok |
