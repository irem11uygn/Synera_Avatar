// Dış üretim emirleri (FR-105): taslak → sevk edildi → tamamlandı.

import { useQuery } from '@tanstack/react-query'
import { Button, Table } from 'antd'
import { api } from '../api/client'
import type { Order } from '../api/types'
import { ORDER_COLUMNS } from '../components/orderColumns'
import { Page } from '../components/Page'
import { QueryError } from '../components/QueryError'
import { navigate } from '../lib/router'

export default function ProductionListPage() {
  const orders = useQuery({ queryKey: ['orders'], queryFn: () => api<Order[]>('/production-orders') })

  return (
    <Page
      title="Dış üretim emirleri"
      extra={
        <Button type="primary" onClick={() => navigate('/uretim/yeni')}>
          Yeni dış üretim emri
        </Button>
      }
    >
      {orders.isError && <QueryError error={orders.error} onRetry={() => orders.refetch()} />}
      <Table<Order>
        rowKey="id"
        size="middle"
        loading={orders.isPending}
        columns={ORDER_COLUMNS}
        dataSource={orders.data}
        pagination={{ pageSize: 50, hideOnSinglePage: true }}
        scroll={{ x: 'max-content' }}
        locale={{ emptyText: 'Henüz dış üretim emri yok.' }}
      />
    </Page>
  )
}
