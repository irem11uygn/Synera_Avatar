import { describe, expect, it } from 'vitest'
import { formatDate, formatDecimal, formatMoney, formatPercent, formatQty, formatUnitCost, todayIso } from './format'

describe('Türkçe biçimler', () => {
  it('para: binlik nokta, kuruş virgül', () => {
    expect(formatMoney('1543.50')).toBe('1.543,50 €')
    expect(formatMoney('0.00')).toBe('0,00 €')
    expect(formatMoney('-12.3')).toBe('−12,30 €')
    expect(formatMoney(null)).toBe('—')
  })

  it('EKP tam değeri kuruştan ince gösterilir', () => {
    expect(formatUnitCost('18.158824')).toBe('18,158824 €')
    expect(formatUnitCost('9.7000')).toBe('9,70 €')
  })

  it('miktar: gereksiz sıfırlar atılır, birim eklenir', () => {
    expect(formatQty('85.000', 'ADET')).toBe('85 adet')
    expect(formatQty('1.500', 'KG')).toBe('1,5 kg')
    expect(formatQty('1250.000')).toBe('1.250')
    expect(formatQty('-85.000', 'ADET')).toBe('−85 adet')
  })

  it('yüzde ve genel ondalık', () => {
    expect(formatPercent('27.07')).toBe('%27,07')
    expect(formatDecimal('0.000', 0, 3)).toBe('0')
    expect(formatDecimal('-0.0004', 0, 3)).toBe('0')
  })

  it('tarih', () => {
    expect(formatDate('2026-12-23')).toBe('23.12.2026')
    expect(formatDate(null)).toBe('—')
    expect(todayIso(new Date(2026, 9, 4))).toBe('2026-10-04')
  })
})
