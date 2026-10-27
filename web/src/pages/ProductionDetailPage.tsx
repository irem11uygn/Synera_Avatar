// Dış üretim emri ayrıntısı (FR-105…FR-111): sevk, mamul kabulü, miktar farkları ve EKP dökümü.
// Akış: Taslak → (sevk: girdiler dış üretici deposuna transfer) → Sevk edildi → (kabul) → Tamamlandı.

import { useQuery, useQueryClient } from '@tanstack/react-query'
import {
  Alert,
  App,
  Button,
  Card,
  Col,
  Descriptions,
  Form,
  Input,
  Popconfirm,
  Row,
  Spin,
  Statistic,
  Steps,
  Table,
  Typography,
  type TableColumnsType,
} from 'antd'
import { useState } from 'react'
import { api, errorMessage } from '../api/client'
import { refreshBusinessData, useProducts } from '../api/queries'
import type { CompleteInput, Order } from '../api/types'
import { ForecastCard } from '../components/ForecastCard'
import { Link } from '../components/Link'
import { Page } from '../components/Page'
import { QueryError } from '../components/QueryError'
import { OrderStatusTag } from '../components/StatusTags'
import { compare, multiply, parseUserDecimal, sum } from '../lib/decimal'
import { formatDateTime, formatMoney, formatPercent, formatQty, formatUnitCost, unitLabel } from '../lib/format'
import { decimalRule, fromApiDecimal, textOrNull, toApiDecimal } from '../lib/rules'
import { t } from '../lib/i18n'

type InputRow = Order['inputs'][number]

function inputColumns(completed: boolean): TableColumnsType<InputRow> {
  const columns: TableColumnsType<InputRow> = [
    { title: t('Lot'), dataIndex: 'lot_no', render: (lotNo: string) => <Link to={`/lotlar/${lotNo}`}>{lotNo}</Link> },
    { title: t('Hammadde'), dataIndex: 'product_name' },
    { title: t('Planlanan'), dataIndex: 'planned_qty', align: 'right', render: (v: string, row) => formatQty(v, row.base_unit) },
    { title: t('Sevk edilen'), dataIndex: 'shipped_qty', align: 'right', render: (v: string, row) => formatQty(v, row.base_unit) },
  ]
  if (!completed) return columns
  return [
    ...columns,
    { title: t('Tüketilen'), dataIndex: 'consumed_qty', align: 'right', render: (v: string, row) => formatQty(v, row.base_unit) },
    { title: t('İade edilen'), dataIndex: 'returned_qty', align: 'right', render: (v: string, row) => formatQty(v, row.base_unit) },
    { title: t('Tüketim değeri'), dataIndex: 'consumed_value', align: 'right', render: formatMoney },
  ]
}

function currentStep(order: Order): number {
  if (order.status === 'TAMAMLANDI') return 3 // son adımdan sonrası: üç adım da bitti
  if (order.status === 'SEVK_EDILDI') return 1
  return 0
}

