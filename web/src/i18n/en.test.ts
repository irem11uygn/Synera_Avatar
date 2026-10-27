import { describe, expect, it } from 'vitest'
import { EN } from './en'

// Kaynak dosyaların metni (Vite içe aktarımı; derlenmiş uygulamaya girmez, yalnız testte okunur).
const SOURCES = import.meta.glob<string>(['../**/*.{ts,tsx}', '!../**/*.test.ts', '!../**/*.d.ts', '!./en.ts'], {
  query: '?raw',
  import: 'default',
  eager: true,
})

/** Kaynaktaki bütün t('...') ve t("...") anahtarları. */
function usedKeys(): Set<string> {
  const keys = new Set<string>()
  const pattern = /\bt\((['"])((?:\\.|(?!\1).)*)\1/g
  for (const text of Object.values(SOURCES)) {
    for (const match of text.matchAll(pattern)) {
      keys.add(match[1] === "'" ? match[2].replace(/\\'/g, "'") : match[2].replace(/\\"/g, '"'))
    }
  }
  return keys
}

describe('İngilizce sözlük', () => {
  const used = usedKeys()

  it('kaynak dosyalar okundu', () => {
    expect(Object.keys(SOURCES).length).toBeGreaterThan(40)
  })

  it('ekrandaki her metnin İngilizcesi var', () => {
    expect([...used].filter((key) => !(key in EN))).toEqual([])
  })

  it('sözlükte kullanılmayan metin kalmadı', () => {
    expect(Object.keys(EN).filter((key) => !used.has(key))).toEqual([])
  })

  it('yer tutucular iki dilde aynı', () => {
    const names = (text: string) => [...text.matchAll(/\{(\w+)\}/g)].map((m) => m[1]).sort()
    const wrong = Object.entries(EN).filter(([tr, en]) => names(tr).join() !== names(en).join())
    expect(wrong).toEqual([])
  })
})
