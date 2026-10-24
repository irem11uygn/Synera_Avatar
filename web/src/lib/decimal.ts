// Ondalıklar API'de metin olarak taşınır (ADR-006). Kayan noktalı sayıya hiç çevrilmez:
// hesaplar ölçeklenmiş tamsayılarla (BigInt) yapılır; sunucunun yuvarlaması gibi yarım yukarı.

const PLAIN_DECIMAL = /^-?\d+(\.\d+)?$/

/** "1543.5" → 15435000n (scale = 4 için). Fazla basamaklar yarım yukarı yuvarlanır. */
export function toScaled(value: string, scale: number): bigint {
  if (!PLAIN_DECIMAL.test(value)) throw new Error(`Geçersiz ondalık sayı: ${value}`)
  const negative = value.startsWith('-')
  const [whole, fraction = ''] = (negative ? value.slice(1) : value).split('.')
  const kept = BigInt(whole + fraction.slice(0, scale).padEnd(scale, '0'))
  const roundUp = fraction.length > scale && fraction[scale] >= '5'
  const magnitude = roundUp ? kept + 1n : kept
  return negative ? -magnitude : magnitude
}

/** 15435000n, 4 → "1543.5000" */
export function fromScaled(value: bigint, scale: number): string {
  const negative = value < 0n
  const digits = (negative ? -value : value).toString().padStart(scale + 1, '0')
  const whole = digits.slice(0, digits.length - scale)
  const fraction = digits.slice(digits.length - scale)
  return `${negative ? '-' : ''}${whole}${scale > 0 ? `.${fraction}` : ''}`
}

/** Ölçeklenmiş değeri yarım yukarı (sıfırdan uzağa) yuvarlayarak bölme. */
function divideRounded(numerator: bigint, divisor: bigint): bigint {
  const negative = numerator < 0n
  const magnitude = negative ? -numerator : numerator
  const rounded = (magnitude + divisor / 2n) / divisor
  return negative ? -rounded : rounded
}

/** Toplam; sonuç `scale` basamakla. */
export function sum(values: readonly string[], scale: number): string {
  return fromScaled(
    values.reduce((total, value) => total + toScaled(value, scale), 0n),
    scale,
  )
}

/** a × b, sonuç `scale` basamağa yarım yukarı yuvarlanır (ör. miktar × birim fiyat → kuruş). */
export function multiply(a: string, b: string, scale: number): string {
  const precision = 8
  const product = toScaled(a, precision) * toScaled(b, precision)
  return fromScaled(divideRounded(product, 10n ** BigInt(2 * precision - scale)), scale)
}

/** a ÷ b, sonuç `scale` basamağa yarım yukarı yuvarlanır (ör. toplam maliyet ÷ adet → EKP). */
export function divide(a: string, b: string, scale: number): string {
  const precision = 8
  const divisor = toScaled(b, precision)
  if (divisor === 0n) throw new Error('Sıfıra bölünemez.')
  const numerator = toScaled(a, precision) * 10n ** BigInt(scale)
  const negative = numerator < 0n !== divisor < 0n
  const n = numerator < 0n ? -numerator : numerator
  const d = divisor < 0n ? -divisor : divisor
  const quotient = (2n * n + d) / (2n * d)
  return fromScaled(negative ? -quotient : quotient, scale)
}

export function compare(a: string, b: string): number {
  const precision = 8
  const difference = toScaled(a, precision) - toScaled(b, precision)
  return difference === 0n ? 0 : difference < 0n ? -1 : 1
}

/**
 * Kullanıcının yazdığı sayıyı API biçimine çevirir: "9,70" ve "9.70" → "9.70".
 * Binlik ayırıcı kabul edilmez (1.543,50 ile 1.543 karışmasın diye). Geçersizse null.
 */
export function parseUserDecimal(input: string, maxFraction: number): string | null {
  const text = input.trim().replace(',', '.')
  if (!/^\d+(\.\d+)?$/.test(text)) return null
  const fraction = text.split('.')[1] ?? ''
  return fraction.length > maxFraction ? null : text
}
