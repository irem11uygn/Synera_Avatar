// Depolar arası transfer (FR-303): ör. satış aracına yükleme. Transfer değer taşımaz; lotun
// değeri değişmez, yalnız bulunduğu depo değişir. Dış üretim sevk ve iadeleri emirden otomatik yazılır.

import { useQuery, useQueryClient } from '@tanstack/react-query'
import { App, Button, Col, Form, Input, Row, Select, Table, Typography, type TableColumnsType } from 'antd'
import { useState } from 'react'
import { api } from '../api/client'
import { refreshBusinessData, useStock, useWarehouses } from '../api/queries'
import type { StockRow, Transfer, TransferInput, TransferReason } from '../api/types'
import { FormModal } from '../components/FormModal'
import { Link } from '../components/Link'
import { Page } from '../components/Page'
import { QueryError } from '../components/QueryError'
import { compare, parseUserDecimal } from '../lib/decimal'
import { formatDate, formatDateTime, formatQty, unitLabel } from '../lib/format'
import { TRANSFER_REASON } from '../lib/labels'
import { decimalRule, toApiDecimal } from '../lib/rules'
import { t } from '../lib/i18n'

type LineValues = { lot_no?: string; qty?: string }
type FormValues = {
  from_warehouse_id: number
  to_warehouse_id: number
  reason: TransferReason
  lines: LineValues[]
}

const MANUAL_REASONS: TransferReason[] = ['ARAC_YUKLEME', 'DIGER']

const COLUMNS: TableColumnsType<Transfer> = [
  { title: t('Belge no'), dataIndex: 'transfer_no' },
  { title: t('Zaman'), dataIndex: 'transferred_at', render: formatDateTime },
  { title: t('Çıkış'), dataIndex: 'from_warehouse_code' },
  { title: t('Giriş'), dataIndex: 'to_warehouse_code' },
  {
    title: t('Neden'),
    dataIndex: 'reason',
    render: (reason: TransferReason, row) =>
      row.production_order_id ? (
        <Link to={`/uretim/${row.production_order_id}`}>{TRANSFER_REASON[reason]}</Link>
      ) : (
        TRANSFER_REASON[reason]
      ),
  },
  {
    title: t('Lotlar'),
    dataIndex: 'lines',
    render: (lines: Transfer['lines']) =>
      lines.map((line) => (
        <div key={line.lot_no}>
          <Link to={`/lotlar/${line.lot_no}`}>{line.lot_no}</Link>: {formatQty(line.qty)}
        </div>
      )),
  },
]

export default function TransfersPage() {
  const { message } = App.useApp()
  const queryClient = useQueryClient()
  const transfers = useQuery({ queryKey: ['transfers'], queryFn: () => api<Transfer[]>('/transfers') })
  const warehouses = useWarehouses()
  const [open, setOpen] = useState(false)

  const main = warehouses.data?.find((w) => w.kind === 'ANA')
  const van = warehouses.data?.find((w) => w.kind === 'ARAC')

  async function save(values: FormValues) {
    const body: TransferInput = {
      from_warehouse_id: values.from_warehouse_id,
      to_warehouse_id: values.to_warehouse_id,
      reason: values.reason,
      lines: values.lines.map((line) => ({ lot_no: line.lot_no!, qty: toApiDecimal(line.qty, 3)! })),
    }
    const transfer = await api<Transfer>('/transfers', { method: 'POST', body })
    await refreshBusinessData(queryClient)
    message.success(`${transfer.transfer_no} kaydedildi.`)
  }

  return (
    <Page
      title={t('Araca yükleme ve depo aktarma')}
      description={t('Satış aracına mal yükleyin ya da depolar arasında mal taşıyın. Telefon uygulaması araç stokunu bir sonraki eşitlemede alır.')}
      extra={
        <Button type="primary" onClick={() => setOpen(true)} disabled={!warehouses.data}>
          {t('Yeni yükleme / aktarma')}
        </Button>
      }
    >
      {transfers.isError && <QueryError error={transfers.error} onRetry={() => transfers.refetch()} />}
      <Table<Transfer>
        rowKey="id"
        size="middle"
        loading={transfers.isPending}
        columns={COLUMNS}
        dataSource={transfers.data}
        pagination={{ pageSize: 50, hideOnSinglePage: true }}
        scroll={{ x: 'max-content' }}
      />
      <FormModal<FormValues>
        title={t('Yeni yükleme / aktarma')}
        open={open}
        onClose={() => setOpen(false)}
        initialValues={{ from_warehouse_id: main?.id, to_warehouse_id: van?.id, reason: 'ARAC_YUKLEME', lines: [{}] }}
        onSubmit={save}
        width={720}
      >
        <TransferFields />
      </FormModal>
    </Page>
  )
}

