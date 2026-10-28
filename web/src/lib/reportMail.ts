// E-postayla gönderilen raporların metni. Ekrandaki verinin aynısından, düz metin olarak üretilir;
// kullanıcı göndermeden önce ön izlemede görür ve isterse değiştirir.

import type { AlertRow, Charts, Dashboard, Recall } from '../api/types'
import { formatDate, formatDateTime, formatMoney, formatQty } from './format'
import { t } from './i18n'
import { ALERT_KIND, SEVERITY } from './labels'

export type MailDraft = { subject: string; body: string }

const bullet = (text: string) => `  • ${text}`

function withNote(note: string, lines: string[]): string {
  const intro = note.trim() ? [note.trim(), ''] : []
  return [...intro, ...lines].join('\n')
}

export function dailySummary(data: Dashboard, note = ''): MailDraft {
  const lines = [
    t('Günlük özet — {day}', { day: formatDate(data.today) }),
    '',
    t('Bugünkü satış: {n} belge, {amount}', { n: data.today_sale_count, amount: formatMoney(data.today_sales_amount) }),
    t('Elimizdeki stok değeri: {amount}', { amount: formatMoney(data.stock_value) }),
    t('Okunmamış alarm: {n}', { n: data.unread_alerts }),
    '',
    t('Son kullanma tarihi yaklaşan ya da geçen parti: {n}', { n: data.expiring.length }),
    ...data.expiring
      .slice(0, 8)
      .map((lot) =>
        bullet(
          `${lot.lot_no} · ${lot.product_name} · ${formatQty(lot.qty, lot.base_unit)} · ${
            lot.days_left < 0 ? t('SKT geçti') : t('{n} gün kaldı', { n: lot.days_left })
          }`,
        ),
      ),
    t('Kritik stok altındaki ürün: {n}', { n: data.low_stock.length }),
    ...data.low_stock.map((row) =>
      bullet(`${row.product_name}: ${formatQty(row.qty, row.base_unit)} (${t('en az')} ${formatQty(row.min_stock, row.base_unit)})`),
    ),
    t('Açık geri çağırma: {n}', { n: data.open_recalls.length }),
    ...data.open_recalls.map((r) => bullet(`${r.recall_no} · ${r.lot_no} · ${formatDateTime(r.started_at)}`)),
  ]
  return { subject: t('Synera günlük özet — {day}', { day: formatDate(data.today) }), body: withNote(note, lines) }
}

export function costReport(data: Charts, note = ''): MailDraft {
  const total = data.cost_slices.reduce((sum, slice) => sum + Number(slice.value), 0)
  const lines = [
    data.cost_order_no
      ? t('Son tamamlanan dış üretim: {no}', { no: data.cost_order_no })
      : t('Henüz tamamlanmış dış üretim yok.'),
    ...data.cost_slices.map((slice) => bullet(`${slice.label}: ${formatMoney(slice.value)}`)),
    ...(data.cost_order_no
      ? [
          bullet(`${t('Toplam maliyet')}: ${formatMoney(total.toFixed(2))}`),
          t('Birim maliyet (EKP): {ekp} / adet', { ekp: formatMoney(data.cost_ekp) }),
        ]
      : []),
    '',
    data.parts_cutting_no
      ? t('Son parçalama {no} — parça maliyetleri (€/kg):', { no: data.parts_cutting_no })
      : t('Henüz onaylanmış parçalama yok.'),
    ...data.part_costs.map((part) => bullet(`${part.label}: ${formatMoney(part.unit_cost)} / kg (${formatQty(part.kg, 'KG')})`)),
    '',
    t('Son 30 gün müşteri sevkiyatı:'),
    ...data.shipments.map((s) =>
      bullet(
        `${s.customer}: ${Object.entries(s.qty_by_unit)
          .map(([unit, qty]) => formatQty(qty, unit === 'adet' ? 'ADET' : 'KG'))
          .join(' + ')} · ${formatMoney(s.amount)}`,
      ),
    ),
  ]
  return { subject: t('Synera maliyet ve sevkiyat raporu'), body: withNote(note, lines) }
}

/**
 * Geri çağırma bildirimi. `customerId` verilirse yalnız o müşterinin miktarları yazılır: her müşteri
 * kendi e-postasını alır, başka müşterinin adını ve miktarını görmez.
 */
export function recallNotice(recall: Recall, note = '', customerId?: number): MailDraft {
  const lots = recall.lots.filter((lot) => lot.depth > 0 || lot.lot_no === recall.source_lot_no)
  const recipients = customerId == null ? recall.recipients : recall.recipients.filter((r) => r.customer_id === customerId)
  const lines = [
    t('Geri çağırma bildirimi: {no}', { no: recall.recall_no }),
    t('Başlangıç: {time}', { time: formatDateTime(recall.started_at) }),
    t('Neden: {reason}', { reason: recall.reason }),
    '',
    t('Etkilenen partiler (lot numarası etiketin üzerindedir):'),
    ...lots.map((lot) => bullet(`${lot.lot_no} · ${lot.product_name}${lot.expiry_date ? ` · SKT ${formatDate(lot.expiry_date)}` : ''}`)),
    '',
    customerId == null ? t('Müşterilere teslim edilen miktarlar:') : t('Size teslim edilen miktarlar:'),
    ...recipients.map((r) => bullet(`${r.customer}: ${r.lot_no} · ${r.product_name} · ${formatQty(r.qty, r.base_unit)}`)),
    '',
    t('Lütfen bu lot numaralı ürünleri hemen satıştan çekin, ayrı bir yerde bekletin ve elinizdeki miktarı bu e-postaya yanıt vererek bildirin. Ürünler tarafımızdan geri alınacaktır.'),
  ]
  return { subject: t('ACİL — Geri çağırma {no} ({lot})', { no: recall.recall_no, lot: recall.source_lot_no }), body: withNote(note, lines) }
}

export function alarmList(rows: AlertRow[], note = ''): MailDraft {
  const lines = [
    t('Açık alarmlar: {n}', { n: rows.length }),
    '',
    ...rows.map((a) => `[${SEVERITY[a.severity]}] ${ALERT_KIND[a.kind]} — ${formatDateTime(a.created_at)}\n    ${a.message}`),
  ]
  return { subject: t('Synera açık alarmlar ({n})', { n: rows.length }), body: withNote(note, lines) }
}

/** E-posta programında açmak için mailto: bağlantısı. Uzun metin kısaltılır (tarayıcı sınırı). */
export function mailtoLink(to: string[], draft: MailDraft, limit = 1800): { href: string; truncated: boolean } {
  const truncated = draft.body.length > limit
  const body = truncated ? `${draft.body.slice(0, limit)}\n…` : draft.body
  const params = `subject=${encodeURIComponent(draft.subject)}&body=${encodeURIComponent(body)}`
  return { href: `mailto:${to.join(",")}?${params}`, truncated }
}
