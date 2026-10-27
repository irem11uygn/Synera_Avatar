// Mağaza satışı: müşteri → ürünler → ödeme → kaydet. Lot elle seçilmez: miktar, son kullanma
// tarihi en yakın lottan başlayarak otomatik dağıtılır (FEFO). Süresi geçmiş ve geri çağrılmış lot
// hiç önerilmez; sunucu da reddeder.

import { DeleteOutlined, PlusOutlined, PrinterOutlined } from '@ant-design/icons'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Alert, Button, Empty, Input, Radio, Result, Select, Space, Table, Tag, Typography } from 'antd'
import { useMemo, useState } from 'react'
import { api, errorMessage } from '../api/client'
import { refreshBusinessData, usePartners, useProducts, useStock, useWarehouses } from '../api/queries'
import type { PaymentMethod, Product, Sale, StockRow } from '../api/types'
import { useSession } from '../auth/context'
import { Page } from '../components/Page'
import { QueryError } from '../components/QueryError'
import { compare, multiply, parseUserDecimal, sum } from '../lib/decimal'
import { allocate, type Pick } from '../lib/fefo'
import { formatDate, formatMoney, formatQty, todayIso } from '../lib/format'
import { options, PAYMENT_METHOD } from '../lib/labels'
import { can } from '../lib/roles'
import { navigate } from '../lib/router'

type Line = { key: number; product: Product; qtyText: string; priceText: string }

const SELLABLE_KINDS = new Set(['MAMUL', 'PARCA', 'YAN_URUN'])

function lotsOf(stock: StockRow[], productId: number) {
  return stock
    .filter((row) => row.product_id === productId)
    .map((row) => ({ lot_no: row.lot_no, qty: row.qty, expiry_date: row.expiry_date, blocked: row.lot_status === 'BLOKE' }))
}

type Checked = { line: Line; qty: string | null; price: string | null; picks: Pick[]; short: string; amount: string | null; problem: string | null }

function check(line: Line, stock: StockRow[], today: string): Checked {
  const qty = parseUserDecimal(line.qtyText, line.product.base_unit === 'ADET' ? 0 : 3)
  const price = parseUserDecimal(line.priceText, 2)
  let problem: string | null = null
  if (!qty || compare(qty, '0') <= 0)
    problem = line.product.base_unit === 'ADET' ? 'Adet tam sayı olmalı.' : 'Miktarı yazın (ör. 2,5).'
  else if (!price) problem = 'Birim fiyatı yazın.'
  const { picks, short } = qty ? allocate(lotsOf(stock, line.product.id), qty, today) : { picks: [], short: '0' }
  if (!problem && compare(short, '0') > 0)
    problem = `Satılabilir stok yetmiyor: ${formatQty(short, line.product.base_unit)} eksik.`
  const amount = qty && price ? multiply(qty, price, 2) : null
  return { line, qty, price, picks, short, amount, problem }
}

