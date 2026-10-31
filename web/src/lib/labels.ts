// API'deki durum değerlerinin ekrandaki Türkçe adları. Record tipi, yeni bir değer eklenince
// burada eksik kalırsa derlemeyi durdurur.

import type {
  AlertKind,
  AllocationMethod,
  CuttingStatus,
  LinkProcess,
  LotOrigin,
  LotStatus,
  MailStatus,
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
  Severity,
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

export const SEVERITY: Record<Severity, string> = { BILGI: t('Bilgi'), UYARI: t('Uyarı'), KRITIK: t('Kritik') }

export const ALERT_KIND: Record<AlertKind, string> = {
  GERI_CAGIRMA_IHLALI: t('Geri çağrılmış ürün satıldı'),
  SKT_IHLALI: t('SKT’si geçmiş ürün satıldı'),
  GERI_CAGIRMA: t('Geri çağırma başlatıldı'),
  BLOKE_SATIS_DENEMESI: t('Bloke lot satış denemesi'),
  BLOKE_STOK: t('Bloke lotta stok var'),
  VERIM_SAPMASI: t('Verim sapması'),
  FIYAT_ARTISI: t('Alış fiyatı artışı'),
  HATALI_GIRIS: t('Art arda hatalı giriş'),
  SKT_YAKLASIYOR: t('Son kullanma tarihi yaklaşan lot'),
  SAYIM_FARKI: t('Sayım farkı'),
}

/** Her alarm türünün ne zaman açıldığı (alarm ayarları ve kişisel e-posta bildirimi ekranı). */
export const ALERT_WHEN: Record<AlertKind, string> = {
  GERI_CAGIRMA_IHLALI: t('Telefondan çevrimdışı satışta bloke lot satılmışsa.'),
  SKT_IHLALI: t('Telefondan çevrimdışı satışta son kullanma tarihi geçmiş lot satılmışsa.'),
  GERI_CAGIRMA: t('Geri çağırma başlatılınca.'),
  BLOKE_SATIS_DENEMESI: t('Mağazada bloke lot satılmak istenince (satış engellenir).'),
  BLOKE_STOK: t('Geri çağrılmış (bloke) lotta hâlâ stok varsa.'),
  VERIM_SAPMASI: t('Üretim veriminin ya da parçalama firesinin model beklentisinden sapması z-skoru eşiğini geçince.'),
  FIYAT_ARTISI: t('Bir ürünün alış fiyatı bir önceki alışa göre eşikten fazla artınca.'),
  HATALI_GIRIS: t('Bir hesaba art arda eşik kadar hatalı giriş denenince.'),
  SKT_YAKLASIYOR: t('Elimizdeki satışa açık lotun son kullanma tarihi 3 gün içinde ya da geçmişse.'),
  SAYIM_FARKI: t('Depo ya da araç sayımında sistemle sayılan farklıysa.'),
}

export const MAIL_STATUS: Record<MailStatus, string> = {
  KUYRUKTA: t('Kuyrukta'),
  GONDERILDI: t('Gönderildi'),
  HATA: t('Gönderilemedi'),
}

/** Denetim günlüğündeki işlem kodlarının adları (bilinmeyen kod olduğu gibi gösterilir). */
export const AUDIT_ACTION: Record<string, string> = {
  GIRIS: t('Giriş'),
  GIRIS_HATASI: t('Hatalı giriş'),
  GIRIS_ENGELLENDI: t('Giriş engellendi'),
  CIKIS: t('Çıkış'),
  SIFRE_DEGISTI: t('Şifre değişti'),
  OTURUMLAR_KAPATILDI: t('Diğer oturumlar kapatıldı'),
  SIFRE_SIFIRLANDI: t('Şifre sıfırlandı'),
  KULLANICI: t('Kullanıcı'),
  MAL_KABUL: t('Mal kabul'),
  URETIM_EMRI: t('Üretim emri'),
  URETIM_SEVK: t('Üretim sevki'),
  URETIM_TAMAM: t('Üretim tamamlandı'),
  URETIM_IPTAL: t('Üretim iptal'),
  YENIDEN_ISLEME: t('Yeniden işleme'),
  PARCALAMA: t('Parçalama'),
  PARCALAMA_ONAY: t('Parçalama onayı'),
  RECETE: t('Reçete'),
  SATIS: t('Satış'),
  SATIS_SENKRON: t('Telefon satışı'),
  IADE: t('İade'),
  DAGITIM: t('İkinci kademe dağıtım'),
  FIRE: t('Fire / düzeltme'),
  TERS_KAYIT: t('Ters kayıt'),
  TRANSFER: t('Transfer'),
  SAYIM: t('Sayım'),
  GERI_CAGIRMA: t('Geri çağırma'),
  GERI_CAGIRMA_KAPANDI: t('Geri çağırma kapandı'),
  ALARM: t('Alarm'),
  ALARM_OKUNDU: t('Alarm okundu'),
  KURAL: t('Alarm kuralları'),
  AYAR: t('Ayar'),
  EPOSTA: t('E-posta'),
  RAPOR_EPOSTA: t('Rapor e-postası'),
  ABONELIK: t('E-posta aboneliği'),
  URUN: t('Ürün'),
  CARI: t('Cari'),
}

/** Gün sonu toplamlarındaki ödeme anahtarı; eski uygulama sürümünden gelen satışta ödeme türü yoktur. */
export function paymentLabel(key: string): string {
  return key in PAYMENT_METHOD ? PAYMENT_METHOD[key as PaymentMethod] : t('Belirtilmedi (eski uygulama)')
}

/** Select bileşeni için { value, label } listesi. */
export function options<K extends string>(labels: Record<K, string>): { value: K; label: string }[] {
  return (Object.keys(labels) as K[]).map((value) => ({ value, label: labels[value] }))
}
