// Yazdırılabilir belgeler: uygulama çerçevesi olmadan, A4 (etiket 100×60 mm). Tarayıcının
// "Yazdır" penceresinden kâğıda ya da PDF'e alınır.

import { ArrowLeftOutlined, PrinterOutlined } from '@ant-design/icons'
import { useQuery } from '@tanstack/react-query'
import { Alert, Button, Flex, InputNumber, Spin } from 'antd'
import { useEffect, useState, type ReactNode } from 'react'
import { api, errorMessage } from '../api/client'
import type { DayEnd, LotDetail, Recall, Sale, StockCount, Warehouse } from '../api/types'
import { useSession } from '../auth/context'
import { code128Modules } from '../lib/code128'
import { formatDate, formatDateTime, formatMoney, formatQty } from '../lib/format'
import { PAYMENT_METHOD, paymentLabel, SALE_CHANNEL } from '../lib/labels'
import { matchPath } from '../lib/router'
import { runDrill, type Drill } from '../lib/drill'
import { DrillTables } from './MockRecallPage'
import { t } from '../lib/i18n'

/** Belgelerin üst bilgisindeki işletme adı; kurulumda işletmenin kendi adıyla değiştirilir. */
const COMPANY = t('Synera Gıda — örnek işletme')

function Barcode({ text, height = 46 }: { text: string; height?: number }) {
  let modules: string
  try {
    modules = code128Modules(text)
  } catch {
    return <span>{text}</span>
  }
  const quiet = 10
  const width = modules.length + quiet * 2
  return (
    <svg viewBox={`0 0 ${width} ${height}`} width="100%" height={height} preserveAspectRatio="none" role="img" aria-label={`Barkod ${text}`}>
      <rect width={width} height={height} fill="#fff" />
      {[...modules].map((bit, index) =>
        bit === '1' ? <rect key={index} x={index + quiet} y={0} width={1} height={height} fill="#000" /> : null,
      )}
    </svg>
  )
}

function Toolbar({ children }: { children?: ReactNode }) {
  return (
    <div className="print-toolbar no-print">
      <Button icon={<ArrowLeftOutlined />} onClick={() => window.history.back()}>
        {t('Geri')}
      </Button>
      {children}
      <Button type="primary" icon={<PrinterOutlined />} onClick={() => window.print()}>
        {t('Yazdır')}
      </Button>
    </div>
  )
}

function Loading({ error }: { error?: unknown }) {
  return (
    <>
      <Toolbar />
      <Flex justify="center" style={{ padding: 48 }}>
        {error ? <Alert type="error" showIcon title={errorMessage(error)} /> : <Spin size="large" />}
      </Flex>
    </>
  )
}

function Head({ title, number, date }: { title: string; number?: string; date?: string }) {
  return (
    <div className="print-head">
      <div>
        <h1>{title}</h1>
        <div>{COMPANY}</div>
      </div>
      <div style={{ textAlign: 'right' }}>
        {number && <div style={{ fontSize: 18, fontWeight: 700 }}>{number}</div>}
        {date && <div>{date}</div>}
      </div>
    </div>
  )
}

// --- Lot etiketi ---

function LabelPrint({ lotNo }: { lotNo: string }) {
  const [copies, setCopies] = useState(() => Number(new URLSearchParams(window.location.search).get('adet')) || 1)
  const lot = useQuery({ queryKey: ['lot', lotNo], queryFn: () => api<LotDetail>(`/lots/${encodeURIComponent(lotNo)}`) })
  if (!lot.data) return <Loading error={lot.error} />
  const data = lot.data
  return (
    <>
      <Toolbar>
        <span>
          Adet:{' '}
          <InputNumber min={1} max={60} value={copies} onChange={(value) => setCopies(value ?? 1)} aria-label={t('Etiket adedi')} />
        </span>
      </Toolbar>
      <div className="label-sheet">
        {Array.from({ length: copies }, (_, index) => (
          <div className="lot-label" key={index}>
            <div>
              <div className="lot-label-product">{data.product_name}</div>
              <div>{COMPANY}</div>
            </div>
            <div>
              <div>
                {t('Üretim / kabul')}: <b>{formatDate(data.produced_at)}</b>
              </div>
              <div>
                {t('Son tüketim')}: <b>{formatDate(data.expiry_date)}</b>
              </div>
            </div>
            <div>
              <Barcode text={data.lot_no} />
              <div className="lot-label-lot">LOT {data.lot_no}</div>
            </div>
          </div>
        ))}
      </div>
    </>
  )
}

