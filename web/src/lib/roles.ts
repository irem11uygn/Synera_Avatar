// Roller ve yetkiler. Sunucu her isteği kendisi denetler (app/api/deps.py); burada yalnız
// kullanıcıya yapamayacağı işin düğmesini göstermemek için aynı kurallar tekrarlanır.

import type { UserRole } from '../api/types'
import { t } from './i18n'

export const ROLE: Record<UserRole, string> = {
  YONETICI: t('Yönetici'),
  DEPO: t('Depo sorumlusu'),
  URETIM: t('Üretim sorumlusu'),
  KALITE: t('Kalite sorumlusu'),
  MAGAZA: t('Mağaza / kasa'),
  SATIS: t('Satış elemanı (araç)'),
}

export const ROLE_HELP: Record<UserRole, string> = {
  YONETICI: t('Her ekranı görür ve her işlemi yapar; kullanıcıları yönetir.'),
  DEPO: t('Mal kabul, stok, sayım, araca yükleme ve fire.'),
  URETIM: t('Fason üretim, parçalama ve yeniden işleme.'),
  KALITE: t('Lot izleme, geri çağırma, tatbikat ve uyarılar.'),
  MAGAZA: t('Mağaza satışı, iade ve gün sonu.'),
  SATIS: t('Yalnız telefon uygulaması: araçtan satış ve araç sayımı.'),
}

export type Action =
  | 'products'
  | 'partners'
  | 'stock'
  | 'production'
  | 'quality'
  | 'store'
  | 'returns'
  | 'dayEnd'
  | 'count'
  | 'users'

const ALLOWED: Record<Action, UserRole[]> = {
  products: ['YONETICI'],
  partners: ['YONETICI', 'DEPO', 'MAGAZA'],
  stock: ['YONETICI', 'DEPO'], // mal kabul, transfer, fire, düzeltme
  production: ['YONETICI', 'URETIM'],
  quality: ['YONETICI', 'KALITE'], // geri çağırma, uyarı onayı
  store: ['YONETICI', 'MAGAZA'], // mağaza satışı
  returns: ['YONETICI', 'MAGAZA', 'KALITE'],
  dayEnd: ['YONETICI', 'MAGAZA'],
  count: ['YONETICI', 'DEPO'],
  users: ['YONETICI'],
}

export function can(role: UserRole, action: Action): boolean {
  return ALLOWED[action].includes(role)
}

export const WEB_ROLES: UserRole[] = ['YONETICI', 'DEPO', 'URETIM', 'KALITE', 'MAGAZA']

// Verisini sunucunun yalnız bazı rollere verdiği ekranlar (docs/guvenlik/api_yetki_matrisi.md). Adres elle
// yazılınca hata kutusu yerine "yetkiniz yok" sayfası çıkar. Diğer ekranları her ofis rolü okuyabilir
// (alarm bağlantıları da oraya gider); yapamayacağı işin düğmesi can() ile gizlenir.
const PAGE_ROLES: Record<string, UserRole[]> = {
  '/kullanicilar': ['YONETICI'],
  '/denetim': ['YONETICI'],
  '/alarm-ayarlari': ['YONETICI'],
  '/gun-sonu': ['YONETICI', 'MAGAZA'],
}

export function canOpenPage(path: string, role: UserRole): boolean {
  const page = Object.keys(PAGE_ROLES).find((key) => path === key || path.startsWith(`${key}/`))
  return !page || PAGE_ROLES[page].includes(role)
}
