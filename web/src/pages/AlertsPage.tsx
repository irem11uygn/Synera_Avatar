// Alarm merkezi: kural motorunun ve iş olaylarının açtığı alarmlar (verim sapması, fiyat artışı,
// bloke lot, geri çağırma, çevrimdışı ihlal, hatalı giriş). Okundu işaretleyen ve zamanı kaydedilir.

import { CheckOutlined, ThunderboltOutlined } from '@ant-design/icons'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { App, Button, Card, Col, Row, Segmented, Select, Space, Table, Tag } from 'antd'
import { useState } from 'react'
import { api } from '../api/client'
import type { AlertRow, AlertSummary, RuleRun, Severity } from '../api/types'
import { useSession } from '../auth/context'
import { SeverityIcon } from '../components/AlarmBell'
import { Page } from '../components/Page'
import { QueryError } from '../components/QueryError'
import { Stat } from '../components/Stat'
import { formatDateTime } from '../lib/format'
import { t } from '../lib/i18n'
import { ALERT_KIND, SEVERITY } from '../lib/labels'

const SEVERITY_COLOR: Record<Severity, string> = { KRITIK: 'red', UYARI: 'orange', BILGI: 'blue' }

export default function AlertsPage() {
  const { user } = useSession()
  const { message } = App.useApp()
  const [onlyOpen, setOnlyOpen] = useState(true)
  const [severity, setSeverity] = useState<Severity | undefined>()
  const queryClient = useQueryClient()
  const alerts = useQuery({
    queryKey: ['alerts', 'list', onlyOpen, severity ?? 'all'],
    queryFn: () => api<AlertRow[]>('/alerts', { query: { only_open: onlyOpen, severity } }),
  })
  const summary = useQuery({ queryKey: ['alerts', 'summary'], queryFn: () => api<AlertSummary>('/alerts/summary') })
  const refresh = () => queryClient.invalidateQueries({ queryKey: ['alerts'] })
  const ack = useMutation({
    mutationFn: (id: number) => api<AlertRow>(`/alerts/${id}/ack`, { method: 'POST' }),
    onSuccess: refresh,
  })
  const ackAll = useMutation({
    mutationFn: () => api<AlertRow[]>('/alerts/ack-all', { method: 'POST' }),
    onSuccess: (rows) => {
      message.success(t('{n} alarm okundu işaretlendi.', { n: rows.length }))
      void refresh()
    },
  })
  const runRules = useMutation({
    mutationFn: () => api<RuleRun>('/alerts/run-rules', { method: 'POST' }),
    onSuccess: (run) => {
      message.success(
        run.created.length > 0
          ? t('Kurallar çalıştı: {n} yeni alarm.', { n: run.created.length })
          : t('Kurallar çalıştı: yeni alarm yok.'),
      )
      run.notes.forEach((note) => message.warning(note))
      void refresh()
    },
  })

  const canAckSome = (alerts.data ?? []).some((row) => row.can_acknowledge)
  return (
    <Page
      title={t('Alarm merkezi')}
      description={t('Sistemin kendiliğinden açtığı alarmlar: verim beklenenden çok farklı, alış fiyatı birden arttı, bloke lotta stok kaldı, geri çağırma başladı, bloke lot satılmak istendi, art arda hatalı giriş. Kritik alarmlar yönetici ve kaliteye e-postayla da gider.')}
      extra={
        <>
          {user.role === 'YONETICI' && (
            <Button icon={<ThunderboltOutlined />} loading={runRules.isPending} onClick={() => runRules.mutate()}>
              {t('Kuralları şimdi çalıştır')}
            </Button>
          )}
          <Button icon={<CheckOutlined />} disabled={!canAckSome || !onlyOpen} loading={ackAll.isPending} onClick={() => ackAll.mutate()}>
            {t('Hepsini okundu say')}
          </Button>
        </>
      }
    >
      <Row gutter={[12, 12]} style={{ marginBottom: 16 }}>
        <Col xs={24} sm={8}>
          <Stat
            label={t('Açık kritik alarm')}
            value={summary.data?.open_critical ?? '—'}
            tone={(summary.data?.open_critical ?? 0) > 0 ? 'danger' : 'success'}
            hint={t('Hemen bakılmalı')}
            onClick={() => {
              setOnlyOpen(true)
              setSeverity('KRITIK')
            }}
          />
        </Col>
        <Col xs={24} sm={8}>
          <Stat
            label={t('Açık uyarı')}
            value={summary.data?.open_warning ?? '—'}
            tone={(summary.data?.open_warning ?? 0) > 0 ? 'warning' : 'success'}
            hint={t('Gün içinde bakılmalı')}
            onClick={() => {
              setOnlyOpen(true)
              setSeverity('UYARI')
            }}
          />
        </Col>
        <Col xs={24} sm={8}>
          <Stat
            label={t('Toplam açık')}
            value={summary.data?.open_total ?? '—'}
            tone="brand"
            hint={t('Okundu işaretlenmemiş')}
            onClick={() => {
              setOnlyOpen(true)
              setSeverity(undefined)
            }}
          />
        </Col>
      </Row>
      <Card size="small">
        <Space wrap style={{ marginBottom: 12 }}>
          <Segmented<boolean>
            value={onlyOpen}
            onChange={setOnlyOpen}
            options={[
              { value: true, label: t('Açık') },
              { value: false, label: t('Hepsi') },
            ]}
          />
          <Select<Severity | 'ALL'>
            style={{ width: 170 }}
            value={severity ?? 'ALL'}
            onChange={(value) => setSeverity(value === 'ALL' ? undefined : value)}
            aria-label={t('Önem')}
            options={[
              { value: 'ALL', label: t('Bütün önem dereceleri') },
              { value: 'KRITIK', label: SEVERITY.KRITIK },
              { value: 'UYARI', label: SEVERITY.UYARI },
              { value: 'BILGI', label: SEVERITY.BILGI },
            ]}
          />
        </Space>
        {alerts.isError && <QueryError error={alerts.error} onRetry={() => alerts.refetch()} />}
        <Table<AlertRow>
          rowKey="id"
          size="small"
          loading={alerts.isPending}
          dataSource={alerts.data}
          pagination={{ pageSize: 20, hideOnSinglePage: true }}
          scroll={{ x: 'max-content' }}
          locale={{ emptyText: onlyOpen ? t('Açık alarm yok.') : t('Alarm yok.') }}
          rowClassName={(row) => (row.severity === 'KRITIK' && !row.acknowledged_at ? 'row-critical' : '')}
          columns={[
            {
              title: t('Önem'),
              dataIndex: 'severity',
              width: 110,
              render: (value: Severity) => (
                <Tag color={SEVERITY_COLOR[value]} icon={<SeverityIcon severity={value} />}>
                  {' '}
                  {SEVERITY[value]}
                </Tag>
              ),
            },
            { title: t('Tür'), dataIndex: 'kind', render: (kind: AlertRow['kind']) => <strong>{ALERT_KIND[kind]}</strong> },
            { title: t('Açıklama'), dataIndex: 'message', render: (text: string) => <span style={{ whiteSpace: 'normal', display: 'block', minWidth: 280, maxWidth: 620 }}>{text}</span> },
            { title: t('Zaman'), dataIndex: 'created_at', render: formatDateTime },
            {
              title: t('Durum'),
              key: 'state',
              render: (_, row) =>
                row.acknowledged_at ? (
                  <span className="muted">
                    {t('Okundu')} · {formatDateTime(row.acknowledged_at)}
                    {row.acknowledged_by_name && <> · {row.acknowledged_by_name}</>}
                  </span>
                ) : row.can_acknowledge ? (
                  <Button size="small" loading={ack.isPending && ack.variables === row.id} onClick={() => ack.mutate(row.id)}>
                    {t('Okundu işaretle')}
                  </Button>
                ) : (
                  <span className="muted">{t('Açık (ilgili birim işaretler)')}</span>
                ),
            },
          ]}
        />
      </Card>
    </Page>
  )
}
