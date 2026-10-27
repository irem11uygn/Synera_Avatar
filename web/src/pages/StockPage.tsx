// Stok durumu (FR-104): ürün / lot / depo kırılımında. Bakiyeler defterdeki hareketlerden türetilir.

import { Segmented, Select, Space, Table, type TableColumnsType } from 'antd'
import { useState } from 'react'
import { useProducts, useStock, useWarehouses } from '../api/queries'
import type { BaseUnit, StockRow } from '../api/types'
import { Link } from '../components/Link'
import { Page } from '../components/Page'
import { QueryError } from '../components/QueryError'
import { LotStatusTag } from '../components/StatusTags'
import { sum } from '../lib/decimal'
import { formatDate, formatQty, formatUnitCost } from '../lib/format'
import { t } from '../lib/i18n'

type View = 'lot' | 'product'

type ProductTotal = {
  key: string
  warehouse_name: string
  product_name: string
  base_unit: BaseUnit
  qty: string
  lots: number
}

const LOT_COLUMNS: TableColumnsType<StockRow> = [
  { title: t('Depo'), dataIndex: 'warehouse_name' },
  { title: t('Ürün'), dataIndex: 'product_name' },
  { title: t('Lot'), dataIndex: 'lot_no', render: (lotNo: string) => <Link to={`/lotlar/${lotNo}`}>{lotNo}</Link> },
  { title: t('Miktar'), dataIndex: 'qty', align: 'right', render: (qty: string, row) => formatQty(qty, row.base_unit) },
  { title: 'SKT', dataIndex: 'expiry_date', render: formatDate },
  { title: t('Durum'), dataIndex: 'lot_status', render: (status: StockRow['lot_status']) => <LotStatusTag status={status} /> },
  { title: t('Birim maliyet'), dataIndex: 'unit_cost', align: 'right', render: formatUnitCost },
]

const PRODUCT_COLUMNS: TableColumnsType<ProductTotal> = [
  { title: t('Depo'), dataIndex: 'warehouse_name' },
  { title: t('Ürün'), dataIndex: 'product_name' },
  { title: t('Lot sayısı'), dataIndex: 'lots', align: 'right' },
  { title: t('Toplam miktar'), dataIndex: 'qty', align: 'right', render: (qty: string, row) => formatQty(qty, row.base_unit) },
]

function totalsByProduct(rows: StockRow[]): ProductTotal[] {
  const groups = new Map<string, StockRow[]>()
  for (const row of rows) {
    const key = `${row.warehouse_id}-${row.product_id}`
    groups.set(key, [...(groups.get(key) ?? []), row])
  }
  return [...groups.entries()].map(([key, group]) => ({
    key,
    warehouse_name: group[0].warehouse_name,
    product_name: group[0].product_name,
    base_unit: group[0].base_unit,
    qty: sum(group.map((r) => r.qty), 3),
    lots: group.length,
  }))
}

export default function StockPage() {
  const warehouses = useWarehouses()
  const products = useProducts()
  const [warehouseId, setWarehouseId] = useState<number | 'all'>('all')
  const [productId, setProductId] = useState<number | undefined>()
  const [view, setView] = useState<View>('lot')
  const stock = useStock({ warehouse_id: warehouseId === 'all' ? undefined : warehouseId, product_id: productId })

  return (
    <Page
      title={t('Stok durumu')}
      description={t('Hangi depoda, hangi lottan ne kadar mal var. Kırmızı: süresi geçmiş ya da satışa kapalı.')}
    >
      {stock.isError && <QueryError error={stock.error} onRetry={() => stock.refetch()} />}
      <Space wrap style={{ marginBottom: 16 }}>
        <Segmented<number | 'all'>
          value={warehouseId}
          onChange={setWarehouseId}
          options={[{ value: 'all', label: t('Bütün depolar') }, ...(warehouses.data ?? []).map((w) => ({ value: w.id, label: w.name }))]}
        />
        <Select
          allowClear
          placeholder={t('Ürün süz')}
          aria-label={t('Ürün süz')}
          style={{ minWidth: 220 }}
          value={productId}
          onChange={setProductId}
          showSearch={{ optionFilterProp: 'label' }}
          options={products.data?.map((p) => ({ value: p.id, label: p.name }))}
        />
        <Segmented<View>
          value={view}
          onChange={setView}
          options={[
            { value: 'lot', label: t('Lot bazında') },
            { value: 'product', label: t('Ürün bazında') },
          ]}
        />
      </Space>
      {view === 'lot' ? (
        <Table<StockRow>
          rowKey={(row) => `${row.warehouse_id}-${row.lot_no}`}
          size="middle"
          loading={stock.isPending}
          columns={LOT_COLUMNS}
          dataSource={stock.data}
          pagination={false}
          scroll={{ x: 'max-content' }}
        />
      ) : (
        <Table<ProductTotal>
          rowKey="key"
          size="middle"
          loading={stock.isPending}
          columns={PRODUCT_COLUMNS}
          dataSource={stock.data ? totalsByProduct(stock.data) : undefined}
          pagination={false}
          scroll={{ x: 'max-content' }}
        />
      )}
    </Page>
  )
}
