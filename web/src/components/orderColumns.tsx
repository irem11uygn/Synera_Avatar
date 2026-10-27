// Dış üretim emri tablosunun sütunları (emir listesi ve ana sayfa).

import type { TableColumnsType } from 'antd'
import type { Order, OrderStatus } from '../api/types'
import { formatDateTime, formatMoney, formatQty, formatUnitCost } from '../lib/format'
import { Link } from './Link'
import { OrderStatusTag } from './StatusTags'

export const ORDER_COLUMNS: TableColumnsType<Order> = [
  {
    title: 'Emir no',
    dataIndex: 'order_no',
    render: (orderNo: string, row) => <Link to={`/uretim/${row.id}`}>{orderNo}</Link>,
  },
  { title: 'Durum', dataIndex: 'status', render: (status: OrderStatus) => <OrderStatusTag status={status} /> },
  { title: 'Fasoncu', dataIndex: 'subcontractor_name' },
  { title: 'Mamul', dataIndex: 'output_product_name' },
  { title: 'Planlanan', dataIndex: 'planned_qty', align: 'right', render: (v: string, row) => formatQty(v, row.base_unit) },
  {
    title: 'Teslim alınan',
    dataIndex: 'received_qty',
    align: 'right',
    render: (v: string | null, row) => formatQty(v, row.base_unit),
  },
  {
    title: 'Mamul lotu',
    dataIndex: 'output_lot_no',
    render: (lotNo: string | null) => (lotNo ? <Link to={`/lotlar/${lotNo}`}>{lotNo}</Link> : '—'),
  },
  { title: 'Toplam maliyet', key: 'total', align: 'right', render: (_, row) => formatMoney(row.cost?.total) },
  { title: 'Birim maliyet', key: 'ekp', align: 'right', render: (_, row) => formatUnitCost(row.cost?.ekp_display) },
  { title: 'Emir tarihi', dataIndex: 'ordered_at', render: formatDateTime },
]
