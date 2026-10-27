// Dış üretim emri tablosunun sütunları (emir listesi ve ana sayfa).

import type { TableColumnsType } from 'antd'
import type { Order, OrderStatus } from '../api/types'
import { formatDateTime, formatMoney, formatQty, formatUnitCost } from '../lib/format'
import { Link } from './Link'
import { OrderStatusTag } from './StatusTags'
import { t } from '../lib/i18n'

export const ORDER_COLUMNS: TableColumnsType<Order> = [
  {
    title: t('Emir no'),
    dataIndex: 'order_no',
    render: (orderNo: string, row) => <Link to={`/uretim/${row.id}`}>{orderNo}</Link>,
  },
  { title: t('Durum'), dataIndex: 'status', render: (status: OrderStatus) => <OrderStatusTag status={status} /> },
  { title: t('Fasoncu'), dataIndex: 'subcontractor_name' },
  { title: t('Mamul'), dataIndex: 'output_product_name' },
  { title: t('Planlanan'), dataIndex: 'planned_qty', align: 'right', render: (v: string, row) => formatQty(v, row.base_unit) },
  {
    title: t('Teslim alınan'),
    dataIndex: 'received_qty',
    align: 'right',
    render: (v: string | null, row) => formatQty(v, row.base_unit),
  },
  {
    title: t('Mamul lotu'),
    dataIndex: 'output_lot_no',
    render: (lotNo: string | null) => (lotNo ? <Link to={`/lotlar/${lotNo}`}>{lotNo}</Link> : '—'),
  },
  { title: t('Toplam maliyet'), key: 'total', align: 'right', render: (_, row) => formatMoney(row.cost?.total) },
  { title: t('Birim maliyet'), key: 'ekp', align: 'right', render: (_, row) => formatUnitCost(row.cost?.ekp_display) },
  { title: t('Emir tarihi'), dataIndex: 'ordered_at', render: formatDateTime },
]
