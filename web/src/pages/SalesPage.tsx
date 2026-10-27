// Satışlar (FR-401, FR-605): Android'den gelen satışlar ve satır bazında lot, maliyet, brüt kâr;
// müşteri iadesi (FR-303). Bir satış satırı = bir lot = bir stok hareketi.

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Card, Col, Form, Input, Row, Select, Table, Tag, Typography, Button, type TableColumnsType } from 'antd'
import { useState } from 'react'
import { api } from '../api/client'
import { refreshBusinessData, useWarehouses } from '../api/queries'
import type { Return, Sale, SaleLine } from '../api/types'
import { StatTile } from '../components/Depth'
import { FormModal } from '../components/FormModal'
import { Link } from '../components/Link'
import { Page } from '../components/Page'
import { QueryError } from '../components/QueryError'
import { sum } from '../lib/decimal'
import { formatDateTime, formatMoney, formatQty, unitLabel } from '../lib/format'
import { SALE_CHANNEL, WAREHOUSE_KIND } from '../lib/labels'
import { decimalRule, toApiDecimal } from '../lib/rules'

type ReturnTarget = { sale: Sale; line: SaleLine }
type ReturnValues = { qty: string; warehouse_id?: number; reason?: string }

function ReturnModal({ target, onClose }: { target: ReturnTarget | null; onClose: () => void }) {
  const queryClient = useQueryClient()
  const warehouses = useWarehouses()
  const mutation = useMutation({
    mutationFn: (values: ReturnValues) =>
      api<Return>('/returns', {
        method: 'POST',
        body: { ...values, sale_line_id: target!.line.id, qty: toApiDecimal(values.qty, 3) },
      }),
    onSuccess: () => refreshBusinessData(queryClient),
  })
  if (!target) return null
  const { sale, line } = target
  return (
    <FormModal<ReturnValues>
      title={`${sale.sale_no} · ${line.lot_no} — müşteri iadesi`}
      open
      onClose={onClose}
      onSubmit={(values) => mutation.mutateAsync(values)}
      okText="İadeyi kaydet"
    >
      <Typography.Paragraph>
        {sale.customer_name} · satılan {formatQty(line.qty, line.base_unit)}. Mal aynı lotla depoya döner.
      </Typography.Paragraph>
      <Form.Item
        name="qty"
        label={`Miktar (${unitLabel(line.base_unit)})`}
        rules={[decimalRule('Miktar', { maxFraction: 3, integer: line.base_unit === 'ADET' })]}
      >
        <Input inputMode="decimal" autoComplete="off" />
      </Form.Item>
      <Form.Item name="warehouse_id" label="Giriş deposu" extra="Boş bırakılırsa ana depo">
        <Select
          allowClear
          options={(warehouses.data ?? []).map((w) => ({ value: w.id, label: `${w.name} (${WAREHOUSE_KIND[w.kind]})` }))}
        />
      </Form.Item>
      <Form.Item name="reason" label="Neden">
        <Input maxLength={255} />
      </Form.Item>
    </FormModal>
  )
}

