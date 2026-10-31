# Erişilebilirlik kontrol listesi

Tarih: 31 Ekim 2026. Hedef: web için WCAG 2.2 AA, telefon için Material 3 ilkeleri.

**Yöntem:**
- Renk karşıtlığı tema renklerinden hesaplandı.
- Klavye gezinmesi tarayıcıda denendi.
- Etiketler ve alt metinler kodda tarandı.

**Yapılmayanlar:**
- Otomatik tarama araçları (axe, Lighthouse) çalıştırılmadı; yeni bağımlılık gerektirir.
- Ekran okuyucuyla (NVDA, TalkBack) elle deneme yapılmadı.

Bu yüzden bu belge "uyumlu" değil, "aşağıdaki maddeler denetlendi" der.

## Renk karşıtlığı (WCAG 1.4.3: normal yazı en az 4,5:1)

| Öğe | Önce | Sonra | Durum |
|---|---|---|---|
| Gövde yazısı (#102a2a) / beyaz kart ve sayfa zemini | 15,1 / 13,8 | aynı | Geçti |
| İkincil yazı (#3f5655) / beyaz, tablo başlığı | 7,9 / 7,3 | aynı | Geçti |
| İpucu yazısı (#5f7372) / beyaz | 5,0 | aynı | Geçti |
| **Birincil düğme ve bağlantı** (beyaz ↔ turkuaz) | **3,74** (#0d9488) | **5,47** (#0f766e) | Düzeltildi |
| **Sol menü yazısı** (geçişin en açık yeri) | **3,20** | **5,00** | Düzeltildi (geçiş #115e59 → #0f766e → #0e7490, yazı %95 beyaz) |
| **Sol menü grup başlığı** | **2,48** | **4,81** | Düzeltildi (%92 beyaz) |
| Seçili ve üzerine gelinen menü satırı | 3,41 | 7,58 / 6,65 | Düzeltildi (satır açılmak yerine koyulaşır) |
| Uyarı, hata, başarı yazıları (yumuşak zeminde) | 4,58 / 5,62 / 4,58 | aynı | Geçti |
| **Telefon üst çubuk ve düğmeler** (beyaz ↔ turkuaz) | **3,74** | **5,47** | Düzeltildi (`Brand.Primary` = #0f766e) |
| Telefon ikincil yazı (#4b5563) / zemin | 6,89 | aynı | Geçti |

Hesap betiği WCAG'ın göreli parlaklık formülünü kullanır; saydam renkler zeminle karıştırılarak hesaplanır.

## Diğer maddeler

| Madde | Sonuç |
|---|---|
| Sayfa dili (3.1.1) | `<html lang="tr">`; İngilizce seçilince `lang="en"` olur (`main.tsx`). |
| Yalnız ikonlu düğmelerin adı (4.1.2) | Kodda bütün yalnız-ikon düğmeler tarandı: etiketsiz 0. Telefonda alt menü ikonları yazılı etiketin yanında; diğer ikonlarda açıklama var. |
| Resimlerde alt metin (1.1.1) | `<img>` kullanan her yerde `alt` var; grafiklerde ayrıca "Tablo" görünümü var. |
| Klavye odağı görünür (2.4.7) ve odak çizgisi karşıtlığı (1.4.11, en az 3:1) | Tarayıcıda Tab ile denendi: odak görünüyor. Sol menüde varsayılan turkuaz çizgi koyu zeminde ~1,7:1 kalıyordu → beyaz çizgi. |
| Dokunma/tıklama hedefi (2.5.8, en az 24×24 px) | Web denetimleri 38 px yükseklikte (`controlHeight`). Telefonda Material 3 düğmeleri en az 48 dp; tıklanabilir kartlar en az 48 dp. |
| Yalnız renge dayanmayan durum (1.4.1) | Lot durumu, son kullanma ve gönderim durumu renkli rozet **ve** yazıyla ("Satışa kapalı", "Gönderildi" vb.). |
| Hata mesajları (3.3.1) | Form hataları alanın yanında, Türkçe ve ne yapılacağını söyleyerek; sunucu hatası iş diliyle. |
| Ekran büyütme | Web 390 px telefon genişliğinde tek sütun (galeri 38, 39, 52). |