export default function ProductionDetailPage({ id }: { id: number }) {
  const { message } = App.useApp()
  const queryClient = useQueryClient()
  const order = useQuery({ queryKey: ['order', id], queryFn: () => api<Order>(`/production-orders/${id}`) })
  const [busy, setBusy] = useState<'ship' | 'cancel' | null>(null)
  const [actionError, setActionError] = useState<string | null>(null)

  async function act(action: 'ship' | 'cancel', done: string) {
    setBusy(action)
    setActionError(null)
    try {
      await api<Order>(`/production-orders/${id}/${action}`, { method: 'POST' })
      await refreshBusinessData(queryClient)
      message.success(done)
    } catch (caught) {
      setActionError(errorMessage(caught))
    } finally {
      setBusy(null)
    }
  }

  if (order.isError) {
    return (
      <Page title={t('Fason üretim emri')}>
        <QueryError error={order.error} onRetry={() => order.refetch()} />
      </Page>
    )
  }
  if (order.isPending) return <Spin />

  const data = order.data
  const unit = data.base_unit
  const completed = data.status === 'TAMAMLANDI'

  const actions =
    data.status === 'TASLAK' ? (
      <>
        <Popconfirm
          title={t('Girdiler sevk edilsin mi?')}
          description={t('Hammadde lotları ana depodan {name} deposuna gönderilecek.', { name: data.subcontractor_name })}
          okText={t('Sevk et')}
          cancelText={t('Vazgeç')}
          onConfirm={() => act('ship', `${data.order_no} sevk edildi.`)}
        >
          <Button type="primary" loading={busy === 'ship'}>
            {t('Girdileri sevk et')}
          </Button>
        </Popconfirm>
        <Popconfirm
          title={t('Emir iptal edilsin mi?')}
          okText={t('İptal et')}
          cancelText={t('Vazgeç')}
          okButtonProps={{ danger: true }}
          onConfirm={() => act('cancel', `${data.order_no} iptal edildi.`)}
        >
          <Button danger loading={busy === 'cancel'}>
            {t('Emri iptal et')}
          </Button>
        </Popconfirm>
      </>
    ) : null

  return (
    <Page title={t('Fason üretim emri {no}', { no: data.order_no })} back={{ to: '/uretim', label: t('Fason üretim') }} extra={actions}>
      {actionError && <Alert type="error" showIcon role="alert" title={actionError} style={{ marginBottom: 16 }} />}

      <Card size="small" style={{ marginBottom: 16 }}>
        {data.status === 'IPTAL' ? (
          <Alert type="warning" showIcon title={t('Bu emir iptal edildi.')} />
        ) : (
          <Steps
            size="small"
            current={currentStep(data)}
            items={[
              { title: t('Taslak'), content: formatDateTime(data.ordered_at) },
              { title: t('Sevk edildi'), content: formatDateTime(data.shipped_at) },
              { title: t('Teslim alındı'), content: formatDateTime(data.completed_at) },
            ]}
          />
        )}
      </Card>

      <Card size="small" style={{ marginBottom: 16 }}>
        <Descriptions
          size="small"
          column={{ xs: 1, sm: 2, lg: 3 }}
          items={[
            { key: 'status', label: t('Durum'), children: <OrderStatusTag status={data.status} /> },
            { key: 'sub', label: t('Fasoncu'), children: data.subcontractor_name },
            { key: 'product', label: t('Mamul'), children: data.output_product_name },
            { key: 'planned', label: t('Planlanan'), children: formatQty(data.planned_qty, unit) },
            { key: 'received', label: t('Teslim alınan'), children: formatQty(data.received_qty, unit) },
            {
              key: 'diff',
              label: t('Miktar farkı (teslim − plan)'),
              children: data.quantity_difference == null ? '—' : formatQty(data.quantity_difference, unit),
            },
            {
              key: 'unit_price',
              label: t('Hizmet birim ücreti'),
              children: data.service_unit_price ? `${formatUnitCost(data.service_unit_price)} / ${unitLabel(unit)}` : '—',
            },
            { key: 'service', label: t('Hizmet faturası'), children: formatMoney(data.service_amount) },
            { key: 'invoice', label: t('Fatura no'), children: data.service_invoice_no ?? '—' },
            {
              key: 'lot',
              label: t('Mamul lotu'),
              children: data.output_lot_no ? <Link to={`/lotlar/${data.output_lot_no}`}>{data.output_lot_no}</Link> : '—',
            },
            ...(data.service_note ? [{ key: 'note', label: t('Fatura farkı açıklaması'), children: data.service_note }] : []),
          ]}
        />
      </Card>

      <ForecastCard order={data} />

      <Card size="small" title={t('Hammadde girdileri')} style={{ marginBottom: 16 }}>
        <Table<InputRow>
          rowKey="lot_no"
          size="small"
          columns={inputColumns(completed)}
          dataSource={data.inputs}
          pagination={false}
          scroll={{ x: 'max-content' }}
        />
      </Card>

      {data.status === 'SEVK_EDILDI' && <CompleteForm order={data} />}
      {completed && <CostBreakdown order={data} />}
    </Page>
  )
}

type CompleteValues = {
  received_qty: string
  // Satırlar emrin girdileriyle aynı sırada; lot numarası formda değil emirden alınır.
  inputs: { consumed_qty: string; returned_qty: string }[]
  service_amount?: string
  service_invoice_no?: string
  service_note?: string
  output_lot_no?: string
}

