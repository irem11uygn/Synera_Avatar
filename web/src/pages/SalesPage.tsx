// Satışlar ve iadeler: mağaza ve araç satışları, satır bazında lot; müşteri iadesi aynı lotla depoya
// döner. Bir satış satırı = bir lot = bir stok hareketi.

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { PrinterOutlined, RollbackOutlined, ShoppingCartOutlined } from '@ant-design/icons'
import { Button, Col, Form, Input, Row, Select, Space, Table, Tag, Typography, type TableColumnsType } from 'antd'
import { useState } from 'react'
import { api } from '../api/client'
import { refreshBusinessData, useWarehouses } from '../api/queries'
import type { PaymentMethod, Return, Sale, SaleLine } from '../api/types'
import { useSession } from '../auth/context'
import { Stat } from '../components/Stat'
import { FormModal } from '../components/FormModal'
import { Link } from '../components/Link'
import { Page } from '../components/Page'
import { QueryError } from '../components/QueryError'
import { sum } from '../lib/decimal'
import { formatDate, formatDateTime, formatMoney, formatQty, todayIso, unitLabel } from '../lib/format'
import { PAYMENT_METHOD, SALE_CHANNEL, WAREHOUSE_KIND } from '../lib/labels'
import { can } from '../lib/roles'
import { navigate } from '../lib/router'
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
  const { user } = useSession()
  const [day, setDay] = useState<string>(todayIso())
  const sales = useQuery({
    queryKey: ['sales', day || 'all'],
    queryFn: () => api<Sale[]>('/sales', { query: { day: day || undefined } }),
  })
  const returns = useQuery({ queryKey: ['returns'], queryFn: () => api<Return[]>('/returns') })
  const [target, setTarget] = useState<ReturnTarget | null>(null)
  const manager = user.role === 'YONETICI'
  const canReturn = can(user.role, 'returns')

  const data = sales.data ?? []
  const amount = sum(data.map((s) => s.total_amount), 2)
  const cost = sum(data.map((s) => s.total_cost), 2)

  const columns: TableColumnsType<Sale> = [
    { title: 'Belge', dataIndex: 'sale_no' },
    { title: 'Zaman', dataIndex: 'sold_at', render: formatDateTime },
    { title: 'Müşteri', dataIndex: 'customer_name' },
    { title: 'Yer', dataIndex: 'channel', render: (c: Sale['channel']) => SALE_CHANNEL[c], responsive: ['md'] },
    {
      title: 'Ödeme',
      dataIndex: 'payment_method',
      render: (p: PaymentMethod | null) => (p ? PAYMENT_METHOD[p] : '—'),
      responsive: ['lg'],
    },
    { title: 'Tutar', dataIndex: 'total_amount', align: 'right', render: formatMoney },
    ...(manager
      ? [{ title: 'Maliyet', dataIndex: 'total_cost', align: 'right' as const, render: formatMoney, responsive: ['xl' as const] }]
      : []),
    {
      title: '',
      key: 'actions',
      render: (_, sale) => (
        <Space>
          {sale.recall_violation && <Tag color="orange">Geri çağrılmış lot satıldı</Tag>}
          <Button size="small" icon={<PrinterOutlined />} onClick={() => navigate(`/yazdir/satis/${sale.id}`)}>
            Fiş
          </Button>
        </Space>
      ),
    },
  ]

  return (
    <Page
      title="Satışlar ve iadeler"
      description={
        canReturn
          ? 'Mağaza ve araç satışları. İade almak için satırın başındaki + işaretine basın, ilgili üründe "İade al"ı seçin.'
          : 'Mağaza ve araç satışları.'
      }
      extra={
        can(user.role, 'store') && (
          <Button type="primary" icon={<ShoppingCartOutlined />} onClick={() => navigate('/magaza-satisi')}>
            Yeni mağaza satışı
          </Button>
        )
      }
    >
      <Space wrap style={{ marginBottom: 16 }}>
        <Input type="date" value={day} max={todayIso()} onChange={(e) => setDay(e.target.value)} aria-label="Gün" style={{ width: 180 }} />
        <Button onClick={() => setDay(todayIso())} disabled={day === todayIso()}>
          Bugün
        </Button>
        <Button onClick={() => setDay('')} disabled={day === ''}>
          Bütün satışlar
        </Button>
      </Space>
      <Row gutter={[12, 12]} style={{ marginBottom: 16 }}>
        <Col xs={12} lg={6}>
          <Stat label="Satış belgesi" value={data.length} hint={day ? formatDate(day) : 'Bütün günler'} />
        </Col>
        <Col xs={12} lg={6}>
          <Stat label="Ciro" value={formatMoney(amount)} tone="success" />
        </Col>
        {manager && (
          <Col xs={12} lg={6}>
            <Stat label="Satılan malın maliyeti" value={formatMoney(cost)} tone="warning" />
          </Col>
        )}
      </Row>
      {sales.isError && <QueryError error={sales.error} onRetry={() => sales.refetch()} />}
      <Table<Sale>
        rowKey="id"
        loading={sales.isPending}
        dataSource={data}
        columns={columns}
        pagination={{ pageSize: 20, hideOnSinglePage: true }}
        scroll={{ x: 'max-content' }}
        locale={{ emptyText: day ? `${formatDate(day)} günü satış yok.` : 'Henüz satış yok.' }}
        expandable={{
          expandedRowRender: (sale) => (
            <Table<SaleLine>
              rowKey="id"
              size="small"
              pagination={false}
              dataSource={sale.lines}
              scroll={{ x: 'max-content' }}
              columns={[
                { title: 'Ürün', dataIndex: 'product_name' },
                { title: 'Lot', dataIndex: 'lot_no', render: (no: string) => <Link to={`/lotlar/${no}`}>{no}</Link> },
                { title: 'Miktar', dataIndex: 'qty', align: 'right', render: (v: string, l) => formatQty(v, l.base_unit) },
                { title: 'Birim fiyat', dataIndex: 'unit_price', align: 'right', render: formatMoney },
                { title: 'Tutar', dataIndex: 'amount', align: 'right', render: formatMoney },
                ...(canReturn
                  ? [
                      {
                        title: '',
                        key: 'return',
                        render: (_: unknown, line: SaleLine) => (
                          <Button size="small" icon={<RollbackOutlined />} onClick={() => setTarget({ sale, line })}>
                            İade al
                          </Button>
                        ),
                      },
                    ]
                  : []),
              ]}
            />
          ),
        }}
      />
      <div className="section-title">Müşteri iadeleri</div>
      <Table<Return>
        rowKey="id"
        loading={returns.isPending}
        dataSource={returns.data}
        pagination={{ pageSize: 10, hideOnSinglePage: true }}
        scroll={{ x: 'max-content' }}
        locale={{ emptyText: 'İade yok.' }}
        columns={[
          { title: 'İade no', dataIndex: 'return_no' },
          { title: 'Zaman', dataIndex: 'created_at', render: formatDateTime },
          { title: 'Müşteri', dataIndex: 'customer_name' },
          { title: 'Lot', dataIndex: 'lot_no', render: (no: string) => <Link to={`/lotlar/${no}`}>{no}</Link> },
          { title: 'Miktar', dataIndex: 'qty', align: 'right', render: (v: string) => formatQty(v) },
          { title: 'Neden', dataIndex: 'reason', render: (v: string | null) => v ?? '—', responsive: ['md'] },
        ]}
      />
      <ReturnModal target={target} onClose={() => setTarget(null)} />
    </Page>
  )
}