// --- Satış fişi / sevk irsaliyesi ---

function SalePrint({ id }: { id: number }) {
  const sale = useQuery({ queryKey: ['sale', id], queryFn: () => api<Sale>(`/sales/${id}`) })
  if (!sale.data) return <Loading error={sale.error} />
  const data = sale.data
  return (
    <>
      <Toolbar />
      <div className="print-sheet">
        <Head title={t('Satış fişi / sevk irsaliyesi')} number={data.sale_no} date={formatDateTime(data.sold_at)} />
        <p>
          <b>{t('Müşteri:')}</b> {data.customer_name}
          <br />
          <b>{t('Satış yeri:')}</b> {SALE_CHANNEL[data.channel]} · <b>{t('Satıcı:')}</b> {data.seller_name || '—'}
          <br />
          <b>{t('Ödeme:')}</b> {data.payment_method ? PAYMENT_METHOD[data.payment_method] : t('Belirtilmedi')}
        </p>
        <table>
          <thead>
            <tr>
              <th>{t('Ürün')}</th>
              <th>{t('Lot')}</th>
              <th className="num">{t('Miktar')}</th>
              <th className="num">{t('Birim fiyat')}</th>
              <th className="num">{t('Tutar')}</th>
            </tr>
          </thead>
          <tbody>
            {data.lines.map((line) => (
              <tr key={line.id}>
                <td>{line.product_name}</td>
                <td>{line.lot_no}</td>
                <td className="num">{formatQty(line.qty, line.base_unit)}</td>
                <td className="num">{formatMoney(line.unit_price)}</td>
                <td className="num">{formatMoney(line.amount)}</td>
              </tr>
            ))}
          </tbody>
          <tfoot>
            <tr>
              <th colSpan={4} className="num">
                {t('Toplam (KDV hariç)')}
              </th>
              <th className="num">{formatMoney(data.total_amount)}</th>
            </tr>
          </tfoot>
        </table>
        <p style={{ fontSize: 12 }}>
          {t('Lot numaraları ürün geri çağırmada müşteriye ulaşmak için kaydedilir. Bu belge mali fatura yerine geçmez.')}
        </p>
        <div className="print-signatures">
          <div>{t('Teslim eden')}</div>
          <div>{t('Teslim alan')}</div>
        </div>
      </div>
    </>
  )
}

// --- Geri çağırma bildirimi (müşteri başına bir sayfa) ---