/** Mamul kabulü (FR-107…FR-109): teslim alınan miktar, tüketim/iade, hizmet faturası, mamul lotu. */
function CompleteForm({ order }: { order: Order }) {
  const { message } = App.useApp()
  const queryClient = useQueryClient()
  const [form] = Form.useForm<CompleteValues>()
  const products = useProducts('MAMUL')
  const [error, setError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)
  const unit = order.base_unit

  const received = parseUserDecimal(Form.useWatch('received_qty', form) ?? '', 3)
  const enteredAmount = Form.useWatch('service_amount', form)
  const suggested = received && order.service_unit_price ? multiply(received, order.service_unit_price, 2) : null
  const amount = enteredAmount?.trim() ? parseUserDecimal(enteredAmount, 2) : suggested
  const amountDiffers = suggested !== null && amount !== null && compare(amount, suggested) !== 0

  const product = products.data?.find((p) => p.id === order.output_product_id)
  const defaultLotNo = `${product?.lot_prefix || product?.code || ''}-${order.order_no.split('-').slice(1).join('-')}`

  async function finish(values: CompleteValues) {
    setSaving(true)
    setError(null)
    const body: CompleteInput = {
      received_qty: toApiDecimal(values.received_qty, 3)!,
      inputs: values.inputs.map((input, index) => ({
        lot_no: order.inputs[index].lot_no,
        consumed_qty: toApiDecimal(input.consumed_qty, 3) ?? '0',
        returned_qty: toApiDecimal(input.returned_qty, 3) ?? '0',
      })),
      service_amount: toApiDecimal(values.service_amount, 2),
      service_invoice_no: textOrNull(values.service_invoice_no),
      service_note: textOrNull(values.service_note),
      output_lot_no: textOrNull(values.output_lot_no),
    }
    try {
      const done = await api<Order>(`/production-orders/${order.id}/complete`, { method: 'POST', body })
      await refreshBusinessData(queryClient)
      message.success(`Mamul kabul edildi: ${done.output_lot_no}, birim maliyet ${formatUnitCost(done.cost?.ekp_display)}.`)
    } catch (caught) {
      setError(errorMessage(caught))
      setSaving(false)
    }
  }

  return (
    <Card size="small" title={t('Mamul kabulü')} style={{ marginBottom: 16 }}>
      {error && <Alert type="error" showIcon role="alert" title={error} style={{ marginBottom: 16 }} />}
      <Form<CompleteValues>
        form={form}
        layout="vertical"
        onFinish={finish}
        validateTrigger="onBlur"
        scrollToFirstError
        initialValues={{
          inputs: order.inputs.map((input) => ({
            consumed_qty: fromApiDecimal(input.shipped_qty),
            returned_qty: '0',
          })),
        }}
      >
        <Row gutter={16}>
          <Col xs={24} sm={12} md={8}>
            <Form.Item
              label={t('Teslim alınan miktar')}
              name="received_qty"
              extra={`Planlanan: ${formatQty(order.planned_qty, unit)}`}
              rules={[decimalRule(t('Teslim alınan miktar'), { maxFraction: 3, integer: unit === 'ADET' })]}
            >
              <Input inputMode="decimal" autoComplete="off" suffix={unitLabel(unit)} />
            </Form.Item>
          </Col>
          <Col xs={24} sm={12} md={8}>
            <Form.Item label={t('Mamul lot no')} name="output_lot_no" extra={t('Boş bırakılırsa {lot}', { lot: defaultLotNo })}>
              <Input maxLength={40} autoComplete="off" spellCheck={false} placeholder={defaultLotNo} />
            </Form.Item>
          </Col>
        </Row>

        <Typography.Title level={5}>{t('Hammadde tüketimi')}</Typography.Title>
        <Typography.Paragraph type="secondary">
          {t('Her lot için tüketilen + iade edilen = sevk edilen olmalı. İade edilen miktar ana depoya geri döner.')}
        </Typography.Paragraph>
        <Form.List name="inputs">
          {(fields) =>
            fields.map((field) => {
              const input = order.inputs[field.name]
              return (
                <Row gutter={8} key={field.key} align="top">
                  <Col xs={24} md={8}>
                    <Form.Item label={t('Lot')}>
                      <Typography.Text>
                        {input.lot_no} · {input.product_name} · sevk {formatQty(input.shipped_qty, input.base_unit)}
                      </Typography.Text>
                    </Form.Item>
                  </Col>
                  <Col xs={12} md={8}>
                    <Form.Item
                      label={t('Tüketilen')}
                      name={[field.name, 'consumed_qty']}
                      rules={[decimalRule(t('Tüketilen'), { maxFraction: 3, allowZero: true })]}
                    >
                      <Input inputMode="decimal" autoComplete="off" suffix={unitLabel(input.base_unit)} />
                    </Form.Item>
                  </Col>
                  <Col xs={12} md={8}>
                    <Form.Item
                      label={t('İade edilen')}
                      name={[field.name, 'returned_qty']}
                      dependencies={[['inputs', field.name, 'consumed_qty']]}
                      rules={[
                        decimalRule(t('İade edilen'), { maxFraction: 3, allowZero: true }),
                        {
                          validator: async (_rule, value: string | undefined) => {
                            const consumed = parseUserDecimal(form.getFieldValue(['inputs', field.name, 'consumed_qty']) ?? '', 3)
                            const returned = parseUserDecimal(value ?? '', 3)
                            if (consumed && returned && compare(sum([consumed, returned], 3), input.shipped_qty) !== 0) {
                              throw new Error(
                                t('Tüketilen + iade edilen, sevk edilen {qty} olmalı.', { qty: formatQty(input.shipped_qty, input.base_unit) }),
                              )
                            }
                          },
                        },
                      ]}
                    >
                      <Input inputMode="decimal" autoComplete="off" suffix={unitLabel(input.base_unit)} />
                    </Form.Item>
                  </Col>
                </Row>
              )
            })
          }
        </Form.List>

        <Typography.Title level={5}>{t('Hizmet faturası')}</Typography.Title>
        <Row gutter={16}>
          <Col xs={24} sm={12} md={8}>
            <Form.Item
              label={t('Fatura tutarı')}
              name="service_amount"
              extra={
                suggested
                  ? t('Boşsa teslim alınan × birim ücret = {amount}', { amount: formatMoney(suggested) })
                  : order.service_unit_price
                    ? t('Teslim alınan miktarı girince önerilen tutar hesaplanır.')
                    : t('Emirde birim ücret yok; tutar zorunlu.')
              }
              rules={[
                decimalRule(t('Fatura tutarı'), {
                  maxFraction: 2,
                  required: !order.service_unit_price,
                  allowZero: true,
                }),
              ]}
            >
              <Input inputMode="decimal" autoComplete="off" suffix="€" />
            </Form.Item>
          </Col>
          <Col xs={24} sm={12} md={8}>
            <Form.Item label={t('Fatura no')} name="service_invoice_no">
              <Input maxLength={50} autoComplete="off" spellCheck={false} />
            </Form.Item>
          </Col>
          <Col xs={24} md={8}>
            <Form.Item
              label={t('Fark açıklaması')}
              name="service_note"
              dependencies={['service_amount', 'received_qty']}
              rules={[
                {
                  validator: async (_rule, value: string | undefined) => {
                    if (amountDiffers && !value?.trim()) {
                      throw new Error(t('Fatura önerilen tutardan farklı; nedenini yazın.'))
                    }
                  },
                },
              ]}
            >
              <Input maxLength={500} autoComplete="off" />
            </Form.Item>
          </Col>
        </Row>
        {amountDiffers && (
          <Alert
            type="warning"
            showIcon
            style={{ marginBottom: 16 }}
            title={t('Fatura ({amount}) önerilen tutardan ({suggested}) farklı; açıklama zorunlu.', { amount: formatMoney(amount), suggested: formatMoney(suggested) })}
          />
        )}
        <Button type="primary" htmlType="submit" loading={saving}>
          {t('Mamulü kabul et')}
        </Button>
      </Form>
    </Card>
  )
}