export default function SalesPage() {
  const sales = useQuery({ queryKey: ['sales'], queryFn: () => api<Sale[]>('/sales') })
  const returns = useQuery({ queryKey: ['returns'], queryFn: () => api<Return[]>('/returns') })
  const [target, setTarget] = useState<ReturnTarget | null>(null)

  const data = sales.data ?? []
  const amount = sum(data.map((s) => s.total_amount), 2)
  const cost = sum(data.map((s) => s.total_cost), 2)

  const columns: TableColumnsType<Sale> = [
    { title: 'Belge', dataIndex: 'sale_no' },
    { title: 'Zaman', dataIndex: 'sold_at', render: formatDateTime },
    { title: 'Kanal', dataIndex: 'channel', render: (c: Sale['channel']) => <Tag>{SALE_CHANNEL[c]}</Tag> },
    { title: 'Müşteri', dataIndex: 'customer_name' },
    { title: 'Tutar', dataIndex: 'total_amount', align: 'right', render: formatMoney },
    { title: 'Maliyet', dataIndex: 'total_cost', align: 'right', render: formatMoney },
    {
      title: 'Durum',
      dataIndex: 'recall_violation',
      render: (v: boolean) => (v ? <Tag color="orange">Geri çağrılmış lot satıldı</Tag> : <Tag color="green">Normal</Tag>),
    },
  ]

  return (
    <Page title="Satışlar">
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col xs={12} lg={6}>
          <StatTile label="Satış belgesi" value={data.length} />
        </Col>
        <Col xs={12} lg={6}>
          <StatTile label="Ciro" value={formatMoney(amount)} color="var(--success)" />
        </Col>
        <Col xs={12} lg={6}>
          <StatTile label="Satılan malın maliyeti" value={formatMoney(cost)} color="var(--warning)" />
        </Col>
        <Col xs={12} lg={6}>
          <StatTile label="İade kaydı" value={returns.data?.length ?? '—'} color="var(--danger)" />
        </Col>
      </Row>
      <Card size="small" title="Satışlar (satırları görmek için satırı açın)" style={{ marginBottom: 16 }}>
        {sales.isError && <QueryError error={sales.error} onRetry={() => sales.refetch()} />}
        <Table<Sale>
          rowKey="id"
          size="small"
          loading={sales.isPending}
          dataSource={data}
          columns={columns}
          pagination={{ pageSize: 20, hideOnSinglePage: true }}
          scroll={{ x: 'max-content' }}
          locale={{ emptyText: 'Henüz satış yok. Satışlar Android uygulamasından gelir.' }}
          expandable={{
            expandedRowRender: (sale) => (
              <Table<SaleLine>
                rowKey="id"
                size="small"
                pagination={false}
                dataSource={sale.lines}
                columns={[
                  { title: 'Lot', dataIndex: 'lot_no', render: (no: string) => <Link to={`/lotlar/${no}`}>{no}</Link> },
                  { title: 'Ürün', dataIndex: 'product_name' },
                  { title: 'Miktar', dataIndex: 'qty', align: 'right', render: (v: string, l) => formatQty(v, l.base_unit) },
                  { title: 'Birim fiyat', dataIndex: 'unit_price', align: 'right', render: formatMoney },
                  { title: 'Tutar', dataIndex: 'amount', align: 'right', render: formatMoney },
                  { title: 'Maliyet', dataIndex: 'cost_amount', align: 'right', render: formatMoney },
                  {
                    title: 'İşlem',
                    key: 'return',
                    render: (_, line) => (
                      <Button size="small" onClick={() => setTarget({ sale, line })}>
                        İade al
                      </Button>
                    ),
                  },
                ]}
              />
            ),
          }}
        />
      </Card>
      <Card size="small" title="Müşteri iadeleri">
        <Table<Return>
          rowKey="id"
          size="small"
          loading={returns.isPending}
          dataSource={returns.data}
          pagination={false}
          scroll={{ x: 'max-content' }}
          locale={{ emptyText: 'İade yok.' }}
          columns={[
            { title: 'İade no', dataIndex: 'return_no' },
            { title: 'Zaman', dataIndex: 'created_at', render: formatDateTime },
            { title: 'Satış', dataIndex: 'sale_no' },
            { title: 'Müşteri', dataIndex: 'customer_name' },
            { title: 'Lot', dataIndex: 'lot_no', render: (no: string) => <Link to={`/lotlar/${no}`}>{no}</Link> },
            { title: 'Miktar', dataIndex: 'qty', align: 'right', render: (v: string) => formatQty(v) },
            { title: 'Depo', dataIndex: 'warehouse_code' },
            { title: 'Neden', dataIndex: 'reason', render: (v: string | null) => v ?? '—' },
          ]}
        />
      </Card>
      <ReturnModal target={target} onClose={() => setTarget(null)} />
    </Page>
  )
}
