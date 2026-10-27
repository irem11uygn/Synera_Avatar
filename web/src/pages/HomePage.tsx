import { useQuery } from '@tanstack/react-query'
import { Button, Card, Col, Row, Space, Table, Typography } from 'antd'
import { api } from '../api/client'
import type { AlertRow, Order, RecallSummary, Report } from '../api/types'
import { StatTile } from '../components/Depth'
import { ORDER_COLUMNS } from '../components/orderColumns'
import { Page } from '../components/Page'
import { QueryError } from '../components/QueryError'
import { SystemStatus } from '../components/SystemStatus'
import { formatMoney } from '../lib/format'
import { tracePath } from '../lib/paths'
import { navigate } from '../lib/router'

export default function HomePage() {
  const orders = useQuery({ queryKey: ['orders'], queryFn: () => api<Order[]>('/production-orders') })
  const recalls = useQuery({ queryKey: ['recalls'], queryFn: () => api<RecallSummary[]>('/recalls') })
  const alerts = useQuery({
    queryKey: ['alerts', true],
    queryFn: () => api<AlertRow[]>('/alerts', { query: { only_open: true } }),
  })
  const integrity = useQuery({ queryKey: ['report', 'integrity', {}], queryFn: () => api<Report>('/reports/integrity') })

  const openRecalls = recalls.data?.filter((r) => r.status === 'ACIK').length
  const passed = integrity.data?.rows.filter((row) => row.ok === true).length
  const total = integrity.data?.rows.length
  const lastOrder = orders.data?.find((o) => o.status === 'TAMAMLANDI')

  return (
    <Page title="Ana sayfa">
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col xs={12} lg={6}>
          <StatTile
            label="Son EKP (Görev 1)"
            value={lastOrder?.cost ? formatMoney(lastOrder.cost.ekp_display) : '—'}
            hint={lastOrder ? `${lastOrder.order_no} · ${lastOrder.output_product_name}` : 'Tamamlanan emir yok'}
            onClick={lastOrder ? () => navigate(`/uretim/${lastOrder.id}`) : undefined}
          />
        </Col>
        <Col xs={12} lg={6}>
          <StatTile
            label="Açık geri çağırma"
            value={openRecalls ?? '—'}
            hint="Bloke lotlar hiçbir kanaldan satılamaz"
            color="var(--danger)"
            onClick={() => navigate('/geri-cagirma')}
          />
        </Col>
        <Col xs={12} lg={6}>
          <StatTile
            label="Okunmamış uyarı"
            value={alerts.data?.length ?? '—'}
            hint="Ör. geri çağrılmış lotun çevrimdışı satışı"
            color="var(--warning)"
            onClick={() => navigate('/uyarilar')}
          />
        </Col>
        <Col xs={12} lg={6}>
          <StatTile
            label="Defter bütünlüğü"
            value={passed != null && total ? `${passed}/${total}` : '—'}
            hint={passed === total ? 'Bütün kurallar tutarlı' : 'Bütünlük raporuna bakın'}
            color={passed === total ? 'var(--success)' : 'var(--danger)'}
            onClick={() => navigate('/raporlar/integrity')}
          />
        </Col>
      </Row>

      <Row gutter={16}>
        <Col xs={24} lg={14}>
          <Card size="small" title="Şartname senaryosu (Görev 3)" style={{ marginBottom: 16 }}>
            <Typography.Paragraph type="secondary">
              ET-2026-001 (100 kg et) → URT-2026-045 → SUC-2026-045 (85 paket) → Market A 30 / B 25 / C 30. Etkilenen
              marketleri tek tıkla bulun, gerekirse geri çağırma başlatın.
            </Typography.Paragraph>
            <Space wrap>
              <Button type="primary" onClick={() => navigate(tracePath('ET-2026-001'))}>
                ET-2026-001 nereye gitti?
              </Button>
              <Button onClick={() => navigate(tracePath('SUC-2026-045', 'backward'))}>SUC-2026-045 neden yapıldı?</Button>
              <Button onClick={() => navigate('/raporlar')}>Raporlar</Button>
              <Button onClick={() => navigate('/yapay-zeka')}>Yapay zekâ</Button>
            </Space>
          </Card>
          <Card size="small" title="Hızlı işlemler" style={{ marginBottom: 16 }}>
            <Space wrap>
              <Button onClick={() => navigate('/uretim/yeni')}>Yeni dış üretim emri</Button>
              <Button onClick={() => navigate('/parcalama/yeni')}>Yeni parçalama</Button>
              <Button onClick={() => navigate('/alislar/yeni')}>Hammadde alışı</Button>
              <Button onClick={() => navigate('/transferler')}>Araca yükleme</Button>
              <Button onClick={() => navigate('/satislar')}>Satışlar ve iadeler</Button>
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