/** EKP dökümü (FR-110, FR-111): saklanan tam değer ve gösterim, lot değeri, kâr ve marj, verim. */
function CostBreakdown({ order }: { order: Order }) {
  const cost = order.cost
  if (!cost) return null
  const unit = order.base_unit
  const suggestedService =
    order.received_qty && order.service_unit_price ? multiply(order.received_qty, order.service_unit_price, 2) : null
  const serviceFormula = `${formatQty(order.received_qty, unit)} × ${formatUnitCost(order.service_unit_price)}`
  const serviceDetail =
    suggestedService === null
      ? t('fatura {no}', { no: order.service_invoice_no ?? '' }).trim()
      : compare(suggestedService, cost.service) === 0
        ? serviceFormula
        : t('fatura {no} · önerilen {formula} = {amount}', { no: order.service_invoice_no ?? '', formula: serviceFormula, amount: formatMoney(suggestedService) })

  const rows = [
    ...order.inputs
      .filter((input) => compare(input.consumed_qty, '0') > 0)
      .map((input) => ({
        key: input.lot_no,
        label: `${input.product_name} (${input.lot_no})`,
        detail: t('{qty} tüketildi', { qty: formatQty(input.consumed_qty, input.base_unit) }),
        amount: input.consumed_value,
      })),
    {
      key: 'service',
      label: t('Fason işçilik'),
      detail: serviceDetail,
      amount: cost.service,
    },
  ]

  return (
    <>
      <Row gutter={16}>
        <Col xs={24} sm={12} lg={6}>
          <Card size="small" style={{ marginBottom: 16 }}>
            <Statistic title={t('Toplam maliyet (lot değeri)')} value={formatMoney(cost.total)} />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card size="small" style={{ marginBottom: 16 }}>
            <Statistic title={`Birim maliyet — EKP (€ / ${unitLabel(unit)})`} value={formatUnitCost(cost.ekp_display)} />
            <Typography.Text type="secondary">{t('Saklanan tam değer: {v}', { v: formatUnitCost(cost.ekp) })}</Typography.Text>
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card size="small" style={{ marginBottom: 16 }}>
            <Statistic title={t('Brüt kâr / birim')} value={formatMoney(order.sales?.gross_profit_per_unit)} />
            <Typography.Text type="secondary">{t('Satış fiyatı {v}', { v: formatMoney(order.sales?.vkp) })}</Typography.Text>
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card size="small" style={{ marginBottom: 16 }}>
            <Statistic title={t('Marj (brüt kâr / satış fiyatı)')} value={formatPercent(order.sales?.margin_pct)} />
          </Card>
        </Col>
      </Row>

      <Row gutter={16}>
        <Col xs={24} lg={14}>
          <Card size="small" title={t('Birim maliyet nasıl hesaplandı?')} style={{ marginBottom: 16 }}>
            <Table
              rowKey="key"
              size="small"
              pagination={false}
              dataSource={rows}
              columns={[
                { title: t('Kalem'), dataIndex: 'label' },
                { title: t('Ayrıntı'), dataIndex: 'detail' },
                { title: t('Tutar'), dataIndex: 'amount', align: 'right', render: formatMoney },
              ]}
              summary={() => (
                <>
                  <Table.Summary.Row>
                    <Table.Summary.Cell index={0} colSpan={2}>
                      <Typography.Text strong>{t('Toplam maliyet')}</Typography.Text>
                    </Table.Summary.Cell>
                    <Table.Summary.Cell index={2} align="right">
                      <Typography.Text strong>{formatMoney(cost.total)}</Typography.Text>
                    </Table.Summary.Cell>
                  </Table.Summary.Row>
                  <Table.Summary.Row>
                    <Table.Summary.Cell index={0} colSpan={2}>
                      {t('÷ Teslim alınan {qty} = birim maliyet', { qty: formatQty(order.received_qty, unit) })}
                    </Table.Summary.Cell>
                    <Table.Summary.Cell index={2} align="right">
                      <Typography.Text strong>{formatUnitCost(cost.ekp_display)}</Typography.Text>
                    </Table.Summary.Cell>
                  </Table.Summary.Row>
                </>
              )}
            />
            <Typography.Paragraph type="secondary" style={{ marginTop: 12, marginBottom: 0 }}>
              {t('Lot değeri toplam maliyettir ({total}). Birim maliyet {exact} olarak saklanır, ekranda {shown} gösterilir; satış maliyetleri lot değerinden dağıtıldığı için yuvarlama farkı oluşmaz.', {
                total: formatMoney(cost.total),
                exact: formatUnitCost(cost.ekp),
                shown: formatUnitCost(cost.ekp_display),
              })}
            </Typography.Paragraph>
          </Card>
        </Col>
        <Col xs={24} lg={10}>
          <Card size="small" title={t('Verim')} style={{ marginBottom: 16 }}>
            {order.yield ? (
              <Descriptions
                size="small"
                column={1}
                items={[
                  { key: 'out', label: t('Mamul (kg)'), children: formatQty(order.yield.output_kg, 'KG') },
                  { key: 'main', label: t('Ana hammadde (kg)'), children: formatQty(order.yield.main_input_kg, 'KG') },
                  { key: 'all', label: t('Bütün girdiler (kg)'), children: formatQty(order.yield.inputs_kg, 'KG') },
                  { key: 'ymain', label: t('Et bazlı verim'), children: formatPercent(order.yield.yield_main_pct) },
                  { key: 'yall', label: t('Toplam girdi verimi'), children: formatPercent(order.yield.yield_total_pct) },
                ]}
              />
            ) : (
              <Typography.Text type="secondary">{t('Verim hesaplanamadı (ağırlık bilgisi eksik).')}</Typography.Text>
            )}
          </Card>
        </Col>
      </Row>
    </>
  )
}
