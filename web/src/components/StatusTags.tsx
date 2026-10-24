import { Tag } from 'antd'
import type { LotStatus, OrderStatus } from '../api/types'
import { LOT_STATUS, ORDER_STATUS } from '../lib/labels'

// Durum yalnız renkle değil yazıyla da belirtilir (erişilebilirlik).

export function LotStatusTag({ status }: { status: LotStatus }) {
  return <Tag color={status === 'BLOKE' ? 'red' : 'green'}>{LOT_STATUS[status]}</Tag>
}

const ORDER_COLOR: Record<OrderStatus, string> = {
  TASLAK: 'default',
  SEVK_EDILDI: 'blue',
  TAMAMLANDI: 'green',
  IPTAL: 'default',
}

export function OrderStatusTag({ status }: { status: OrderStatus }) {
  return <Tag color={ORDER_COLOR[status]}>{ORDER_STATUS[status]}</Tag>
}
