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

export const PRODUCT_KIND: Record<ProductKind, string> = {
  HAMMADDE: 'Hammadde',
  MAMUL: 'Mamul',
  PARCA: 'Parça',
  YAN_URUN: 'Yan ürün',
}

export const WAREHOUSE_KIND: Record<WarehouseKind, string> = {
  ANA: 'Ana depo',
  DIS_URETICI: 'Fasoncu deposu',
  ARAC: 'Satış aracı',
}

export const LOT_STATUS: Record<LotStatus, string> = { AKTIF: 'Satışa açık', BLOKE: 'Satışa kapalı' }

export const LOT_ORIGIN: Record<LotOrigin, string> = {
  ALIS: 'Alış',
  URETIM: 'Fason üretim',
  PARCALAMA: 'Parçalama',
  YENIDEN_ISLEME: 'Yeniden işleme',
}

export const LINK_PROCESS: Record<LinkProcess, string> = {
  URETIM: 'Fason üretim',
  PARCALAMA: 'Parçalama',
  YENIDEN_ISLEME: 'Yeniden işleme',
}

export const MOVEMENT_TYPE: Record<MovementType, string> = {
  ALIS_GIRIS: 'Mal kabul',
  TRANSFER_CIKIS: 'Depodan çıkış (aktarma)',
  TRANSFER_GIRIS: 'Depoya giriş (aktarma)',
  URETIM_TUKETIM: 'Üretimde tüketim',
  URETIM_GIRIS: 'Üretimden giriş',
  PARCALAMA_TUKETIM: 'Parçalamada tüketim',
  PARCALAMA_GIRIS: 'Parçalamadan giriş',
  SATIS: 'Satış',
  IADE_GIRIS: 'Müşteri iadesi',
  FIRE: 'Fire / imha',
  TERS_KAYIT: 'Düzeltme (geri alma)',
}

export const ORDER_STATUS: Record<OrderStatus, string> = {
  TASLAK: 'Taslak',
  SEVK_EDILDI: 'Sevk edildi',
  TAMAMLANDI: 'Tamamlandı',
  IPTAL: 'İptal',
}

export const TRANSFER_REASON: Record<TransferReason, string> = {
  ARAC_YUKLEME: 'Araca yükleme',
  DIS_URETIM_SEVK: 'Fasoncuya sevk',
  DIS_URETIM_IADE: 'Fasoncudan iade',
  DIGER: 'Depolar arası',
}

export const PURCHASE_COST_KIND: Record<PurchaseCostKind, string> = {
  NAKLIYE: 'Nakliye',
  KESIM: 'Kesim',
  VETERINER: 'Veteriner',
  DIGER: 'Diğer',
}

export const ALLOCATION_METHOD: Record<AllocationMethod, string> = {
  MIKTAR: 'Kiloya göre',
  DEGER: 'Piyasa değerine göre',
}

export const CUTTING_STATUS: Record<CuttingStatus, string> = { TASLAK: 'Taslak', ONAYLANDI: 'Onaylandı' }

export const RECIPE_LINE_TYPE: Record<RecipeLineType, string> = {
  PARCA: 'Parça',
  YAN_URUN: 'Yan ürün',
  FIRE: 'Fire',
}

export const SPECIES: Record<Species, string> = { KUZU: 'Kuzu', KOYUN: 'Koyun', KECI: 'Keçi' }

export const ONWARD_STATUS: Record<OnwardStatus, string> = {
  KAYITLI: 'Müşterinin dağıttığı yerler kayıtlı',
  KISMEN: 'Bir kısmının nereye gittiği biliniyor',
  BILINMIYOR: 'Müşteriden sonrası bilinmiyor',
}

export const RECALL_STATUS: Record<RecallStatus, string> = { ACIK: 'Açık', KAPANDI: 'Kapandı' }

export const RECALL_RESOLUTION: Record<RecallResolution, string> = {
  IMHA: 'İmha et (elimizdeki mal düşülür, lotlar satışa kapalı kalır)',
  SERBEST: 'Sorun yok, satışa aç (lotlar yeniden satılabilir)',
}

export const SALE_CHANNEL: Record<SaleChannel, string> = { ANDROID: 'Araç (telefon)', WEB: 'Mağaza' }

export const PAYMENT_METHOD: Record<PaymentMethod, string> = {
  NAKIT: 'Nakit',
  KART: 'Kredi kartı',
  HAVALE: 'Havale / EFT',
  VERESIYE: 'Veresiye (açık hesap)',
}

/** Gün sonu toplamlarındaki ödeme anahtarı; eski uygulama sürümünden gelen satışta ödeme türü yoktur. */
export function paymentLabel(key: string): string {
  return key in PAYMENT_METHOD ? PAYMENT_METHOD[key as PaymentMethod] : 'Belirtilmedi (eski uygulama)'
}

/** Select bileşeni için { value, label } listesi. */
export function options<K extends string>(labels: Record<K, string>): { value: K; label: string }[] {
  return (Object.keys(labels) as K[]).map((value) => ({ value, label: labels[value] }))
}
