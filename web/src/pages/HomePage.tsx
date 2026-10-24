import { useQuery } from '@tanstack/react-query'
import { Button, Card, Col, Row, Space, Table } from 'antd'
import { api } from '../api/client'
import type { Order } from '../api/types'
import { ORDER_COLUMNS } from '../components/orderColumns'
import { Page } from '../components/Page'
import { QueryError } from '../components/QueryError'
import { SystemStatus } from '../components/SystemStatus'
import { navigate } from '../lib/router'

export default function HomePage() {
  const orders = useQuery({ queryKey: ['orders'], queryFn: () => api<Order[]>('/production-orders') })

  return (
    <Page title="Ana sayfa">
      <Row gutter={16}>
        <Col xs={24} lg={14}>
          <Card size="small" title="Hızlı işlemler" style={{ marginBottom: 16 }}>
            <Space wrap>
              <Button type="primary" onClick={() => navigate('/uretim/yeni')}>
                Yeni dış üretim emri
              </Button>
              <Button onClick={() => navigate('/alislar/yeni')}>Hammadde alışı</Button>
              <Button onClick={() => navigate('/transferler')}>Araca yükleme</Button>
              <Button onClick={() => navigate('/stok')}>Stok durumu</Button>
            </Space>
          </Card>
        </Col>
        <Col xs={24} lg={10}>
          <Card size="small" title="Sistem durumu" style={{ marginBottom: 16 }}>
            <SystemStatus />
          </Card>
        </Col>
      </Row>
      <Card size="small" title="Son dış üretim emirleri">
        {orders.isError && <QueryError error={orders.error} onRetry={() => orders.refetch()} />}
        <Table<Order>
          rowKey="id"
          size="small"
          loading={orders.isPending}
          columns={ORDER_COLUMNS}
          dataSource={orders.data?.slice(0, 5)}
          pagination={false}
          scroll={{ x: 'max-content' }}
          locale={{ emptyText: 'Henüz dış üretim emri yok.' }}
        />
      </Card>
    </Page>
  )
}
