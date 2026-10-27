// Yeni hammadde alışı (FR-102, FR-203, FR-207). Lot numarası tedarikçinin etiketinden elle girilir.
// Ekrandaki "miktar × fiyat" ve "lot değeri" yalnız ön izlemedir; kesin hesap sunucudadır.

import { useQueryClient } from '@tanstack/react-query'
import { Alert, App, Button, Card, Col, Flex, Form, Input, Row, Select, Space, Typography } from 'antd'
import type { FormInstance } from 'antd'
import { useState } from 'react'
import { api, errorMessage } from '../api/client'
import { refreshBusinessData, usePartners, useProducts } from '../api/queries'
import type { Product, Purchase, PurchaseCostKind, PurchaseInput } from '../api/types'
import { Page } from '../components/Page'
import { compare, multiply, parseUserDecimal, sum } from '../lib/decimal'
import { formatMoney, todayIso, unitLabel } from '../lib/format'
import { options, PURCHASE_COST_KIND } from '../lib/labels'
import { navigate } from '../lib/router'
import { decimalRule, fromApiDecimal, textOrNull, toApiDecimal } from '../lib/rules'

type CostValues = { kind: PurchaseCostKind; amount: string; note?: string }
type LineValues = {
  product_id?: number
  lot_no?: string
  qty?: string
  unit_price?: string
  invoice_amount?: string
  discrepancy_note?: string
  expiry_date?: string
  extra_costs?: CostValues[]
}
type FormValues = { supplier_id: number; doc_no: string; doc_date: string; note?: string; lines: LineValues[] }

function toInput(values: FormValues): PurchaseInput {
  return {
    supplier_id: values.supplier_id,
    doc_no: values.doc_no.trim(),
    doc_date: values.doc_date,
    note: textOrNull(values.note),
    lines: values.lines.map((line) => ({
      product_id: line.product_id!,
      lot_no: line.lot_no!.trim(),
      qty: toApiDecimal(line.qty, 3)!,
      unit_price: toApiDecimal(line.unit_price, 4)!,
      invoice_amount: toApiDecimal(line.invoice_amount, 2),
      discrepancy_note: textOrNull(line.discrepancy_note),
      expiry_date: line.expiry_date || null,
      extra_costs: (line.extra_costs ?? []).map((cost) => ({
        kind: cost.kind,
        amount: toApiDecimal(cost.amount, 2)!,
        note: textOrNull(cost.note),
      })),
    })),
  }
}

/** Satır ön izlemesi: miktar × fiyat (kuruşa yuvarlı), fatura farkı, lot değeri. Eksik girişte null. */
function preview(line: LineValues | undefined) {
  const qty = parseUserDecimal(line?.qty ?? '', 3)
  const price = parseUserDecimal(line?.unit_price ?? '', 4)
  if (!qty || !price) return null
  const computed = multiply(qty, price, 2)
  const invoice = line?.invoice_amount?.trim() ? parseUserDecimal(line.invoice_amount, 2) : computed
  if (invoice === null) return null
  const costs = (line?.extra_costs ?? []).map((c) => parseUserDecimal(c?.amount ?? '', 2) ?? '0')
  return { computed, invoice, mismatch: compare(invoice, computed) !== 0, lotValue: sum([invoice, ...costs], 2) }
}

function addDays(isoDate: string, days: number): string {
  const date = new Date(`${isoDate}T00:00:00Z`)
  date.setUTCDate(date.getUTCDate() + days)
  return date.toISOString().slice(0, 10)
}

