// Dış üretim emirleri (FR-105): taslak → sevk edildi → tamamlandı.

import { useQuery } from '@tanstack/react-query'
import { Button, Table } from 'antd'
import { api } from '../api/client'
import type { Order } from '../api/types'
import { ORDER_COLUMNS } from '../components/orderColumns'
import { Page } from '../components/Page'
import { QueryError } from '../components/QueryError'
import { navigate } from '../lib/router'
import { t } from '../lib/i18n'

export default function ProductionListPage() {
  const orders = useQuery({ queryKey: ['orders'], queryFn: () => api<Order[]>('/production-orders') })

  return (
    <Page
      title={t('Fason üretim')}
      description={t('Hammaddeyi fasoncuya gönderip ürettirdiğiniz işler. Adımlar: emir aç → hammaddeyi sevk et → ürünü teslim al (birim maliyet hesaplanır).')}
      extra={
        <Button type="primary" onClick={() => navigate('/uretim/yeni')}>
          {t('Yeni fason üretim emri')}
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
        locale={{ emptyText: t('Henüz fason üretim emri yok.') }}
      />
    </Page>
  )
}
