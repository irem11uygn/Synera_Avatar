// Lot listesi: her alış, üretim ve parçalama yeni lot açar. Lot numarasına tıklayınca köken,
// hareket geçmişi ve lot ağı görünür.

import { useQuery } from '@tanstack/react-query'
import { Input, Segmented, Space, Table, type TableColumnsType } from 'antd'
import { useDeferredValue, useState } from 'react'
import { api } from '../api/client'
import type { Lot, LotOrigin, LotStatus } from '../api/types'
import { Link } from '../components/Link'
import { Page } from '../components/Page'
import { QueryError } from '../components/QueryError'
import { LotStatusTag } from '../components/StatusTags'
import { formatDate, formatMoney, formatQty, formatUnitCost } from '../lib/format'
import { LOT_ORIGIN } from '../lib/labels'
import { t } from '../lib/i18n'
import { sortable } from '../lib/sort'

const COLUMNS: TableColumnsType<Lot> = [
  { title: t('Lot no'), dataIndex: 'lot_no', render: (lotNo: string) => <Link to={`/lotlar/${lotNo}`}>{lotNo}</Link> },
  { title: t('Ürün'), dataIndex: 'product_name' },
  { title: t('Köken'), dataIndex: 'origin', render: (origin: LotOrigin) => LOT_ORIGIN[origin] },
  { title: t('Tedarikçi'), dataIndex: 'supplier_name', render: (v: string | null) => v ?? '—' },
  { title: t('Durum'), dataIndex: 'status', render: (status: LotStatus) => <LotStatusTag status={status} /> },
  { title: t('Başlangıç'), dataIndex: 'initial_qty', align: 'right', render: (v: string, row) => formatQty(v, row.base_unit) },
  { title: t('Kalan'), dataIndex: 'remaining_qty', align: 'right', render: (v: string, row) => formatQty(v, row.base_unit) },
  { title: t('Kalan değer'), dataIndex: 'remaining_value', align: 'right', render: formatMoney },
  { title: t('Birim maliyet'), dataIndex: 'unit_cost', align: 'right', render: formatUnitCost },
  { title: t('Üretim'), dataIndex: 'produced_at', render: formatDate },
  { title: 'SKT', dataIndex: 'expiry_date', render: formatDate },
]

export default function LotsPage() {
  const [search, setSearch] = useState('')
  const [status, setStatus] = useState<LotStatus | 'all'>('all')
  const q = useDeferredValue(search.trim())
  const lots = useQuery({
    queryKey: ['lots', { q, status }],
    queryFn: () => api<Lot[]>('/lots', { query: { q, status: status === 'all' ? undefined : status } }),
    placeholderData: (previous) => previous,
  })

  return (
    <Page
      title={t('Lotlar (partiler)')}
      description={t('Her mal girişi bir lot numarası alır. Lot kartında nereden geldiği, nereye gittiği ve bütün hareketleri görünür.')}
    >
      {lots.isError && <QueryError error={lots.error} onRetry={() => lots.refetch()} />}
      <Space wrap style={{ marginBottom: 16 }}>
        <Input.Search
          placeholder={t('Lot no ara (ör. ET-2026)')}
          aria-label={t('Lot no ara')}
          allowClear
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          autoComplete="off"
          spellCheck={false}
          enterKeyHint="search"
          style={{ width: 260 }}
        />
        <Segmented<LotStatus | 'all'>
          value={status}
          onChange={setStatus}
          options={[
            { value: 'all', label: t('Tümü') },
            { value: 'AKTIF', label: t('Satışa açık') },
            { value: 'BLOKE', label: t('Satışa kapalı') },
          ]}
        />
      </Space>
      <Table<Lot>
        rowKey="id"
        size="middle"
        loading={lots.isPending}
        columns={sortable(COLUMNS)}
        dataSource={lots.data}
        pagination={{ pageSize: 50, hideOnSinglePage: true }}
        scroll={{ x: 'max-content' }}
      />
    </Page>
  )
}
