// Ekranda Türkçe sayı ve tarih biçimleri: 1.543,50 € · 85 adet · %27,07 · 23.12.2026.
// Sayılar metin olarak biçimlenir; kayan noktalı sayıya çevrilmez (ADR-006).

import { fromScaled, toScaled } from './decimal'

export type Unit = 'KG' | 'ADET'

const UNIT_LABEL: Record<Unit, string> = { KG: 'kg', ADET: 'adet' }

function groupThousands(whole: string): string {
  return whole.replace(/\B(?=(\d{3})+(?!\d))/g, '.')
}

/** Kesir basamağı en az `minFraction`, en çok `maxFraction` olacak biçimde; fazlası yarım yukarı yuvarlanır. */
export function formatDecimal(value: string, minFraction = 0, maxFraction = 6): string {
  const normalized = fromScaled(toScaled(value, maxFraction), maxFraction)
  const negative = normalized.startsWith('-')
  const [whole, fraction = ''] = (negative ? normalized.slice(1) : normalized).split('.')
  let digits = fraction
  while (digits.length > minFraction && digits.endsWith('0')) digits = digits.slice(0, -1)
  const sign = negative && /[1-9]/.test(whole + digits) ? '−' : ''
  return `${sign}${groupThousands(whole)}${digits ? `,${digits}` : ''}`
}

export function formatMoney(value: string | null | undefined): string {
  return value == null ? '—' : `${formatDecimal(value, 2, 2)} €`
}

/** Birim maliyet ve EKP gibi kuruştan ince değerler (ör. 18,158824 €). */
export function formatUnitCost(value: string | null | undefined): string {
  return value == null ? '—' : `${formatDecimal(value, 2, 6)} €`
}

export function formatQty(value: string | null | undefined, unit?: Unit): string {
  if (value == null) return '—'
  const number = formatDecimal(value, 0, 3)
  return unit ? `${number} ${UNIT_LABEL[unit]}` : number
}

export function formatPercent(value: string | null | undefined): string {
  return value == null ? '—' : `%${formatDecimal(value, 2, 2)}`
}

export function unitLabel(unit: Unit): string {
  return UNIT_LABEL[unit]
}

/** "2026-12-23" → "23.12.2026" (saat dilimi dönüşümü yok; takvim günüdür). */
export function formatDate(value: string | null | undefined): string {
  if (!value) return '—'
  const [year, month, day] = value.slice(0, 10).split('-')
  return `${day}.${month}.${year}`
}

const DATE_TIME = new Intl.DateTimeFormat('tr-TR', {
  day: '2-digit',
  month: '2-digit',
  year: 'numeric',
  hour: '2-digit',
  minute: '2-digit',
})

/** API zamanları saat dilimi ekli ISO 8601'dir; tarayıcının yerel saatine çevrilir. */
export function formatDateTime(value: string | null | undefined): string {
  return value ? DATE_TIME.format(new Date(value)) : '—'
}

/** Tarayıcının yerel takvimine göre bugün, API biçiminde (YYYY-MM-DD). */
export function todayIso(now: Date = new Date()): string {
  const month = String(now.getMonth() + 1).padStart(2, '0')
  const day = String(now.getDate()).padStart(2, '0')
  return `${now.getFullYear()}-${month}-${day}`
}
