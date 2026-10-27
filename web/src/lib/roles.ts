// Roller ve yetkiler. Sunucu her isteği kendisi denetler (app/api/deps.py); burada yalnız
// kullanıcıya yapamayacağı işin düğmesini göstermemek için aynı kurallar tekrarlanır.

import type { UserRole } from '../api/types'

export const ROLE: Record<UserRole, string> = {
  YONETICI: 'Yönetici',
  DEPO: 'Depo sorumlusu',
  URETIM: 'Üretim sorumlusu',
  KALITE: 'Kalite sorumlusu',
  MAGAZA: 'Mağaza / kasa',
  SATIS: 'Satış elemanı (araç)',
}

export const ROLE_HELP: Record<UserRole, string> = {
  YONETICI: 'Her ekranı görür ve her işlemi yapar; kullanıcıları yönetir.',
  DEPO: 'Mal kabul, stok, sayım, araca yükleme ve fire.',
  URETIM: 'Fason üretim, parçalama ve yeniden işleme.',
  KALITE: 'Lot izleme, geri çağırma, tatbikat ve uyarılar.',
  MAGAZA: 'Mağaza satışı, iade ve gün sonu.',
  SATIS: 'Yalnız telefon uygulaması: araçtan satış ve araç sayımı.',
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
