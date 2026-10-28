// Denetim günlüğü (yalnız yönetici): kim, ne zaman, ne yaptı. Kayıtlar değiştirilemez, silinemez.

import { DownloadOutlined } from '@ant-design/icons'
import { useQuery } from '@tanstack/react-query'
import { App, Button, Card, DatePicker, Input, Select, Space, Table, Tag } from 'antd'
import { useState } from 'react'
import { api, errorMessage } from '../api/client'
import type { AuditRow, Severity, UserAdmin } from '../api/types'
import { SeverityIcon } from '../components/AlarmBell'
import { Page } from '../components/Page'
import { QueryError } from '../components/QueryError'
import { useDebounced } from '../lib/useDebounced'
import { downloadFile } from '../lib/download'
import { formatDateTime } from '../lib/format'
import { t } from '../lib/i18n'
import { AUDIT_ACTION, SEVERITY } from '../lib/labels'

type Filter = { q?: string; severity?: Severity; username?: string; day_from?: string; day_to?: string }

const SEVERITY_COLOR: Record<Severity, string> = { KRITIK: 'red', UYARI: 'orange', BILGI: 'default' }
const isoDay = (text: string) => (text ? text.split('.').reverse().join('-') : undefined)

export default function AuditPage() {
  const { message } = App.useApp()
  const [filter, setFilter] = useState<Filter>({})
  const [text, setText] = useState('')
  const q = useDebounced(text.trim(), 300)
  const query = { ...filter, q: q || undefined }
  const rows = useQuery({ queryKey: ['audit', query], queryFn: () => api<AuditRow[]>('/audit', { query }) })
  const users = useQuery({ queryKey: ['users'], queryFn: () => api<UserAdmin[]>('/users') })
  const [downloading, setDownloading] = useState(false)

  const download = async () => {
    setDownloading(true)
    try {
      await downloadFile('/audit/export.csv', query, 'denetim_gunlugu.csv')
    } catch (error) {
      message.error(errorMessage(error))
    } finally {
      setDownloading(false)
    }
  }

  return (
    <Page
      title={t('Denetim günlüğü')}
      description={t('Sistemde yapılan her önemli işin kaydı: kim, ne zaman, ne yaptı. Hatalı giriş denemeleri de burada. Kayıtlar değiştirilemez ve silinemez.')}
      extra={
        <Button type="primary" icon={<DownloadOutlined />} loading={downloading} onClick={() => void download()}>
          {t('CSV indir')}
        </Button>
      }
    >
      <Card size="small">
        <Space wrap style={{ marginBottom: 12 }}>
          <Input.Search
            allowClear
            placeholder={t('Ara: lot, belge, kullanıcı…')}
            aria-label={t('Ara')}
            style={{ width: 260 }}
            value={text}
            onChange={(event) => setText(event.target.value)}
          />
          <Select<Severity>
            allowClear
            placeholder={t('Önem')}
            aria-label={t('Önem')}
            style={{ width: 140 }}
            value={filter.severity}
            onChange={(severity) => setFilter((f) => ({ ...f, severity }))}
            options={(['KRITIK', 'UYARI', 'BILGI'] as Severity[]).map((value) => ({ value, label: SEVERITY[value] }))}
          />
          <Select<string>
            allowClear
            showSearch
            optionFilterProp="label"
            placeholder={t('Kullanıcı')}
            aria-label={t('Kullanıcı')}
            style={{ width: 200 }}
            value={filter.username}
            onChange={(username) => setFilter((f) => ({ ...f, username }))}
            options={(users.data ?? []).map((u) => ({ value: u.username, label: `${u.full_name} (${u.username})` }))}
          />
          <DatePicker.RangePicker
            format="DD.MM.YYYY"
            aria-label={t('Tarih aralığı')}
            onChange={(_, [from, to]) => setFilter((f) => ({ ...f, day_from: isoDay(from), day_to: isoDay(to) }))}
          />
        </Space>
        {rows.isError && <QueryError error={rows.error} onRetry={() => rows.refetch()} />}
        <Table<AuditRow>
          rowKey="id"
          size="small"
          loading={rows.isPending}
          dataSource={rows.data}
          pagination={{ pageSize: 25, hideOnSinglePage: true, showSizeChanger: false }}
          scroll={{ x: 'max-content' }}
          locale={{ emptyText: t('Bu süzgece uyan kayıt yok.') }}
          columns={[
            { title: t('Zaman'), dataIndex: 'created_at', render: formatDateTime, width: 150 },
            {
              title: t('Kullanıcı'),
              key: 'user',
              render: (_, row) =>
                row.full_name ? (
                  <>
                    {row.full_name}
                    <div className="muted">{row.username}</div>
                  </>
                ) : (
                  <span className="muted">{row.username ?? t('Sistem')}</span>
                ),
            },
            {
              title: t('Önem'),
              dataIndex: 'severity',
              render: (value: Severity) => (
                <Tag color={SEVERITY_COLOR[value]} icon={<SeverityIcon severity={value} />}>
                  {' '}
                  {SEVERITY[value]}
                </Tag>
              ),
            },
            { title: t('İşlem'), dataIndex: 'action', render: (code: string) => AUDIT_ACTION[code] ?? code },
            {
              title: t('Açıklama'),
              dataIndex: 'message',
              render: (value: string) => <span style={{ whiteSpace: 'normal', display: 'block', minWidth: 260, maxWidth: 640 }}>{value}</span>,
            },
            { title: t('Adres'), dataIndex: 'client', render: (value: string | null) => value ?? '—' },
          ]}
        />
      </Card>
    </Page>
  )
}
