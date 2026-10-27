// İlk dolan ilk çıkar (FEFO): satılacak miktar, son kullanma tarihi en yakın lottan başlayarak
// lotlara dağıtılır. Satışa kapalı ve süresi geçmiş lotlar atlanır; tarihsiz lotlar en sona kalır.

import { compare, sum } from './decimal'

export type StockLot = { lot_no: string; qty: string; expiry_date: string | null; blocked: boolean }
export type Pick = { lot_no: string; qty: string; expiry_date: string | null }

/** Satılabilir lotlar, ilk dolan önde. `today` YYYY-MM-DD. */
export function sellableLots<T extends StockLot>(lots: readonly T[], today: string): T[] {
  return lots
    .filter((lot) => !lot.blocked && compare(lot.qty, '0') > 0 && (lot.expiry_date === null || lot.expiry_date >= today))
    .toSorted((a, b) => {
      if (a.expiry_date === b.expiry_date) return a.lot_no.localeCompare(b.lot_no)
      if (a.expiry_date === null) return 1
      if (b.expiry_date === null) return -1
      return a.expiry_date.localeCompare(b.expiry_date)
    })
}

/** Miktarı lotlara dağıtır. Yetmezse `short` eksik kalan miktardır ("0" değilse satış yapılamaz). */
export function allocate(lots: readonly StockLot[], qty: string, today: string): { picks: Pick[]; short: string } {
  const picks: Pick[] = []
  let remaining = qty
  for (const lot of sellableLots(lots, today)) {
    if (compare(remaining, '0') <= 0) break
    const take = compare(lot.qty, remaining) < 0 ? lot.qty : remaining
    picks.push({ lot_no: lot.lot_no, qty: take, expiry_date: lot.expiry_date })
    remaining = sum([remaining, negate(take)], 3)
  }
  return { picks, short: compare(remaining, '0') > 0 ? remaining : '0' }
}

function negate(value: string): string {
  return value.startsWith('-') ? value.slice(1) : `-${value}`
}
