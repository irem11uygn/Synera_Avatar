// API'deki durum değerlerinin ekrandaki Türkçe adları. Record tipi, yeni bir değer eklenince
// burada eksik kalırsa derlemeyi durdurur.

import type {
  AllocationMethod,
  CuttingStatus,
  LinkProcess,
  LotOrigin,
  LotStatus,
  MovementType,
  OnwardStatus,
  OrderStatus,
  PaymentMethod,
  ProductKind,
  PurchaseCostKind,
  RecallResolution,
  RecallStatus,
  RecipeLineType,
  SaleChannel,
  Species,
  TransferReason,
  WarehouseKind,
} from '../api/types'
import { t } from './i18n'

export const PRODUCT_KIND: Record<ProductKind, string> = {
  HAMMADDE: t('Hammadde'),
  MAMUL: t('Mamul'),
  PARCA: t('Parça'),
  YAN_URUN: t('Yan ürün'),
}

export const WAREHOUSE_KIND: Record<WarehouseKind, string> = {
  ANA: t('Ana depo'),
  DIS_URETICI: t('Fasoncu deposu'),
  ARAC: t('Satış aracı'),
}

export const LOT_STATUS: Record<LotStatus, string> = { AKTIF: t('Satışa açık'), BLOKE: t('Satışa kapalı') }

export const LOT_ORIGIN: Record<LotOrigin, string> = {
  ALIS: t('Alış'),
  URETIM: t('Fason üretim'),
  PARCALAMA: t('Parçalama'),
  YENIDEN_ISLEME: t('Yeniden işleme'),
}

export const LINK_PROCESS: Record<LinkProcess, string> = {
  URETIM: t('Fason üretim'),
  PARCALAMA: t('Parçalama'),
  YENIDEN_ISLEME: t('Yeniden işleme'),
}

export const MOVEMENT_TYPE: Record<MovementType, string> = {
  ALIS_GIRIS: t('Mal kabul'),
  TRANSFER_CIKIS: t('Depodan çıkış (aktarma)'),
  TRANSFER_GIRIS: t('Depoya giriş (aktarma)'),
  URETIM_TUKETIM: t('Üretimde tüketim'),
  URETIM_GIRIS: t('Üretimden giriş'),
  PARCALAMA_TUKETIM: t('Parçalamada tüketim'),
  PARCALAMA_GIRIS: t('Parçalamadan giriş'),
  SATIS: t('Satış'),
  IADE_GIRIS: t('Müşteri iadesi'),
  FIRE: t('Fire / imha'),
  TERS_KAYIT: t('Düzeltme (geri alma)'),
}

export const ORDER_STATUS: Record<OrderStatus, string> = {
  TASLAK: t('Taslak'),
  SEVK_EDILDI: t('Sevk edildi'),
  TAMAMLANDI: t('Tamamlandı'),
  IPTAL: t('İptal'),
}

export const TRANSFER_REASON: Record<TransferReason, string> = {
  ARAC_YUKLEME: t('Araca yükleme'),
  DIS_URETIM_SEVK: t('Fasoncuya sevk'),
  DIS_URETIM_IADE: t('Fasoncudan iade'),
  DIGER: t('Depolar arası'),
}

export const PURCHASE_COST_KIND: Record<PurchaseCostKind, string> = {
  NAKLIYE: t('Nakliye'),
  KESIM: t('Kesim'),
  VETERINER: t('Veteriner'),
  DIGER: t('Diğer'),
}

export const ALLOCATION_METHOD: Record<AllocationMethod, string> = {
  MIKTAR: t('Kiloya göre'),
  DEGER: t('Piyasa değerine göre'),
}

export const CUTTING_STATUS: Record<CuttingStatus, string> = { TASLAK: t('Taslak'), ONAYLANDI: t('Onaylandı') }

export const RECIPE_LINE_TYPE: Record<RecipeLineType, string> = {
  PARCA: t('Parça'),
  YAN_URUN: t('Yan ürün'),
  FIRE: t('Fire'),
}

export const SPECIES: Record<Species, string> = { KUZU: t('Kuzu'), KOYUN: t('Koyun'), KECI: t('Keçi') }

export const ONWARD_STATUS: Record<OnwardStatus, string> = {
  KAYITLI: t('Müşterinin dağıttığı yerler kayıtlı'),
  KISMEN: t('Bir kısmının nereye gittiği biliniyor'),
  BILINMIYOR: t('Müşteriden sonrası bilinmiyor'),
}

export const RECALL_STATUS: Record<RecallStatus, string> = { ACIK: t('Açık'), KAPANDI: t('Kapandı') }

export const RECALL_RESOLUTION: Record<RecallResolution, string> = {
  IMHA: t('İmha et (elimizdeki mal düşülür, lotlar satışa kapalı kalır)'),
  SERBEST: t('Sorun yok, satışa aç (lotlar yeniden satılabilir)'),
}

export const SALE_CHANNEL: Record<SaleChannel, string> = { ANDROID: t('Araç (telefon)'), WEB: t('Mağaza') }

export const PAYMENT_METHOD: Record<PaymentMethod, string> = {
  NAKIT: t('Nakit'),
  KART: t('Kredi kartı'),
  HAVALE: t('Havale / EFT'),
  VERESIYE: t('Veresiye (açık hesap)'),
}

/** Gün sonu toplamlarındaki ödeme anahtarı; eski uygulama sürümünden gelen satışta ödeme türü yoktur. */
export function paymentLabel(key: string): string {
  return key in PAYMENT_METHOD ? PAYMENT_METHOD[key as PaymentMethod] : t('Belirtilmedi (eski uygulama)')
}

/** Select bileşeni için { value, label } listesi. */
export function options<K extends string>(labels: Record<K, string>): { value: K; label: string }[] {
  return (Object.keys(labels) as K[]).map((value) => ({ value, label: labels[value] }))
}
