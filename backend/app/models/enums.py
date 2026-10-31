"""Durum ve tür değerleri (data_model.md). Değer = ad; veritabanında MySQL ENUM olarak tutulur."""

from enum import StrEnum


class UserRole(StrEnum):
    """Orta ölçekli işletme: her çalışan yalnız kendi işinin ekranlarını görür."""

    YONETICI = "YONETICI"  # her şey, kullanıcı ve ana veri yönetimi
    DEPO = "DEPO"  # mal kabul, stok, transfer, fire ve sayım
    URETIM = "URETIM"  # fason üretim, parçalama, yeniden işleme
    KALITE = "KALITE"  # izleme, geri çağırma, uyarılar
    MAGAZA = "MAGAZA"  # dükkân satışı, iade, gün sonu
    SATIS = "SATIS"  # saha satışı (yalnız Android)


class ProductKind(StrEnum):
    HAMMADDE = "HAMMADDE"
    MAMUL = "MAMUL"
    PARCA = "PARCA"
    YAN_URUN = "YAN_URUN"


class BaseUnit(StrEnum):
    KG = "KG"
    ADET = "ADET"


class WarehouseKind(StrEnum):
    ANA = "ANA"
    DIS_URETICI = "DIS_URETICI"
    ARAC = "ARAC"


class LotOrigin(StrEnum):
    ALIS = "ALIS"
    URETIM = "URETIM"
    PARCALAMA = "PARCALAMA"
    YENIDEN_ISLEME = "YENIDEN_ISLEME"


class LotStatus(StrEnum):
    AKTIF = "AKTIF"
    BLOKE = "BLOKE"


class LinkProcess(StrEnum):
    URETIM = "URETIM"
    PARCALAMA = "PARCALAMA"
    YENIDEN_ISLEME = "YENIDEN_ISLEME"


class MovementType(StrEnum):
    ALIS_GIRIS = "ALIS_GIRIS"
    TRANSFER_CIKIS = "TRANSFER_CIKIS"
    TRANSFER_GIRIS = "TRANSFER_GIRIS"
    URETIM_TUKETIM = "URETIM_TUKETIM"
    URETIM_GIRIS = "URETIM_GIRIS"
    PARCALAMA_TUKETIM = "PARCALAMA_TUKETIM"
    PARCALAMA_GIRIS = "PARCALAMA_GIRIS"
    SATIS = "SATIS"
    IADE_GIRIS = "IADE_GIRIS"
    FIRE = "FIRE"
    TERS_KAYIT = "TERS_KAYIT"


class DocType(StrEnum):
    ALIS = "ALIS"
    TRANSFER = "TRANSFER"
    URETIM = "URETIM"
    PARCALAMA = "PARCALAMA"
    SATIS = "SATIS"
    IADE = "IADE"
    DUZELTME = "DUZELTME"


class PurchaseCostKind(StrEnum):
    NAKLIYE = "NAKLIYE"
    KESIM = "KESIM"
    VETERINER = "VETERINER"
    DIGER = "DIGER"


class ProductionKind(StrEnum):
    DIS_URETIM = "DIS_URETIM"
    YENIDEN_ISLEME = "YENIDEN_ISLEME"


class ProductionStatus(StrEnum):
    TASLAK = "TASLAK"
    SEVK_EDILDI = "SEVK_EDILDI"
    TAMAMLANDI = "TAMAMLANDI"
    IPTAL = "IPTAL"


class Species(StrEnum):
    KUZU = "KUZU"
    KOYUN = "KOYUN"
    KECI = "KECI"


class AllocationMethod(StrEnum):
    MIKTAR = "MIKTAR"
    DEGER = "DEGER"


class RecipeLineType(StrEnum):
    PARCA = "PARCA"
    YAN_URUN = "YAN_URUN"
    FIRE = "FIRE"


class CuttingStatus(StrEnum):
    TASLAK = "TASLAK"
    ONAYLANDI = "ONAYLANDI"


class SaleChannel(StrEnum):
    ANDROID = "ANDROID"
    WEB = "WEB"


class TransferReason(StrEnum):
    ARAC_YUKLEME = "ARAC_YUKLEME"
    DIS_URETIM_SEVK = "DIS_URETIM_SEVK"
    DIS_URETIM_IADE = "DIS_URETIM_IADE"
    DIGER = "DIGER"


class AdjustmentKind(StrEnum):
    FIRE = "FIRE"


class RecallStatus(StrEnum):
    ACIK = "ACIK"
    KAPANDI = "KAPANDI"


class RecallResolution(StrEnum):
    IMHA = "IMHA"
    SERBEST = "SERBEST"


class ContactOutcome(StrEnum):
    """Geri çağırmada müşteriyle iletişimin sonucu (müşteri başına son kayıt durumu gösterir)."""

    ULASILDI = "ULASILDI"  # ulaşıldı, bilgilendirildi; ürün ayrılacak/iade edilecek
    ULASILAMADI = "ULASILAMADI"  # aranacak
    URUN_KALMADI = "URUN_KALMADI"  # ulaşıldı; elde ürün kalmamış (tüketilmiş ya da satılmış)


class AlertKind(StrEnum):
    GERI_CAGIRMA_IHLALI = "GERI_CAGIRMA_IHLALI"
    SKT_IHLALI = "SKT_IHLALI"  # son kullanma tarihi geçmiş parti satıldı (çevrimdışı)
    GERI_CAGIRMA = "GERI_CAGIRMA"  # geri çağırma başlatıldı
    BLOKE_SATIS_DENEMESI = "BLOKE_SATIS_DENEMESI"  # mağazada bloke lot satılmak istendi (reddedildi)
    BLOKE_STOK = "BLOKE_STOK"  # bloke lotta hâlâ stok var
    VERIM_SAPMASI = "VERIM_SAPMASI"  # üretim/parçalama verimi beklenenden çok farklı (z-skoru)
    FIYAT_ARTISI = "FIYAT_ARTISI"  # alış fiyatı bir önceki alışa göre eşikten fazla arttı
    HATALI_GIRIS = "HATALI_GIRIS"  # art arda hatalı giriş denemesi
    SKT_YAKLASIYOR = "SKT_YAKLASIYOR"  # elimizdeki lotun son kullanma tarihi yaklaştı ya da geçti
    SAYIM_FARKI = "SAYIM_FARKI"  # depo/araç sayımında sistemle sayılan farklı


class Severity(StrEnum):
    """Alarm ve denetim kaydı önemi."""

    BILGI = "BILGI"
    UYARI = "UYARI"
    KRITIK = "KRITIK"


class MailStatus(StrEnum):
    KUYRUKTA = "KUYRUKTA"  # e-posta sunucusu tanımlı değil ya da henüz gönderilmedi
    GONDERILDI = "GONDERILDI"
    HATA = "HATA"  # gönderim denendi, başarısız (yeniden denenebilir)


class PaymentMethod(StrEnum):
    NAKIT = "NAKIT"
    KART = "KART"
    HAVALE = "HAVALE"
    VERESIYE = "VERESIYE"


class AiModel(StrEnum):
    A_URETIM = "A_URETIM"
    B_PARCALAMA = "B_PARCALAMA"


class ForecastTarget(StrEnum):
    URETIM_EMRI = "URETIM_EMRI"
    PARCALAMA = "PARCALAMA"
