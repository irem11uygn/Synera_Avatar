// Gün sonu: günün satışları ve iadeleri, ödeme türüne ve satıcıya göre toplamlar. Kasa sayımı ve
// araç dönüşünde kullanılır; yazdırılabilir.

import { PrinterOutlined } from '@ant-design/icons'
import { Button, Card, Col, Input, Row, Select, Table, Tag } from 'antd'
import { useState } from 'react'
import { useDayEnd, useWarehouses } from '../api/queries'
import type { DaySale, PaymentMethod } from '../api/types'
import { useSession } from '../auth/context'
import { Page } from '../components/Page'
import { QueryError } from '../components/QueryError'
import { Stat } from '../components/Stat'
import { sum } from '../lib/decimal'
import { formatDate, formatDateTime, formatMoney, formatQty, todayIso } from '../lib/format'
import { PAYMENT_METHOD, paymentLabel, SALE_CHANNEL } from '../lib/labels'
import { navigate } from '../lib/router'
import { t } from '../lib/i18n'

export default function DayEndPage() {
  const { user } = useSession()
  const [day, setDay] = useState(todayIso())
  const [warehouseId, setWarehouseId] = useState<number | undefined>()
  const warehouses = useWarehouses()
  const report = useDayEnd(day, warehouseId)
  const data = report.data
  const places = (warehouses.data ?? []).filter((w) => w.kind !== 'DIS_URETICI')
  const cash = data?.by_payment.find((row) => row.key === 'NAKIT')?.amount ?? '0'

  return (
    <Page
      title={t('Gün sonu')}
      description={t('Günün satışları, iadeleri ve ödeme türüne göre toplamlar. Kasayı sayarken ve araç dönünce kullanın.')}
      extra={
        <Button
          icon={<PrinterOutlined />}
          onClick={() => navigate(`/yazdir/gun-sonu/${day}${warehouseId ? `?depo=${warehouseId}` : ''}`)}
        >
          {t('Yazdır')}
        </Button>
      }
    >
      <Card style={{ marginBottom: 16 }}>
        <Row gutter={[12, 12]}>
          <Col xs={24} sm={12} md={8}>
            <label className="muted" htmlFor="gun">
              {t('Gün')}
            </label>
            <Input id="gun" type="date" value={day} max={todayIso()} onChange={(e) => e.target.value && setDay(e.target.value)} />
          </Col>
          <Col xs={24} sm={12} md={8}>
            <label className="muted" htmlFor="yer">
              {t('Satış yeri')}
            </label>
            <Select
              id="yer"
              style={{ width: '100%' }}
              value={warehouseId ?? 0}
              onChange={(value: number) => setWarehouseId(value || undefined)}
              options={[
                { value: 0, label: t('Hepsi (mağaza + araçlar)') },
                ...places.map((w) => ({ value: w.id, label: w.kind === 'ANA' ? t('Mağaza (ana depo)') : w.name })),
              ]}
            />
          </Col>
        </Row>
      </Card>

      {report.isError && <QueryError error={report.error} onRetry={() => report.refetch()} />}

      {data && (
        <>
          <Row gutter={[12, 12]} style={{ marginBottom: 16 }}>
            <Col xs={12} lg={6}>
              <Stat label={t('Satış')} value={formatMoney(data.sales_amount)} hint={`${data.sale_count} belge`} tone="success" />
            </Col>
            <Col xs={12} lg={6}>
              <Stat label={t('İade')} value={formatMoney(data.refund_amount)} hint={`${data.returns.length} iade`} tone="warning" />
            </Col>
            <Col xs={12} lg={6}>
              <Stat label={t('Net')} value={formatMoney(data.net_amount)} hint={t('Satış − iade')} tone="brand" />
            </Col>
            <Col xs={12} lg={6}>
              <Stat label={t('Kasadaki nakit satış')} value={formatMoney(cash)} hint={t('Nakit iade verdiyseniz düşün')} />
            </Col>
          </Row>
          {user.role === 'YONETICI' && (
            <Row gutter={[12, 12]} style={{ marginBottom: 16 }}>
              <Col xs={12} lg={6}>
                <Stat label={t('Satılan malın maliyeti')} value={formatMoney(data.cost_amount)} />
              </Col>
              <Col xs={12} lg={6}>
                <Stat
                  label={t('Brüt kâr')}
                  value={formatMoney(sum([data.sales_amount, `-${data.cost_amount}`], 2))}
                  tone="success"
                />
              </Col>
            </Row>
          )}

          <Row gutter={[16, 16]}>
            <Col xs={24} lg={12}>
              <Card title={t('Ödeme türüne göre')} size="small">
                <Table
                  rowKey="key"
                  size="small"
                  pagination={false}
                  dataSource={data.by_payment}
                  locale={{ emptyText: t('Bu gün satış yok.') }}
                  columns={[
                    { title: t('Ödeme'), dataIndex: 'key', render: paymentLabel },
                    { title: t('Belge'), dataIndex: 'sale_count', align: 'right' },
                    { title: t('Tutar'), dataIndex: 'amount', align: 'right', render: formatMoney },
                  ]}
                />
              </Card>
            </Col>
            <Col xs={24} lg={12}>
              <Card title={t('Satıcıya göre')} size="small">
                <Table
                  rowKey="key"
                  size="small"
                  pagination={false}
                  dataSource={data.by_seller}
                  locale={{ emptyText: t('Bu gün satış yok.') }}
                  columns={[
                    { title: t('Satıcı'), dataIndex: 'key' },
                    { title: t('Belge'), dataIndex: 'sale_count', align: 'right' },
                    { title: t('Tutar'), dataIndex: 'amount', align: 'right', render: formatMoney },
                  ]}
                />
              </Card>
            </Col>
          </Row>

          <div className="section-title">{t('Satışlar ({n})', { n: data.sales.length })}</div>
          <Table<DaySale>
            rowKey="id"
            dataSource={data.sales}
            pagination={{ pageSize: 20, hideOnSinglePage: true }}
            scroll={{ x: 'max-content' }}
            locale={{ emptyText: t('{day} günü satış yok.', { day: formatDate(day) }) }}
            columns={[
              { title: t('Saat'), dataIndex: 'sold_at', render: (v: string) => formatDateTime(v).slice(-5) },
              { title: t('Belge'), dataIndex: 'sale_no' },
              { title: t('Müşteri'), dataIndex: 'customer_name' },
              { title: t('Satıcı'), dataIndex: 'seller_name', responsive: ['md'] },
              { title: t('Yer'), dataIndex: 'channel', render: (c: DaySale['channel']) => SALE_CHANNEL[c], responsive: ['lg'] },
              {
                title: t('Ödeme'),
                dataIndex: 'payment_method',
                render: (p: PaymentMethod | null) => (p ? PAYMENT_METHOD[p] : <Tag>{t('Belirtilmedi')}</Tag>),
              },
              { title: t('Tutar'), dataIndex: 'amount', align: 'right', render: formatMoney },
              {
                title: '',
                render: (_, sale) => (
                  <Button size="small" icon={<PrinterOutlined />} onClick={() => navigate(`/yazdir/satis/${sale.id}`)}>
                    {t('Fiş')}
                  </Button>
                ),
              },
            ]}
          />

          {data.returns.length > 0 && (
            <>
              <div className="section-title">{t('İadeler ({n})', { n: data.returns.length })}</div>
              <Table
                rowKey="return_no"
                dataSource={data.returns}
                pagination={false}
                scroll={{ x: 'max-content' }}
                columns={[
                  { title: t('İade'), dataIndex: 'return_no' },
                  { title: t('Satış'), dataIndex: 'sale_no' },
                  { title: t('Müşteri'), dataIndex: 'customer_name' },
                  { title: t('Lot'), dataIndex: 'lot_no' },
                  { title: t('Miktar'), dataIndex: 'qty', align: 'right', render: (v: string) => formatQty(v) },
                  { title: t('Geri ödenecek'), dataIndex: 'refund_amount', align: 'right', render: formatMoney },
                ]}
              />
            </>
          )}

          {data.stock_left.length > 0 && (
            <>
              <div className="section-title">{t('Araçta kalan mal')}</div>
              <Table
                rowKey="lot_no"
                dataSource={data.stock_left}
                pagination={false}
                scroll={{ x: 'max-content' }}
                columns={[
                  { title: t('Ürün'), dataIndex: 'product_name' },
                  { title: t('Lot'), dataIndex: 'lot_no' },
                  { title: t('Son kullanma'), dataIndex: 'expiry_date', render: formatDate },
                  {
                    title: t('Miktar'),
                    align: 'right',
                    render: (_, row) => formatQty(row.qty, row.base_unit),
                  },
                ]}
              />
            </>
          )}
        </>
      )}
    </Page>
  )
}