function TransferFields() {
  const form = Form.useFormInstance<FormValues>()
  const warehouses = useWarehouses()
  const fromId = Form.useWatch('from_warehouse_id', form)
  const lines = Form.useWatch('lines', form)
  const stock = useStock({ warehouse_id: fromId }, fromId !== undefined)
  const available = (stock.data ?? []).filter((row) => row.lot_status === 'AKTIF')
  const byLot = new Map<string, StockRow>(available.map((row) => [row.lot_no, row]))
  const warehouseOptions = warehouses.data?.map((w) => ({ value: w.id, label: w.name }))

  return (
    <>
      <Row gutter={16}>
        <Col xs={24} sm={8}>
          <Form.Item label={t('Çıkış deposu')} name="from_warehouse_id" rules={[{ required: true }]}>
            <Select options={warehouseOptions} onChange={() => form.setFieldValue('lines', [{}])} />
          </Form.Item>
        </Col>
        <Col xs={24} sm={8}>
          <Form.Item
            label={t('Giriş deposu')}
            name="to_warehouse_id"
            dependencies={['from_warehouse_id']}
            rules={[
              { required: true },
              {
                validator: async (_rule, value: number) => {
                  if (value === form.getFieldValue('from_warehouse_id')) throw new Error(t('Çıkış ve giriş deposu aynı olamaz.'))
                },
              },
            ]}
          >
            <Select options={warehouseOptions} />
          </Form.Item>
        </Col>
        <Col xs={24} sm={8}>
          <Form.Item label={t('Neden')} name="reason" rules={[{ required: true }]}>
            <Select options={MANUAL_REASONS.map((r) => ({ value: r, label: TRANSFER_REASON[r] }))} />
          </Form.Item>
        </Col>
      </Row>
      <Typography.Text type="secondary">{t('Yalnız çıkış deposunda bakiyesi olan ve satışa açık lotlar listelenir.')}</Typography.Text>
      <Form.List name="lines">
        {(fields, { add, remove }) => (
          <>
            {fields.map((field) => (
              <Row gutter={8} key={field.key} align="top" style={{ marginTop: 8 }}>
                <Col xs={24} sm={14}>
                  <Form.Item label={t('Lot')} name={[field.name, 'lot_no']} rules={[{ required: true, message: t('Lot seçin.') }]}>
                    <Select
                      loading={stock.isPending}
                      showSearch={{ optionFilterProp: 'label' }}
                      options={available.map((row) => ({
                        value: row.lot_no,
                        label: `${row.lot_no} · ${row.product_name} · ${formatQty(row.qty, row.base_unit)} · SKT ${formatDate(row.expiry_date)}`,
                      }))}
                    />
                  </Form.Item>
                </Col>
                <Col xs={18} sm={7}>
                  <Form.Item
                    label={t('Miktar')}
                    name={[field.name, 'qty']}
                    dependencies={[['lines', field.name, 'lot_no']]}
                    rules={[
                      decimalRule(t('Miktar'), { maxFraction: 3 }),
                      {
                        validator: async (_rule, value: string | undefined) => {
                          const row = byLot.get(form.getFieldValue(['lines', field.name, 'lot_no']))
                          const qty = parseUserDecimal(value ?? '', 3)
                          if (row && qty && compare(qty, row.qty) > 0) {
                            throw new Error(`Depoda ${formatQty(row.qty, row.base_unit)} var.`)
                          }
                        },
                      },
                    ]}
                  >
                    <Input inputMode="decimal" autoComplete="off" suffix={<UnitSuffix row={byLot.get(lines?.[field.name]?.lot_no ?? '')} />} />
                  </Form.Item>
                </Col>
                <Col xs={6} sm={3}>
                  <Form.Item label=" ">
                    <Button disabled={fields.length === 1} onClick={() => remove(field.name)}>
                      {t('Sil')}
                    </Button>
                  </Form.Item>
                </Col>
              </Row>
            ))}
            <Button size="small" onClick={() => add({})}>
              {t('Lot ekle')}
            </Button>
          </>
        )}
      </Form.List>
    </>
  )
}

// Sonek her zaman var: antd'de sonek sonradan eklenirse giriş kutusu yeniden kurulur ve odak kaybolur.
function UnitSuffix({ row }: { row?: StockRow }) {
  return <span>{row ? unitLabel(row.base_unit) : ''}</span>
}