function RecallPrint({ id }: { id: number }) {
  const recall = useQuery({ queryKey: ['recall', id], queryFn: () => api<Recall>(`/recalls/${id}`) })
  if (!recall.data) return <Loading error={recall.error} />
  const data = recall.data
  const customers = [...new Map(data.recipients.map((r) => [r.customer_id, r.customer])).entries()]
  return (
    <>
      <Toolbar />
      {customers.length === 0 && (
        <div className="print-sheet">
          <Head title={t('Ürün geri çağırma bildirimi')} number={data.recall_no} date={formatDateTime(data.started_at)} />
          <p>{t('Bu geri çağırmada mal hiçbir müşteriye satılmamış; bildirim gerekmez.')}</p>
        </div>
      )}
      {customers.map(([customerId, name]) => {
        const rows = data.recipients.filter((r) => r.customer_id === customerId)
        const contact = rows[0].contact
        return (
          <div className="print-sheet" key={customerId} style={{ breakAfter: 'page' }}>
            <Head title={t('Ürün geri çağırma bildirimi')} number={data.recall_no} date={formatDate(data.started_at)} />
            <p>
              <b>{t('Sayın {person},', { person: contact.person ?? t('Yetkili') })}</b>
              <br />
              {name}
              {contact.address ? `, ${contact.address}` : ''}
            </p>
            <p>
              {t('Size teslim ettiğimiz aşağıdaki ürünler "{reason}" nedeniyle geri çağrılmıştır. Lütfen bu ürünleri hemen satıştan kaldırın, ayrı bir yerde muhafaza edin ve bize ulaşın. Ürünler tarafımızdan teslim alınacak; bedeli iade edilecek ya da yenisiyle değiştirilecektir.', { reason: data.reason })}
            </p>
            <table>
              <thead>
                <tr>
                  <th>{t('Ürün')}</th>
                  <th>{t('Lot no')}</th>
                  <th>{t('Teslim belgesi')}</th>
                  <th className="num">{t('Sizde olması gereken')}</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row) => (
                  <tr key={row.lot_no}>
                    <td>{row.product_name}</td>
                    <td>{row.lot_no}</td>
                    <td>{row.sales.map((s) => s.sale_no).join(', ')}</td>
                    <td className="num">{formatQty(row.qty, row.base_unit)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <p>
              {t('Ürünleri başka bir şubenize ya da müşterinize verdiyseniz, lütfen kime ve ne kadar verdiğinizi bize bildirin; onlara da ulaşmamız gerekiyor.')}
            </p>
            <div className="print-signatures">
              <div>{t('Kalite sorumlusu')}</div>
              <div>{t('Müşteri teslim alındı / tarih')}</div>
            </div>
          </div>
        )
      })}
    </>
  )
}

// --- Gün sonu ---

function DayEndPrint({ day }: { day: string }) {
  const warehouseId = Number(new URLSearchParams(window.location.search).get('depo')) || undefined
  const report = useQuery({
    queryKey: ['day-end', day, warehouseId ?? 'all'],
    queryFn: () => api<DayEnd>('/day-end', { query: { day, warehouse_id: warehouseId } }),
  })
  const warehouses = useQuery({ queryKey: ['warehouses'], queryFn: () => api<Warehouse[]>('/warehouses') })
  if (!report.data) return <Loading error={report.error} />
  const data = report.data
  const place = warehouses.data?.find((w) => w.id === warehouseId)?.name ?? t('Mağaza ve araçlar')
  return (
    <>
      <Toolbar />
      <div className="print-sheet">
        <Head title={t('Gün sonu raporu')} number={formatDate(day)} date={place} />
        <table>
          <tbody>
            <tr>
              <th>{t('Satış ({n} belge)', { n: data.sale_count })}</th>
              <td className="num">{formatMoney(data.sales_amount)}</td>
            </tr>
            <tr>
              <th>{t('İade ({n})', { n: data.returns.length })}</th>
              <td className="num">− {formatMoney(data.refund_amount)}</td>
            </tr>
            <tr>
              <th>{t('Net')}</th>
              <td className="num">
                <b>{formatMoney(data.net_amount)}</b>
              </td>
            </tr>
          </tbody>
        </table>
        <h3>{t('Ödeme türüne göre')}</h3>
        <table>
          <thead>
            <tr>
              <th>{t('Ödeme')}</th>
              <th className="num">{t('Belge')}</th>
              <th className="num">{t('Tutar')}</th>
              <th className="num">{t('Sayılan')}</th>
            </tr>
          </thead>
          <tbody>
            {data.by_payment.map((row) => (
              <tr key={row.key}>
                <td>{paymentLabel(row.key)}</td>
                <td className="num">{row.sale_count}</td>
                <td className="num">{formatMoney(row.amount)}</td>
                <td />
              </tr>
            ))}
          </tbody>
        </table>
        <h3>{t('Satıcıya göre')}</h3>
        <table>
          <tbody>
            {data.by_seller.map((row) => (
              <tr key={row.key}>
                <td>{row.key}</td>
                <td className="num">{row.sale_count}</td>
                <td className="num">{formatMoney(row.amount)}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <h3>{t('Satışlar')}</h3>
        <table>
          <thead>
            <tr>
              <th>{t('Saat')}</th>
              <th>{t('Belge')}</th>
              <th>{t('Müşteri')}</th>
              <th>{t('Ödeme')}</th>
              <th className="num">{t('Tutar')}</th>
            </tr>
          </thead>
          <tbody>
            {data.sales.map((sale) => (
              <tr key={sale.id}>
                <td>{formatDateTime(sale.sold_at).slice(-5)}</td>
                <td>{sale.sale_no}</td>
                <td>{sale.customer_name}</td>
                <td>{sale.payment_method ? PAYMENT_METHOD[sale.payment_method] : '—'}</td>
                <td className="num">{formatMoney(sale.amount)}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {data.stock_left.length > 0 && (
          <>
            <h3>{t('Araçta kalan mal')}</h3>
            <table>
              <tbody>
                {data.stock_left.map((row) => (
                  <tr key={row.lot_no}>
                    <td>{row.product_name}</td>
                    <td>{row.lot_no}</td>
                    <td className="num">{formatQty(row.qty, row.base_unit)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </>
        )}
        <div className="print-signatures">
          <div>{t('Teslim eden (kasa / satış elemanı)')}</div>
          <div>{t('Teslim alan (yönetici)')}</div>
        </div>
      </div>
    </>
  )
}

// --- Sayım tutanağı ---

function CountPrint({ id }: { id: number }) {
  const count = useQuery({ queryKey: ['stock-count', id], queryFn: () => api<StockCount>(`/stock-counts/${id}`) })
  if (!count.data) return <Loading error={count.error} />
  const data = count.data
  return (
    <>
      <Toolbar />
      <div className="print-sheet">
        <Head title={t('Sayım tutanağı')} number={data.count_no} date={formatDateTime(data.created_at)} />
        <p>
          <b>{t('Yer:')}</b> {data.warehouse_code} · <b>{t('Sayan:')}</b> {data.counted_by}
          {data.note && (
            <>
              {' '}
              · <b>{t('Not:')}</b> {data.note}
            </>
          )}
        </p>
        <table>
          <thead>
            <tr>
              <th>{t('Ürün')}</th>
              <th>{t('Lot')}</th>
              <th className="num">{t('Sistemde')}</th>
              <th className="num">{t('Sayılan')}</th>
              <th className="num">{t('Fark')}</th>
              <th className="num">{t('Eksik maliyeti')}</th>
            </tr>
          </thead>
          <tbody>
            {data.lines.map((line) => (
              <tr key={line.lot_no}>
                <td>{line.product_name}</td>
                <td>{line.lot_no}</td>
                <td className="num">{formatQty(line.system_qty, line.base_unit)}</td>
                <td className="num">{formatQty(line.counted_qty, line.base_unit)}</td>
                <td className="num">{formatQty(line.difference)}</td>
                <td className="num">{formatMoney(line.shortage_value)}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <p>{t('Eksikler "Sayım farkı" firesi olarak stoktan düşülmüştür. Fazla çıkan miktar stoka eklenmemiştir.')}</p>
        <div className="print-signatures">
          <div>{t('Sayan')}</div>
          <div>{t('Onaylayan')}</div>
        </div>
      </div>
    </>
  )
}

// --- Tatbikat raporu ---

function DrillPrint({ lotNo }: { lotNo: string }) {
  const { user } = useSession()
  const [drill, setDrill] = useState<Drill | null>(null)
  const [error, setError] = useState<unknown>(null)
  useEffect(() => {
    runDrill(lotNo).then(setDrill, setError)
  }, [lotNo])
  if (!drill) return <Loading error={error} />
  const measured = Number(new URLSearchParams(window.location.search).get('sure')) || drill.ms
  return (
    <>
      <Toolbar />
      <div className="print-sheet">
        <Head title={t('Geri çağırma tatbikatı raporu')} number={lotNo} date={formatDateTime(drill.at)} />
        <p>
          <b>{t('Yapan:')}</b> {user.full_name} · <b>{t('Bulma süresi:')}</b> {(measured / 1000).toFixed(2)} saniye (hedef 4 saat) ·{' '}
          <b>{t('Etkilenen lot:')}</b> {drill.forward.lots.length} · <b>{t('Müşteri:')}</b>{' '}
          {new Set(drill.forward.recipients.map((r) => r.customer_id)).size}
        </p>
        <p>{t('Tatbikatta hiçbir lot satışa kapatılmamıştır.')}</p>
        <DrillTables drill={drill} />
        <div className="print-signatures">
          <div>{t('Kalite sorumlusu')}</div>
          <div>{t('İşletme yöneticisi')}</div>
        </div>
      </div>
    </>
  )
}

function positiveId(raw: string): number | null {
  const id = Number(raw)
  return Number.isInteger(id) && id > 0 ? id : null
}

export default function PrintPage({ path }: { path: string }) {
  useEffect(() => {
    document.title = t('Yazdır — Synera')
  }, [])
  let params = matchPath('/yazdir/etiket/:lotNo', path)
  if (params) return <LabelPrint lotNo={params.lotNo} />
  params = matchPath('/yazdir/tatbikat/:lotNo', path)
  if (params) return <DrillPrint lotNo={params.lotNo} />
  params = matchPath('/yazdir/gun-sonu/:day', path)
  if (params && /^\d{4}-\d{2}-\d{2}$/.test(params.day)) return <DayEndPrint day={params.day} />
  for (const [pattern, Component] of [
    ['/yazdir/satis/:id', SalePrint],
    ['/yazdir/geri-cagirma/:id', RecallPrint],
    ['/yazdir/sayim/:id', CountPrint],
  ] as const) {
    const match = matchPath(pattern, path)
    const id = match && positiveId(match.id)
    if (id) return <Component id={id} />
  }
  return <Loading error={new Error(t('Yazdırılacak belge bulunamadı.'))} />
}
