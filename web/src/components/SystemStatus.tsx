import { useQuery } from '@tanstack/react-query'
import { Alert, Descriptions, Spin, Tag } from 'antd'
import { fetchHealth } from '../api/health'

function StatusTag({ ok }: { ok: boolean }) {
  return <Tag color={ok ? 'success' : 'error'}>{ok ? 'Çalışıyor' : 'Ulaşılamıyor'}</Tag>
}

export function SystemStatus() {
  const { data, error, isPending } = useQuery({
    queryKey: ['health'],
    queryFn: fetchHealth,
    refetchInterval: 10_000,
  })

  if (isPending) return <Spin />
  if (error) return <Alert type="error" showIcon title="API'ye ulaşılamadı" description={error.message} />

  return (
    <Descriptions
      column={1}
      size="small"
      bordered
      items={[
        { key: 'api', label: 'API', children: <StatusTag ok /> },
        { key: 'db', label: 'Veritabanı (MySQL)', children: <StatusTag ok={data.database === 'ok'} /> },
        { key: 'version', label: 'Sürüm', children: data.version },
      ]}
    />
  )
}
