// Yeni dış üretim emri (FR-105): dış üretici, mamul, planlanan miktar ve kullanılacak hammadde lotları.
// Lotlar yalnız ana depodaki bloke olmayan bakiyelerden seçilir. Ekrandaki maliyet plana göre
// ön izlemedir; gerçek EKP kabulde, tüketilen lotların gerçek değeriyle hesaplanır (FR-110).

import { useQueryClient } from '@tanstack/react-query'
import { Alert, App, Button, Card, Col, Descriptions, Flex, Form, Input, Row, Select, Typography } from 'antd'
import { useState } from 'react'
import { api, errorMessage } from '../api/client'
import { refreshBusinessData, usePartners, useProducts, useStock, useWarehouses } from '../api/queries'
import type { Order, OrderInput, StockRow } from '../api/types'
import { Page } from '../components/Page'
import { compare, divide, multiply, parseUserDecimal, sum } from '../lib/decimal'
import { formatDate, formatMoney, formatQty, formatUnitCost, unitLabel } from '../lib/format'
import { navigate } from '../lib/router'
import { decimalRule, toApiDecimal } from '../lib/rules'
import { t } from '../lib/i18n'

type InputValues = { lot_no?: string; qty?: string }
type FormValues = {
  subcontractor_id: number
  output_product_id: number
  planned_qty: string
  service_unit_price?: string
  inputs: InputValues[]
}

