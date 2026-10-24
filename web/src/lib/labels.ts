// API'deki durum değerlerinin ekrandaki Türkçe adları. Record tipi, yeni bir değer eklenince
// burada eksik kalırsa derlemeyi durdurur.

import type {
  AllocationMethod,
  CuttingStatus,
  LinkProcess,
  LotOrigin,
  LotStatus,
  MovementType,
  OrderStatus,
  ProductKind,
  PurchaseCostKind,
  RecipeLineType,
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
  DIS_URETICI: 'Dış üretici deposu',
  ARAC: 'Araç deposu',
}

export const LOT_STATUS: Record<LotStatus, string> = { AKTIF: 'Aktif', BLOKE: 'Bloke' }

export const LOT_ORIGIN: Record<LotOrigin, string> = {
  ALIS: 'Alış',
  URETIM: 'Dış üretim',
  PARCALAMA: 'Parçalama',
  YENIDEN_ISLEME: 'Yeniden işleme',
}

export const LINK_PROCESS: Record<LinkProcess, string> = {
  URETIM: 'Dış üretim',
  PARCALAMA: 'Parçalama',
  YENIDEN_ISLEME: 'Yeniden işleme',
}

export const MOVEMENT_TYPE: Record<MovementType, string> = {
  ALIS_GIRIS: 'Alış girişi',
  TRANSFER_CIKIS: 'Transfer çıkışı',
  TRANSFER_GIRIS: 'Transfer girişi',
  URETIM_TUKETIM: 'Üretimde tüketim',
  URETIM_GIRIS: 'Üretimden giriş',
  PARCALAMA_TUKETIM: 'Parçalamada tüketim',
  PARCALAMA_GIRIS: 'Parçalamadan giriş',
  SATIS: 'Satış',
  IADE_GIRIS: 'İade girişi',
  FIRE: 'Fire',
  TERS_KAYIT: 'Ters kayıt',
}

export const ORDER_STATUS: Record<OrderStatus, string> = {
  TASLAK: 'Taslak',
  SEVK_EDILDI: 'Sevk edildi',
  TAMAMLANDI: 'Tamamlandı',
  IPTAL: 'İptal',
}

export const TRANSFER_REASON: Record<TransferReason, string> = {
  ARAC_YUKLEME: 'Araca yükleme',
  DIS_URETIM_SEVK: 'Dış üretime sevk',
  DIS_URETIM_IADE: 'Dış üretimden iade',
  DIGER: 'Diğer',
}

export const PURCHASE_COST_KIND: Record<PurchaseCostKind, string> = {
  NAKLIYE: 'Nakliye',
  KESIM: 'Kesim',
  VETERINER: 'Veteriner',
  DIGER: 'Diğer',
}

export const ALLOCATION_METHOD: Record<AllocationMethod, string> = {
  MIKTAR: 'Miktar ağırlıklı',
  DEGER: 'Değer ağırlıklı',
}

export const CUTTING_STATUS: Record<CuttingStatus, string> = { TASLAK: 'Taslak', ONAYLANDI: 'Onaylandı' }

export const RECIPE_LINE_TYPE: Record<RecipeLineType, string> = {
  PARCA: 'Parça',
  YAN_URUN: 'Yan ürün',
  FIRE: 'Fire',
}

export const SPECIES: Record<Species, string> = { KUZU: 'Kuzu', KOYUN: 'Koyun', KECI: 'Keçi' }

/** Select bileşeni için { value, label } listesi. */
export function options<K extends string>(labels: Record<K, string>): { value: K; label: string }[] {
  return (Object.keys(labels) as K[]).map((value) => ({ value, label: labels[value] }))
}
