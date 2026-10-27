// İzleme ve geri çağırma ekranlarındaki alıcı tablosu (FR-307, FR-308).

import { Space, Tag, Typography, type TableColumnsType } from 'antd'
import type { Recipient } from '../api/types'
import { formatQty } from '../lib/format'
import { ONWARD_STATUS, SALE_CHANNEL } from '../lib/labels'
import { ContactInfo } from './ContactInfo'
import { Link } from './Link'

export const RECIPIENT_COLUMNS: TableColumnsType<Recipient> = [
  {
    title: 'Alıcı',
    dataIndex: 'customer',
    render: (name: string, r) => (
      <>
        <Typography.Text strong>{name}</Typography.Text>
        {r.recall_violation && (
          <Tag color="orange" style={{ marginInlineStart: 8 }}>
            Geri çağırmadan sonra satış
          </Tag>
        )}
      </>
    ),
  },
  { title: 'İletişim', key: 'contact', render: (_, r) => <ContactInfo contact={r.contact} /> },
  { title: 'Lot', dataIndex: 'lot_no', render: (lotNo: string) => <Link to={`/lotlar/${lotNo}`}>{lotNo}</Link> },
  { title: 'Ürün', dataIndex: 'product_name' },
  { title: 'Satılan', dataIndex: 'sold_qty', align: 'right', render: (v: string, r) => formatQty(v, r.base_unit) },
  { title: 'İade', dataIndex: 'returned_qty', align: 'right', render: (v: string, r) => formatQty(v, r.base_unit) },
  {
    title: 'Müşteride',
    dataIndex: 'qty',
    align: 'right',
    render: (v: string, r) => <Typography.Text strong>{formatQty(v, r.base_unit)}</Typography.Text>,
  },
  {
    title: 'Satış belgeleri',
    key: 'sales',
    render: (_, r) => r.sales.map((s) => `${s.sale_no} (${SALE_CHANNEL[s.channel]})`).join(', '),
  },
  {
    title: 'Müşterinin dağıttığı',
    key: 'onward',
    render: (_, r) => (
      <Space orientation="vertical" size={0}>
        <Tag color={r.onward_status === 'KAYITLI' ? 'green' : r.onward_status === 'KISMEN' ? 'gold' : 'default'}>
          {ONWARD_STATUS[r.onward_status]}
        </Tag>
        {r.onward_items.map((item) => (
          <span key={`${item.recipient}-${item.qty}`}>
            {item.recipient}: {formatQty(item.qty, r.base_unit)}
          </span>
        ))}
        {r.onward_status === 'KISMEN' && <span>Bilinmeyen: {formatQty(r.onward_unknown_qty, r.base_unit)}</span>}
      </Space>
    ),
  },
]