export default function ProductionNewPage() {
  const { message } = App.useApp()
  const queryClient = useQueryClient()
  const [form] = Form.useForm<FormValues>()
  const subcontractors = usePartners('subcontractor')
  const finishedGoods = useProducts('MAMUL')
  const warehouses = useWarehouses()
  const mainId = warehouses.data?.find((w) => w.kind === 'ANA')?.id
  const stock = useStock({ warehouse_id: mainId }, mainId !== undefined)
  const [error, setError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)

  const values = Form.useWatch((all: Partial<FormValues>) => all, form)
  const product = finishedGoods.data?.find((p) => p.id === values?.output_product_id)
  const available = (stock.data ?? []).filter((row) => row.lot_status === 'AKTIF')
  const byLot = new Map<string, StockRow>(available.map((row) => [row.lot_no, row]))

  // Plana göre maliyet ön izlemesi: lotların birim maliyeti × planlanan miktar.
  const planned = parseUserDecimal(values?.planned_qty ?? '', 3)
  const servicePrice = parseUserDecimal(values?.service_unit_price ?? '', 4)
  const rawCosts = (values?.inputs ?? []).flatMap((input) => {
    const row = byLot.get(input?.lot_no ?? '')
    const qty = parseUserDecimal(input?.qty ?? '', 3)
    return row && qty ? [multiply(qty, row.unit_cost, 2)] : []
  })
  const rawTotal = rawCosts.length ? sum(rawCosts, 2) : null
  const serviceTotal = planned && servicePrice ? multiply(planned, servicePrice, 2) : null
  const plannedTotal = rawTotal && serviceTotal ? sum([rawTotal, serviceTotal], 2) : null
  const plannedEkp = plannedTotal && planned && compare(planned, '0') > 0 ? divide(plannedTotal, planned, 6) : null

  async function finish(submitted: FormValues) {
    setSaving(true)
    setError(null)
    const body: OrderInput = {
      subcontractor_id: submitted.subcontractor_id,
      output_product_id: submitted.output_product_id,
      planned_qty: toApiDecimal(submitted.planned_qty, 3)!,
      service_unit_price: toApiDecimal(submitted.service_unit_price, 4),
      inputs: submitted.inputs.map((input) => ({ lot_no: input.lot_no!, qty: toApiDecimal(input.qty, 3)! })),
    }
    try {
      const order = await api<Order>('/production-orders', { method: 'POST', body })
      await refreshBusinessData(queryClient)
      message.success(t('{no} açıldı.', { no: order.order_no }))
      navigate(`/uretim/${order.id}`)
    } catch (caught) {
      setError(errorMessage(caught))
      setSaving(false)
      window.scrollTo(0, 0)
    }
  }

  return (
    <Page title={t('Yeni fason üretim emri')} back={{ to: '/uretim', label: t('Fason üretim') }}>
      {error && <Alert type="error" showIcon role="alert" title={error} style={{ marginBottom: 16 }} />}
      <Form<FormValues>
        form={form}
        layout="vertical"
        onFinish={finish}
        validateTrigger="onBlur"
        initialValues={{ inputs: [{}] }}
        scrollToFirstError
      >
        <Card title={t('Emir')} size="small" style={{ marginBottom: 16 }}>
          <Row gutter={16}>
            <Col xs={24} md={12}>
              <Form.Item
                label={t('Fasoncu')}
                name="subcontractor_id"
                rules={[{ required: true, message: t('Fasoncuyu seçin.') }]}
              >
                <Select
                  loading={subcontractors.isPending}
                  options={subcontractors.data?.map((p) => ({ value: p.id, label: p.name }))}
                />
              </Form.Item>
            </Col>
            <Col xs={24} md={12}>
              <Form.Item label={t('Mamul')} name="output_product_id" rules={[{ required: true, message: t('Mamul seçin.') }]}>
                <Select
                  loading={finishedGoods.isPending}
                  options={finishedGoods.data
                    ?.filter((p) => p.active)
                    .map((p) => ({ value: p.id, label: `${p.code} · ${p.name}` }))}
                />
              </Form.Item>
            </Col>
            <Col xs={24} sm={12}>
              <Form.Item
                label={t('Planlanan miktar')}
                name="planned_qty"
                dependencies={['output_product_id']}
                rules={[decimalRule(t('Planlanan miktar'), { maxFraction: 3, integer: product?.base_unit === 'ADET' })]}
              >
                <Input inputMode="decimal" autoComplete="off" suffix={<span>{product ? unitLabel(product.base_unit) : ''}</span>} />
              </Form.Item>
            </Col>
            <Col xs={24} sm={12}>
              <Form.Item
                label={t('Hizmet birim ücreti')}
                name="service_unit_price"
                extra={t('Fasoncunun birim başına işçilik ücreti (hammadde bedeli içermez).')}
                rules={[decimalRule(t('Hizmet birim ücreti'), { maxFraction: 4, required: false, allowZero: true })]}
              >
                <Input
                  inputMode="decimal"
                  autoComplete="off"
                  suffix={<span>{product ? `€ / ${unitLabel(product.base_unit)}` : '€'}</span>}
                />
              </Form.Item>
            </Col>
          </Row>
          {product && (
            <Descriptions
              size="small"
              column={{ xs: 1, sm: 3 }}
              items={[
                { key: 'vkp', label: t('Satış fiyatı'), children: formatMoney(product.sale_price) },
                {
                  key: 'weight',
                  label: t('1 adet'),
                  children: product.unit_weight_kg ? formatQty(product.unit_weight_kg, 'KG') : '—',
                },
                {
                  key: 'shelf',
                  label: t('Raf ömrü'),
                  children: product.shelf_life_days == null ? '—' : t('{n} gün', { n: product.shelf_life_days }),
                },
              ]}
            />
          )}
        </Card>

        <Card title={t('Kullanılacak hammadde lotları (ana depodan)')} size="small" style={{ marginBottom: 16 }}>
          <Form.List name="inputs">
            {(fields, { add, remove }) => (
              <>
                {fields.map((field) => {
                  const row = byLot.get(values?.inputs?.[field.name]?.lot_no ?? '')
                  return (
                    <Row gutter={8} key={field.key} align="top">
                      <Col xs={24} md={14}>
                        <Form.Item
                          label={t('Lot')}
                          name={[field.name, 'lot_no']}
                          rules={[
                            { required: true, message: t('Lot seçin.') },
                            {
                              validator: async (_rule, lotNo: string | undefined) => {
                                const chosen = (form.getFieldValue('inputs') as InputValues[]).filter(
                                  (input) => input?.lot_no === lotNo,
                                )
                                if (lotNo && chosen.length > 1) throw new Error(t('Bu lot emirde zaten var.'))
                              },
                            },
                          ]}
                        >
                          <Select
                            loading={stock.isPending}
                            showSearch={{ optionFilterProp: 'label' }}
                            options={available.map((item) => ({
                              value: item.lot_no,
                              label: `${item.lot_no} · ${item.product_name} · ${formatQty(item.qty, item.base_unit)} · ${formatUnitCost(item.unit_cost)}/${unitLabel(item.base_unit)} · SKT ${formatDate(item.expiry_date)}`,
                            }))}
                          />
                        </Form.Item>
                      </Col>
                      <Col xs={18} md={7}>
                        <Form.Item
                          label={t('Planlanan miktar')}
                          name={[field.name, 'qty']}
                          dependencies={[['inputs', field.name, 'lot_no']]}
                          rules={[
                            decimalRule(t('Miktar'), { maxFraction: 3 }),
                            {
                              validator: async (_rule, value: string | undefined) => {
                                const qty = parseUserDecimal(value ?? '', 3)
                                if (row && qty && compare(qty, row.qty) > 0) {
                                  throw new Error(`Ana depoda ${formatQty(row.qty, row.base_unit)} var.`)
                                }
                              },
                            },
                          ]}
                        >
                          <Input inputMode="decimal" autoComplete="off" suffix={<span>{row ? unitLabel(row.base_unit) : ''}</span>} />
                        </Form.Item>
                      </Col>
                      <Col xs={6} md={3}>
                        <Form.Item label=" ">
                          <Button disabled={fields.length === 1} onClick={() => remove(field.name)}>
                            {t('Sil')}
                          </Button>
                        </Form.Item>
                      </Col>
                    </Row>
                  )
                })}
                <Button size="small" onClick={() => add({})}>
                  {t('Lot ekle')}
                </Button>
              </>
            )}
          </Form.List>
        </Card>

        <Card title={t('Plana göre maliyet (ön izleme)')} size="small" style={{ marginBottom: 16 }}>
          <Descriptions
            size="small"
            column={{ xs: 1, sm: 2, lg: 4 }}
            items={[
              { key: 'raw', label: t('Hammadde'), children: formatMoney(rawTotal) },
              { key: 'service', label: t('Hizmet'), children: formatMoney(serviceTotal) },
              { key: 'total', label: t('Toplam'), children: formatMoney(plannedTotal) },
              { key: 'ekp', label: t('Planlanan birim maliyet'), children: formatUnitCost(plannedEkp) },
            ]}
          />
          <Typography.Text type="secondary">
            {t('Kesin birim maliyet, mamul kabulünde gerçekten tüketilen lotların değeri ve teslim alınan miktarla hesaplanır.')}
          </Typography.Text>
        </Card>

        <Flex gap="small">
          <Button type="primary" htmlType="submit" loading={saving}>
            {t('Emri oluştur')}
          </Button>
          <Button onClick={() => navigate('/uretim')}>{t('Vazgeç')}</Button>
        </Flex>
      </Form>
    </Page>
  )
}