export default function PurchaseNewPage() {
  const { message } = App.useApp()
  const queryClient = useQueryClient()
  const [form] = Form.useForm<FormValues>()
  const suppliers = usePartners('supplier')
  const products = useProducts()
  const [error, setError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)

  async function finish(values: FormValues) {
    setSaving(true)
    setError(null)
    try {
      const purchase = await api<Purchase>('/purchases', { method: 'POST', body: toInput(values) })
      await refreshBusinessData(queryClient)
      message.success(`${purchase.doc_no} kaydedildi: ${purchase.lines.length} lot açıldı.`)
      navigate('/alislar')
    } catch (caught) {
      setError(errorMessage(caught))
      setSaving(false)
      window.scrollTo(0, 0)
    }
  }

  return (
    <Page title="Yeni mal kabul" back={{ to: '/alislar', label: 'Mal kabul' }}>
      {error && <Alert type="error" showIcon role="alert" title={error} style={{ marginBottom: 16 }} />}
      <Form<FormValues>
        form={form}
        layout="vertical"
        onFinish={finish}
        validateTrigger="onBlur"
        initialValues={{ doc_date: todayIso(), lines: [{ extra_costs: [] }] }}
        scrollToFirstError
      >
        <Card title="Belge" size="small" style={{ marginBottom: 16 }}>
          <Row gutter={16}>
            <Col xs={24} md={8}>
              <Form.Item label="Tedarikçi" name="supplier_id" rules={[{ required: true, message: 'Tedarikçi seçin.' }]}>
                <Select
                  loading={suppliers.isPending}
                  showSearch={{ optionFilterProp: 'label' }}
                  options={suppliers.data?.map((s) => ({ value: s.id, label: s.name }))}
                />
              </Form.Item>
            </Col>
            <Col xs={24} sm={12} md={8}>
              <Form.Item
                label="Fatura / irsaliye no"
                name="doc_no"
                rules={[{ required: true, whitespace: true, message: 'Belge numarası gerekli.' }]}
              >
                <Input maxLength={50} autoComplete="off" spellCheck={false} />
              </Form.Item>
            </Col>
            <Col xs={24} sm={12} md={8}>
              <Form.Item label="Belge tarihi" name="doc_date" rules={[{ required: true, message: 'Tarih gerekli.' }]}>
                <Input type="date" />
              </Form.Item>
            </Col>
            <Col span={24}>
              <Form.Item label="Not" name="note">
                <Input maxLength={255} autoComplete="off" />
              </Form.Item>
            </Col>
          </Row>
        </Card>

        <Form.List name="lines">
          {(fields, { add, remove }) => (
            <>
              {fields.map((field, index) => (
                <PurchaseLine
                  key={field.key}
                  form={form}
                  name={field.name}
                  index={index}
                  products={products.data ?? []}
                  onRemove={fields.length > 1 ? () => remove(field.name) : undefined}
                />
              ))}
              <Button onClick={() => add({ extra_costs: [] })} style={{ marginBottom: 16 }}>
                Satır ekle
              </Button>
            </>
          )}
        </Form.List>

        <Flex gap="small">
          <Button type="primary" htmlType="submit" loading={saving}>
            Alışı kaydet
          </Button>
          <Button onClick={() => navigate('/alislar')}>Vazgeç</Button>
        </Flex>
      </Form>
    </Page>
  )
}

type LineProps = {
  form: FormInstance<FormValues>
  name: number
  index: number
  products: Product[]
  onRemove?: () => void
}

