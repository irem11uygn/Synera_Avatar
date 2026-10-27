import { useQuery } from '@tanstack/react-query'
import { Alert, Descriptions, Spin, Tag } from 'antd'
import { fetchHealth } from '../api/health'
import { t } from '../lib/i18n'

function StatusTag({ ok }: { ok: boolean }) {
  return <Tag color={ok ? 'success' : 'error'}>{ok ? t('Çalışıyor') : t('Ulaşılamıyor')}</Tag>
}

export function SystemStatus() {
  const { data, error, isPending } = useQuery({
    queryKey: ['health'],
    queryFn: fetchHealth,
    refetchInterval: 10_000,
  })

  if (isPending) return <Spin />
  if (error) return <Alert type="error" showIcon title={t("API'ye ulaşılamadı")} description={error.message} />

  return (
    <Descriptions
      column={1}
      size="small"
      bordered
      items={[
        { key: 'api', label: 'API', children: <StatusTag ok /> },
        { key: 'db', label: t('Veritabanı (MySQL)'), children: <StatusTag ok={data.database === 'ok'} /> },
        { key: 'version', label: t('Sürüm'), children: data.version },
      ]}
    />
  )
}
