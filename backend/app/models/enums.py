"""Durum ve tür değerleri (data_model.md). Değer = ad; veritabanında MySQL ENUM olarak tutulur."""

from enum import StrEnum


class UserRole(StrEnum):
    YONETICI = "YONETICI"
    SATIS = "SATIS"


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


class AlertKind(StrEnum):
    GERI_CAGIRMA_IHLALI = "GERI_CAGIRMA_IHLALI"


class AiModel(StrEnum):
    A_URETIM = "A_URETIM"
    B_PARCALAMA = "B_PARCALAMA"


class ForecastTarget(StrEnum):
    URETIM_EMRI = "URETIM_EMRI"
    PARCALAMA = "PARCALAMA"
