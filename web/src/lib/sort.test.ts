import { describe, expect, it } from 'vitest'
import { compareValues, sortable } from './sort'

const sorted = (values: unknown[]) => [...values].sort(compareValues)

describe('tablo sıralama', () => {
  it('ondalık metinler sayı olarak sıralanır', () => {
    expect(sorted(['85.000', '9.700', '1543.50', '-3'])).toEqual(['-3', '9.700', '85.000', '1543.50'])
  })

  it('metin Türkçe alfabeyle, lot numaraları içindeki sayıyla sıralanır', () => {
    expect(sorted(['Şube', 'Çiğköfte', 'Sucuk', 'Cevizli'])).toEqual(['Cevizli', 'Çiğköfte', 'Sucuk', 'Şube'])
    expect(sorted(['SUC-2026-10', 'SUC-2026-9', 'ET-2026-001'])).toEqual(['ET-2026-001', 'SUC-2026-9', 'SUC-2026-10'])
  })

  it('ISO tarihler zaman sırasıyla, boş değer sonda', () => {
    expect(sorted(['2026-11-02', null, '2026-10-28', '2026-10-30T09:00:00Z'])).toEqual([
      '2026-10-28',
      '2026-10-30T09:00:00Z',
      '2026-11-02',
      null,
    ])
  })

  it('yalnız veri sütunlarına sıralama eklenir', () => {
    const columns = sortable<{ lot_no: string }>([
      { title: 'Lot', dataIndex: 'lot_no' },
      { title: 'İşlem', key: 'actions' },
      { title: 'Özel', dataIndex: 'x', sorter: false },
    ])
    expect(typeof columns[0].sorter).toBe('function')
    expect(columns[1].sorter).toBeUndefined()
    expect(columns[2].sorter).toBe(false)
  })
})
