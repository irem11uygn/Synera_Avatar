import { useQuery } from '@tanstack/react-query'
import { Alert, Card, Descriptions, Layout, Spin, Tag, Typography } from 'antd'
import { fetchHealth } from './api/health'

const { Header, Content } = Layout

function StatusTag({ ok }: { ok: boolean }) {
  return <Tag color={ok ? 'success' : 'error'}>{ok ? 'Çalışıyor' : 'Ulaşılamıyor'}</Tag>
}

function SystemStatus() {
  const { data, error, isPending } = useQuery({
    queryKey: ['health'],
    queryFn: fetchHealth,
    refetchInterval: 10_000,
  })

  if (isPending) return <Spin />
  if (error) return <Alert type="error" showIcon message="API'ye ulaşılamadı" description={error.message} />

  return (
    <Descriptions
      column={1}
      bordered
      items={[
        { key: 'api', label: 'API', children: <StatusTag ok /> },
        { key: 'db', label: 'Veritabanı (MySQL)', children: <StatusTag ok={data.database === 'ok'} /> },
        { key: 'version', label: 'Sürüm', children: data.version },
      ]}
    />
  )
}

export default function App() {
  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Header>
        <Typography.Title level={4} style={{ color: '#fff', margin: '14px 0' }}>
          AVATAR — Üretim, Maliyet ve Lot İzlenebilirliği
        </Typography.Title>
      </Header>
      <Content style={{ padding: 24, maxWidth: 720 }}>
        <Card title="Sistem durumu">
          <SystemStatus />
        </Card>
      </Content>
    </Layout>
  )
}
