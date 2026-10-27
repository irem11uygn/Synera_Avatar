import { describe, expect, it } from 'vitest'
import { code128Modules, code128Values, PATTERNS } from './code128'

describe('Code 128', () => {
  it('desen tablosu standart uzunlukta', () => {
    expect(PATTERNS).toHaveLength(107)
    PATTERNS.forEach((pattern, value) => {
      const modules = [...pattern].reduce((total, width) => total + Number(width), 0)
      expect(modules, `değer ${value}`).toBe(value === 106 ? 13 : 11)
    })
  })

  it('B kümesiyle başlar, sağlama değeri doğru, durdurma deseniyle biter', () => {
    // "AB": (104 + 33×1 + 34×2) mod 103 = 102
    expect(code128Values('AB')).toEqual([104, 33, 34, 102, 106])
    const modules = code128Modules('AB')
    expect(modules.startsWith('11010010000')).toBe(true)
    expect(modules.endsWith('1100011101011')).toBe(true)
    expect(modules).toHaveLength(11 * 4 + 13)
  })

  it('lot numarası kodlanır, Türkçe harf reddedilir', () => {
    expect(code128Modules('SUC-2026-045').length).toBe(11 * (12 + 2) + 13)
    expect(() => code128Values('ŞİŞ')).toThrow()
  })
})