export default function StoreSalePage() {
  const { user } = useSession()
  const queryClient = useQueryClient()
  const warehouses = useWarehouses()
  const main = warehouses.data?.find((w) => w.kind === 'ANA')
  const stock = useStock({ warehouse_id: main?.id }, main !== undefined)
  const products = useProducts()
  const customers = usePartners('customer')
  const today = todayIso()

  const [customerId, setCustomerId] = useState<number | undefined>()
  const [lines, setLines] = useState<Line[]>([])
  const [payment, setPayment] = useState<PaymentMethod | undefined>()
  const [nextKey, setNextKey] = useState(1)
  const [saved, setSaved] = useState<Sale | null>(null)

  const defaultCustomer = customers.data?.find((c) => c.code === 'PERAKENDE')
  const chosenCustomer = customerId ?? defaultCustomer?.id

  // Satılabilir ürünler: mağazada (ana depo) satılabilir stoku olan mamul/parça/yan ürün.
  const available = useMemo(() => {
    const rows = stock.data ?? []
    return (products.data ?? []).filter(
      (p) =>
        p.active &&
        SELLABLE_KINDS.has(p.kind) &&
        allocate(lotsOf(rows, p.id), '0.001', today).short === '0',
    )
  }, [products.data, stock.data, today])

  const checked = lines.map((line) => check(line, stock.data ?? [], today))
  const total = sum(
    checked.map((c) => c.amount ?? '0'),
    2,
  )
  const ready = chosenCustomer !== undefined && lines.length > 0 && payment && checked.every((c) => !c.problem)
  const missing =
    chosenCustomer === undefined
      ? 'Müşteriyi seçin.'
      : lines.length === 0
        ? 'Ürün ekleyin.'
        : !payment
          ? 'Ödeme türünü seçin.'
          : null

  const save = useMutation({
    mutationFn: () =>
      api<Sale>('/sales', {
        method: 'POST',
        body: {
          customer_id: chosenCustomer,
          warehouse_id: main!.id,
          payment_method: payment,
          lines: checked.flatMap((c) => c.picks.map((p) => ({ lot_no: p.lot_no, qty: p.qty, unit_price: c.price }))),
        },
      }),
    onSuccess: async (sale) => {
      setSaved(sale)
      await refreshBusinessData(queryClient)
    },
  })

  function addProduct(productId: number) {
    const product = products.data?.find((p) => p.id === productId)
    if (!product) return
    setLines((current) => [
      ...current,
      { key: nextKey, product, qtyText: product.base_unit === 'ADET' ? '1' : '', priceText: product.sale_price?.replace('.', ',') ?? '' },
    ])
    setNextKey(nextKey + 1)
  }

  function update(key: number, patch: Partial<Line>) {
    setLines((current) => current.map((line) => (line.key === key ? { ...line, ...patch } : line)))
  }

  function reset() {
    setSaved(null)
    setLines([])
    setPayment(undefined)
    setCustomerId(undefined)
    save.reset()
  }

  if (!can(user.role, 'store')) {
    return (
      <Page title="Mağaza satışı">
        <Alert type="info" showIcon title="Mağaza satışını mağaza/kasa çalışanı ya da yönetici yapar." />
      </Page>
    )
  }

  if (saved) {
    return (
      <Page title="Mağaza satışı">
        <Result
          status="success"
          title={`Satış kaydedildi: ${saved.sale_no}`}
          subTitle={`${saved.customer_name} · ${formatMoney(saved.total_amount)} · ${PAYMENT_METHOD[saved.payment_method ?? 'NAKIT']}`}
          extra={[
            <Button key="print" type="primary" size="large" icon={<PrinterOutlined />} onClick={() => navigate(`/yazdir/satis/${saved.id}`)}>
              Fiş / irsaliye yazdır
            </Button>,
            <Button key="new" size="large" onClick={reset}>
              Yeni satış
            </Button>,
          ]}
        />
      </Page>
    )
  }

  const problem = warehouses.error ?? stock.error ?? products.error ?? customers.error

  return (
    <Page
      title="Mağaza satışı"
      description="Ürünü ekleyin, miktarı yazın. Lot otomatik seçilir: son kullanma tarihi en yakın olan önce satılır."
    >
      {problem && <QueryError error={problem} />}

      <div className="step-box">
        <div className="step-box-title">
          <span className="step-number">1</span> Müşteri
        </div>
        <Select
          showSearch={{ optionFilterProp: 'label' }}
          size="large"
          style={{ width: '100%', maxWidth: 480 }}
          value={chosenCustomer}
          onChange={setCustomerId}
          loading={customers.isPending}
          aria-label="Müşteri"
          placeholder="Müşteri seçin"
          options={(customers.data ?? []).map((c) => ({ value: c.id, label: c.name }))}
        />
        <div className="muted" style={{ marginTop: 6 }}>
          Adını bilmediğiniz peşin müşteri için "Perakende müşteri" seçili kalabilir.
        </div>
      </div>

      <div className="step-box">
        <div className="step-box-title">
          <span className="step-number">2</span> Ürünler
        </div>
        <Select
          showSearch={{ optionFilterProp: 'label' }}
          size="large"
          placeholder="Ürün ekle — adını yazmaya başlayın"
          style={{ width: '100%', maxWidth: 480, marginBottom: 16 }}
          value={null}
          onChange={(value: number) => addProduct(value)}
          loading={stock.isPending || products.isPending}
          aria-label="Ürün ekle"
          suffixIcon={<PlusOutlined />}
          options={available.map((p) => ({
            value: p.id,
            label: `${p.name}${p.sale_price ? ` — ${formatMoney(p.sale_price)} / ${p.base_unit === 'ADET' ? 'adet' : 'kg'}` : ''}`,
          }))}
          notFoundContent={stock.isPending ? 'Yükleniyor…' : 'Mağazada satılabilir stoku olan ürün yok.'}
        />
        {lines.length === 0 ? (
          <Empty description="Henüz ürün eklenmedi." image={Empty.PRESENTED_IMAGE_SIMPLE} />
        ) : (
          <Table<Checked>
            rowKey={(c) => c.line.key}
            pagination={false}
            dataSource={checked}
            scroll={{ x: 'max-content' }}
            columns={[
              {
                title: 'Ürün',
                render: (_, c) => (
                  <>
                    <Typography.Text strong>{c.line.product.name}</Typography.Text>
                    <div className="muted" style={{ fontSize: 13 }}>
                      {c.picks.length > 0
                        ? c.picks.map((p) => `${p.lot_no} (SKT ${formatDate(p.expiry_date)}): ${formatQty(p.qty)}`).join(' · ')
                        : '—'}
                    </div>
                    {c.problem &&
                      (c.line.qtyText.trim() ? (
                        <Tag color="red" style={{ marginTop: 4 }}>
                          {c.problem}
                        </Tag>
                      ) : (
                        <div className="muted">Miktarı yazın.</div>
                      ))}
                  </>
                ),
              },
              {
                title: 'Miktar',
                width: 150,
                render: (_, c) => (
                  <Input
                    value={c.line.qtyText}
                    inputMode="decimal"
                    suffix={c.line.product.base_unit === 'ADET' ? 'adet' : 'kg'}
                    onChange={(e) => update(c.line.key, { qtyText: e.target.value })}
                    aria-label={`${c.line.product.name} miktarı`}
                  />
                ),
              },
              {
                title: 'Birim fiyat',
                width: 150,
                render: (_, c) => (
                  <Input
                    value={c.line.priceText}
                    inputMode="decimal"
                    suffix="€"
                    onChange={(e) => update(c.line.key, { priceText: e.target.value })}
                    aria-label={`${c.line.product.name} birim fiyatı`}
                  />
                ),
              },
              { title: 'Tutar', align: 'right', render: (_, c) => <span className="num">{formatMoney(c.amount)}</span> },
              {
                title: '',
                width: 56,
                render: (_, c) => (
                  <Button
                    type="text"
                    danger
                    icon={<DeleteOutlined />}
                    aria-label={`${c.line.product.name} satırını sil`}
                    onClick={() => setLines((current) => current.filter((l) => l.key !== c.line.key))}
                  />
                ),
              },
            ]}
          />
        )}
      </div>

      <div className="step-box">
        <div className="step-box-title">
          <span className="step-number">3</span> Ödeme
        </div>
        <Radio.Group
          size="large"
          optionType="button"
          buttonStyle="solid"
          value={payment}
          onChange={(e) => setPayment(e.target.value)}
          options={options(PAYMENT_METHOD)}
          aria-label="Ödeme türü"
        />
        {payment === 'VERESIYE' && (
          <div className="muted" style={{ marginTop: 8 }}>
            Veresiye satış müşterinin hesabına yazılır; gün sonunda ayrı görünür.
          </div>
        )}
      </div>

      {save.isError && <Alert type="error" showIcon role="alert" title={errorMessage(save.error)} style={{ marginBottom: 16 }} />}
      <div className="total-bar">
        <div>
          <div className="muted">Toplam</div>
          <div className="total-bar-amount">{formatMoney(total)}</div>
        </div>
        <Space wrap>
          {missing && <Typography.Text type="secondary">{missing}</Typography.Text>}
          <Button type="primary" size="large" disabled={!ready} loading={save.isPending} onClick={() => save.mutate()}>
            Satışı kaydet
          </Button>
        </Space>
      </div>
    </Page>
  )
}
