// 3D lot akış şeması (FR-304, FR-305): lotlar derinliğe göre sütunlarda, aralarında bağ miktarı ve
// belge; ileri izlemede en sağda alıcılar. Şema yalnız kayıtlardan çizilir (CON-003).
// Ekran okuyucu için aynı bilgi bloklardaki metinde ve sayfadaki tablolarda da vardır.

import { Tooltip } from 'antd'
import type { Recipient, TraceLink, TracedLot } from '../api/types'
import { formatQty } from '../lib/format'
import { LINK_PROCESS, LOT_ORIGIN, ONWARD_STATUS } from '../lib/labels'
import { navigate } from '../lib/router'

type Props = {
  lots: TracedLot[]
  links: TraceLink[]
  recipients?: Recipient[]
  direction: 'forward' | 'backward'
}

function LotBlock({ lot, source }: { lot: TracedLot; source: boolean }) {
  const classes = ['lot-block']
  if (lot.status === 'BLOKE') classes.push('is-blocked')
  else if (source) classes.push('is-source')
  return (
    <button
      type="button"
      className={classes.join(' ')}
      style={{ textAlign: 'left', cursor: 'pointer', font: 'inherit' }}
      onClick={() => navigate(`/lotlar/${lot.lot_no}`)}
      aria-label={`${lot.lot_no} lotunun ayrıntısı`}
    >
      <div className="lot-block-title">{lot.lot_no}</div>
      <div className="lot-block-sub">{lot.product_name}</div>
      <div className="lot-block-sub">
        {LOT_ORIGIN[lot.origin]} · başlangıç {formatQty(lot.initial_qty, lot.base_unit)}
      </div>
      <div className="lot-block-sub">
        Kalan {formatQty(lot.remaining_qty, lot.base_unit)}
        {lot.status === 'BLOKE' && <strong style={{ color: 'var(--danger)' }}> · BLOKE</strong>}
      </div>
    </button>
  )
}

function CustomerBlock({ recipient }: { recipient: Recipient }) {
  const classes = ['lot-block', recipient.recall_violation ? 'is-violation' : 'is-customer']
  return (
    <Tooltip title={ONWARD_STATUS[recipient.onward_status]}>
      <div className={classes.join(' ')} tabIndex={0}>
        <div className="lot-block-title">{recipient.customer}</div>
        <div className="lot-block-sub">
          {recipient.lot_no} · {formatQty(recipient.qty, recipient.base_unit)}
        </div>
        <div className="lot-block-sub">
          {recipient.onward_status === 'KAYITLI'
            ? `Alıcıları kayıtlı (${recipient.onward_items.length})`
            : recipient.onward_status === 'KISMEN'
              ? 'Kısmen kayıtlı'
              : 'Sonrası bilinmiyor'}
        </div>
        {recipient.recall_violation && <div className="lot-block-sub">Geri çağırma sonrası satış</div>}
      </div>
    </Tooltip>
  )
}

export function TraceFlow({ lots, links, recipients = [], direction }: Props) {
  // İleri izlemede derinlik soldan sağa artar; geri izlemede kaynaklar solda, incelenen lot sağda.
  const maxDepth = Math.max(0, ...lots.map((lot) => lot.depth))
  const order = Array.from({ length: maxDepth + 1 }, (_, i) => (direction === 'forward' ? i : maxDepth - i))
  const columns = order.map((depth) => lots.filter((lot) => lot.depth === depth))
  const sourceNo = lots.find((lot) => lot.depth === 0)?.lot_no

  function linksBetween(left: TracedLot[], right: TracedLot[]): TraceLink[] {
    const leftNos = new Set(left.map((lot) => lot.lot_no))
    const rightNos = new Set(right.map((lot) => lot.lot_no))
    return links.filter((link) => leftNos.has(link.parent_lot_no) && rightNos.has(link.child_lot_no))
  }

  return (
    <div className="trace-stage" role="group" aria-label="Lot akış şeması">
      <div className="trace-plane">
        {columns.map((column, index) => (
          <div key={order[index]} style={{ display: 'flex' }}>
            {index > 0 && (
              <div className="trace-arrows" aria-hidden="true">
                {linksBetween(columns[index - 1], column).map((link) => (
                  <div className="trace-arrow" key={`${link.parent_lot_no}-${link.child_lot_no}-${link.doc_no}`}>
                    {link.doc_no ?? LINK_PROCESS[link.process]}
                    <br />
                    {formatQty(link.qty)} · {link.parent_lot_no}
                  </div>
                ))}
              </div>
            )}
            <div className="trace-column">
              <div className="trace-column-title">
                {order[index] === 0 ? (direction === 'forward' ? 'Kaynak lot' : 'İncelenen lot') : `${order[index]}. kademe`}
              </div>
              {column.map((lot) => (
                <LotBlock key={lot.lot_no} lot={lot} source={lot.lot_no === sourceNo} />
              ))}
            </div>
          </div>
        ))}
        {direction === 'forward' && recipients.length > 0 && (
          <div style={{ display: 'flex' }}>
            <div className="trace-arrows" aria-hidden="true">
              {recipients.map((r) => (
                <div className="trace-arrow" key={`${r.customer}-${r.lot_no}`}>
                  {r.sales.map((s) => s.sale_no).join(', ')}
                  <br />
                  {formatQty(r.sold_qty, r.base_unit)}
                </div>
              ))}
            </div>
            <div className="trace-column">
              <div className="trace-column-title">Alıcılar</div>
              {recipients.map((r) => (
                <CustomerBlock key={`${r.customer}-${r.lot_no}`} recipient={r} />
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
