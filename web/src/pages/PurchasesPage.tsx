// Hammadde alışları (FR-102, FR-207): her satır yeni bir lot açar. Fatura tutarı miktar × fiyattan
// farklıysa açıklama zorunludur; ek maliyetler (kesim, nakliye…) lot değerine eklenir.

import { useQuery } from '@tanstack/react-query'
import { Button, Table, Tag, Typography, type TableColumnsType } from 'antd'
import { api } from '../api/client'
import type { Purchase } from '../api/types'
import { Link } from '../components/Link'
import { Page } from '../components/Page'
import { QueryError } from '../components/QueryError'
import { formatDate, formatMoney, formatQty, formatUnitCost } from '../lib/format'
import { PURCHASE_COST_KIND } from '../lib/labels'
import { navigate } from '../lib/router'
import { t } from '../lib/i18n'
import { sortable } from '../lib/sort'

type Line = Purchase['lines'][number]

const LINE_COLUMNS: TableColumnsType<Line> = [
  { title: t('Lot'), dataIndex: 'lot_no', render: (lotNo: string) => <Link to={`/lotlar/${lotNo}`}>{lotNo}</Link> },
  { title: t('Ürün'), dataIndex: 'product_name' },
  { title: t('Miktar'), dataIndex: 'qty', align: 'right', render: (v: string) => formatQty(v) },
  { title: t('Birim fiyat'), dataIndex: 'unit_price', align: 'right', render: formatUnitCost },
  { title: t('Miktar × fiyat'), dataIndex: 'computed_amount', align: 'right', render: formatMoney },
  {
    title: t('Fatura tutarı'),
    dataIndex: 'invoice_amount',
    align: 'right',
    render: (value: string, row) =>
      value === row.computed_amount ? (
        formatMoney(value)
      ) : (
        <span>
          {formatMoney(value)} <Tag color="orange">{t('fark')}</Tag>
        </span>
      ),
  },
  {
    title: t('Ek maliyetler'),
    dataIndex: 'extra_costs',
    render: (costs: Line['extra_costs']) =>
      costs.length === 0
        ? '—'
        : costs.map((c) => `${PURCHASE_COST_KIND[c.kind]} ${formatMoney(c.amount)}`).join(', '),
  },
  { title: t('Lot değeri'), dataIndex: 'lot_value', align: 'right', render: formatMoney },
  { title: 'SKT', dataIndex: 'expiry_date', render: formatDate },
  { title: t('Açıklama'), dataIndex: 'discrepancy_note', render: (v: string | null) => v ?? '—' },
]

const COLUMNS: TableColumnsType<Purchase> = [
  { title: t('Belge no'), dataIndex: 'doc_no' },
  { title: t('Tarih'), dataIndex: 'doc_date', render: formatDate },
  { title: t('Tedarikçi'), dataIndex: 'supplier_name' },
  { title: t('Lot sayısı'), key: 'lines', align: 'right', render: (_, row) => row.lines.length },
  { title: t('Toplam değer'), dataIndex: 'total_value', align: 'right', render: formatMoney },
  { title: t('Not'), dataIndex: 'note', render: (v: string | null) => v ?? '—' },
]

export default function PurchasesPage() {
  const purchases = useQuery({ queryKey: ['purchases'], queryFn: () => api<Purchase[]>('/purchases') })

  return (
    <Page
      title={t('Mal kabul')}
      description={t('Tedarikçiden gelen malın girişi. Her teslimat yeni bir lot numarası alır; nakliye ve kesim gibi ek masraflar maliyete eklenir.')}
      extra={
        <Button type="primary" onClick={() => navigate('/alislar/yeni')}>
          {t('Yeni alış')}
        </Button>
      }
    >
      {purchases.isError && <QueryError error={purchases.error} onRetry={() => purchases.refetch()} />}
      <Table<Purchase>
        rowKey="id"
        size="middle"
        loading={purchases.isPending}
        columns={sortable(COLUMNS)}
        dataSource={purchases.data}
        pagination={false}
        scroll={{ x: 'max-content' }}
        expandable={{
          expandedRowRender: (row) => (
            <Table<Line>
              rowKey="lot_no"
              size="small"
              columns={LINE_COLUMNS}
              dataSource={row.lines}
              pagination={false}
              scroll={{ x: 'max-content' }}
            />
          ),
        }}
      />
      <Typography.Paragraph type="secondary" style={{ marginTop: 12 }}>
        {t('Satırı açınca alışın lotları, fatura farkları ve ek maliyetler görünür.')}
      </Typography.Paragraph>
    </Page>
  )
}