function PurchaseLine({ form, name, index, products, onRemove }: LineProps) {
  const line = Form.useWatch(['lines', name], form)
  const product = products.find((p) => p.id === line?.product_id)
  const shown = preview(line)

  function chooseProduct(productId: number) {
    const chosen = products.find((p) => p.id === productId)
    if (!chosen) return
    const current = form.getFieldValue(['lines', name]) as LineValues
    const docDate = form.getFieldValue('doc_date') as string | undefined
    form.setFieldValue(['lines', name], {
      ...current,
      unit_price: current.unit_price || fromApiDecimal(chosen.default_purchase_price),
      expiry_date:
        current.expiry_date ||
        (docDate && chosen.shelf_life_days != null ? addDays(docDate, chosen.shelf_life_days) : undefined),
    })
  }

  return (
    <Card
      size="small"
      title={`Satır ${index + 1}`}
      style={{ marginBottom: 16 }}
      extra={
        onRemove && (
          <Button size="small" danger onClick={onRemove}>
            Satırı sil
          </Button>
        )
      }
    >
      <Row gutter={16}>
        <Col xs={24} md={8}>
          <Form.Item label="Ürün" name={[name, 'product_id']} rules={[{ required: true, message: 'Ürün seçin.' }]}>
            <Select
              showSearch={{ optionFilterProp: 'label' }}
              onChange={chooseProduct}
              options={products.filter((p) => p.active).map((p) => ({ value: p.id, label: `${p.code} · ${p.name}` }))}
            />
          </Form.Item>
        </Col>
        <Col xs={24} sm={12} md={8}>
          <Form.Item
            label="Lot no"
            name={[name, 'lot_no']}
            extra="Tedarikçinin lot / parti numarası."
            rules={[{ required: true, whitespace: true, message: 'Lot numarası zorunlu.' }]}
          >
            <Input maxLength={40} autoComplete="off" spellCheck={false} />
          </Form.Item>
        </Col>
        <Col xs={24} sm={12} md={8}>
          <Form.Item label="Son kullanma tarihi" name={[name, 'expiry_date']}>
            <Input type="date" />
          </Form.Item>
        </Col>
        <Col xs={24} sm={8}>
          <Form.Item label="Miktar" name={[name, 'qty']} rules={[decimalRule('Miktar', { maxFraction: 3 })]}>
            {/* Sonek her zaman var: sonradan eklenirse giriş kutusu yeniden kurulur ve odak kaybolur. */}
            <Input inputMode="decimal" autoComplete="off" suffix={<span>{product ? unitLabel(product.base_unit) : ''}</span>} />
          </Form.Item>
        </Col>
        <Col xs={24} sm={8}>
          <Form.Item
            label="Birim fiyat"
            name={[name, 'unit_price']}
            rules={[decimalRule('Birim fiyat', { maxFraction: 4, allowZero: true })]}
          >
            <Input inputMode="decimal" autoComplete="off" suffix="€" />
          </Form.Item>
        </Col>
        <Col xs={24} sm={8}>
          <Form.Item
            label="Fatura tutarı"
            name={[name, 'invoice_amount']}
            extra="Boşsa miktar × fiyat alınır."
            rules={[decimalRule('Fatura tutarı', { maxFraction: 2, required: false, allowZero: true })]}
          >
            <Input inputMode="decimal" autoComplete="off" suffix="€" />
          </Form.Item>
        </Col>
        <Col span={24}>
          <Form.Item
            label="Fark açıklaması"
            name={[name, 'discrepancy_note']}
            dependencies={[['lines', name, 'invoice_amount'], ['lines', name, 'qty'], ['lines', name, 'unit_price']]}
            rules={[
              {
                validator: async (_rule, value: string | undefined) => {
                  if (preview(form.getFieldValue(['lines', name]))?.mismatch && !value?.trim()) {
                    throw new Error('Fatura tutarı miktar × fiyattan farklı; farkın nedenini yazın.')
                  }
                },
              },
            ]}
          >
            <Input maxLength={500} autoComplete="off" placeholder="ör. kesim ve nakliye dahil" />
          </Form.Item>
        </Col>
      </Row>

      <Form.List name={[name, 'extra_costs']}>
        {(costs, { add, remove }) => (
          <>
            {costs.map((cost) => (
              <Row gutter={8} key={cost.key} align="top">
                <Col xs={24} sm={6}>
                  <Form.Item label="Ek maliyet" name={[cost.name, 'kind']} rules={[{ required: true, message: 'Tür seçin.' }]}>
                    <Select options={options(PURCHASE_COST_KIND)} />
                  </Form.Item>
                </Col>
                <Col xs={24} sm={6}>
                  <Form.Item label="Tutar" name={[cost.name, 'amount']} rules={[decimalRule('Tutar', { maxFraction: 2 })]}>
                    <Input inputMode="decimal" autoComplete="off" suffix="€" />
                  </Form.Item>
                </Col>
                <Col xs={20} sm={10}>
                  <Form.Item label="Açıklama" name={[cost.name, 'note']}>
                    <Input maxLength={255} autoComplete="off" />
                  </Form.Item>
                </Col>
                <Col xs={4} sm={2}>
                  <Form.Item label=" ">
                    <Button aria-label="Ek maliyeti sil" onClick={() => remove(cost.name)}>
                      Sil
                    </Button>
                  </Form.Item>
                </Col>
              </Row>
            ))}
            <Button size="small" onClick={() => add({ kind: 'NAKLIYE' })}>
              Ek maliyet ekle (kesim, nakliye…)
            </Button>
          </>
        )}
      </Form.List>

      <div aria-live="polite" style={{ marginTop: 12 }}>
        {shown && (
          <Space size="large" wrap>
            <Typography.Text>Miktar × fiyat: {formatMoney(shown.computed)}</Typography.Text>
            {shown.mismatch && <Typography.Text type="warning">Fatura farklı: {formatMoney(shown.invoice)}</Typography.Text>}
            <Typography.Text strong>Lot değeri (ön izleme): {formatMoney(shown.lotValue)}</Typography.Text>
          </Space>
        )}
      </div>
    </Card>
  )
}
