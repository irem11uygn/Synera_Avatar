import { describe, expect, it } from 'vitest'
import type { Charts, Dashboard, Recall } from '../api/types'
import { costReport, dailySummary, mailtoLink, recallNotice } from './reportMail'

const dashboard: Dashboard = {
  today: '2026-10-28',
  expiry_warning_days: 3,
  expiring: [
    { lot_no: 'SUC-2026-045', product_name: 'Narin Sucuk 1 kg', base_unit: 'ADET', expiry_date: '2026-10-30', days_left: 2, qty: '12.000', warehouses: ['ANA'], blocked: false },
  ],
  low_stock: [],
  open_recalls: [],
  unread_alerts: 1,
  draft_orders: 0,
  shipped_orders: 0,
  draft_cuttings: 0,
  today_sale_count: 3,
  today_sales_amount: '2116.50',
  stock_value: '1543.50',
}

describe('rapor e-postası', () => {
  it('günlük özet ekrandaki sayılarla yazılır, not başa eklenir', () => {
    const draft = dailySummary(dashboard, 'Toplantıda konuşalım.')
    expect(draft.subject).toContain('28.10.2026')
    expect(draft.body.startsWith('Toplantıda konuşalım.\n')).toBe(true)
    expect(draft.body).toContain('Bugünkü satış: 3 belge, 2.116,50 €')
    expect(draft.body).toContain('SUC-2026-045 · Narin Sucuk 1 kg · 12 adet · 2 gün kaldı')
  })

  it('maliyet raporu toplam maliyeti ve EKP’yi verir', () => {
    const charts = {
      cost_order_no: 'URT-2026-045',
      cost_ekp: '18.16',
      cost_slices: [
        { label: 'Sucukluk et', value: '970.00' },
        { label: 'Dış üretim hizmeti', value: '467.50' },
      ],
      parts_cutting_no: null,
      part_costs: [],
      shipments: [{ customer: 'Market A', qty_by_unit: { adet: '30.000' }, amount: '747.00' }],
    } as unknown as Charts
    const body = costReport(charts).body
    expect(body).toContain('Toplam maliyet: 1.437,50 €')
    expect(body).toContain('Birim maliyet (EKP): 18,16 € / adet')
    expect(body).toContain('Market A: 30 adet · 747,00 €')
  })

  it('e-posta programı bağlantısı uzun metni kısaltır', () => {
    const long = mailtoLink(['a@example.com', 'b@example.com'], { subject: 'Konu ş', body: 'x'.repeat(3000) }, 100)
    expect(long.truncated).toBe(true)
    expect(long.href.startsWith('mailto:a@example.com,b@example.com?subject=Konu%20%C5%9F&body=')).toBe(true)
    expect(mailtoLink(['a@example.com'], { subject: 's', body: 'kısa' }).truncated).toBe(false)
  })

  it('geri çağırma bildiriminde her müşteri yalnız kendi miktarını görür', () => {
    const contact = { person: null, phone: null, address: null }
    const recall = {
      recall_no: 'GC-2026-001',
      source_lot_no: 'ET-2026-001',
      reason: 'Deneme',
      started_at: '2026-10-28T08:00:00Z',
      lots: [{ lot_no: 'SUC-2026-045', product_name: 'Narin Sucuk 1 kg', depth: 1, expiry_date: null }],
      recipients: [
        { customer_id: 1, customer: 'Market A', contact: { ...contact, email: 'a@example.com' }, lot_no: 'SUC-2026-045', product_name: 'Narin Sucuk 1 kg', base_unit: 'ADET', qty: '30.000' },
        { customer_id: 2, customer: 'Market B', contact: { ...contact, email: 'b@example.com' }, lot_no: 'SUC-2026-045', product_name: 'Narin Sucuk 1 kg', base_unit: 'ADET', qty: '25.000' },
      ],
    } as unknown as Recall
    const own = recallNotice(recall, '', 2).body
    expect(own).toContain('Market B: SUC-2026-045 · Narin Sucuk 1 kg · 25 adet')
    expect(own).not.toContain('Market A')
    expect(recallNotice(recall).body).toContain('Market A')
  })
})
