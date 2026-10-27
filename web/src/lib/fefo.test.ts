import { describe, expect, it } from 'vitest'
import { allocate, sellableLots } from './fefo'

const lots = [
  { lot_no: 'SUC-3', qty: '10', expiry_date: '2026-11-20', blocked: false },
  { lot_no: 'SUC-1', qty: '4', expiry_date: '2026-11-02', blocked: false },
  { lot_no: 'SUC-OLD', qty: '9', expiry_date: '2026-10-20', blocked: false },
  { lot_no: 'SUC-BLK', qty: '9', expiry_date: '2026-11-01', blocked: true },
  { lot_no: 'SUC-NODATE', qty: '5', expiry_date: null, blocked: false },
]

describe('FEFO', () => {
  it('süresi geçmiş ve satışa kapalı lotları atlar, ilk dolanı öne alır', () => {
    expect(sellableLots(lots, '2026-10-28').map((l) => l.lot_no)).toEqual(['SUC-1', 'SUC-3', 'SUC-NODATE'])
  })

  it('miktarı ilk dolan lottan başlayarak böler', () => {
    const { picks, short } = allocate(lots, '6', '2026-10-28')
    expect(picks.map((p) => [p.lot_no, p.qty])).toEqual([
      ['SUC-1', '4'],
      ['SUC-3', '2.000'],
    ])
    expect(short).toBe('0')
  })

  it('stok yetmezse eksik miktarı söyler', () => {
    expect(allocate(lots, '25', '2026-10-28').short).toBe('6.000')
  })
})
