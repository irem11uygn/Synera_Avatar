// Form doğrulama kuralları. İstemci doğrulaması kullanıcıya hızlı geri bildirim içindir;
// asıl denetim sunucudadır (aynı kurallar orada da var).

import type { FormRule } from 'antd'
import { compare, parseUserDecimal } from './decimal'

type DecimalOptions = { maxFraction: number; required?: boolean; allowZero?: boolean; integer?: boolean }

export function decimalRule(
  label: string,
  { maxFraction, required = true, allowZero = false, integer = false }: DecimalOptions,
): FormRule {
  return {
    required,
    validator: async (_rule, value: unknown) => {
      const text = value == null ? '' : String(value)
      if (!text.trim()) {
        if (required) throw new Error(`${label} gerekli.`)
        return
      }
      const parsed = parseUserDecimal(text, integer ? 0 : maxFraction)
      if (parsed === null) {
        throw new Error(
          integer
            ? `${label} tam sayı olmalı.`
            : `${label}: geçerli bir sayı yazın (en çok ${maxFraction} ondalık, binlik ayırıcı olmadan).`,
        )
      }
      if (!allowZero && compare(parsed, '0') === 0) throw new Error(`${label} sıfırdan büyük olmalı.`)
    },
  }
}

/** Formdaki metni API'nin beklediği ondalık metne çevirir; boşsa null. */
export function toApiDecimal(value: string | null | undefined, maxFraction: number): string | null {
  if (value == null || !value.trim()) return null
  const parsed = parseUserDecimal(value, maxFraction)
  if (parsed === null) throw new Error(`Geçersiz sayı: ${value}`)
  return parsed
}

/** API'deki ondalığı forma yazmak için gereksiz sıfırları atar: "9.7000" → "9.7", "85.000" → "85". */
export function fromApiDecimal(value: string | null | undefined): string | undefined {
  if (value == null) return undefined
  return value.includes('.') ? value.replace(/0+$/, '').replace(/\.$/, '') : value
}

export function textOrNull(value: string | null | undefined): string | null {
  const text = value?.trim()
  return text ? text : null
}
