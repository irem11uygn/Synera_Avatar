// Uyarılar: ör. geri çağrılmış lotun çevrimdışı satışı (ADR-004). Okundu işaretlenebilir.

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Button, Card, Segmented, Table, Tag } from 'antd'
import { useState } from 'react'
import { api } from '../api/client'
import type { AlertRow } from '../api/types'
import { Page } from '../components/Page'
import { QueryError } from '../components/QueryError'
import { formatDateTime } from '../lib/format'

export default function AlertsPage() {
  const [onlyOpen, setOnlyOpen] = useState(true)
  const queryClient = useQueryClient()
  const alerts = useQuery({
    queryKey: ['alerts', onlyOpen],
    queryFn: () => api<AlertRow[]>('/alerts', { query: { only_open: onlyOpen } }),
  })
  const ack = useMutation({
    mutationFn: (id: number) => api<AlertRow>(`/alerts/${id}/ack`, { method: 'POST' }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['alerts'] }),
  })

  return (
    <Page
      title="Uyarılar"
      extra={
        <Segmented<boolean>
          value={onlyOpen}
          onChange={setOnlyOpen}
          options={[
            { value: true, label: 'Okunmamış' },
            { value: false, label: 'Hepsi' },
          ]}
        />
      }
    >
      <Card size="small">
        {alerts.isError && <QueryError error={alerts.error} onRetry={() => alerts.refetch()} />}
        <Table<AlertRow>
          rowKey="id"
          size="small"
          loading={alerts.isPending}
          dataSource={alerts.data}
          pagination={false}
          scroll={{ x: 'max-content' }}
          locale={{ emptyText: onlyOpen ? 'Okunmamış uyarı yok.' : 'Uyarı yok.' }}
          columns={[
            { title: 'Zaman', dataIndex: 'created_at', render: formatDateTime },
            { title: 'Tür', dataIndex: 'kind', render: () => <Tag color="orange">Geri çağırma ihlali</Tag> },
            { title: 'Mesaj', dataIndex: 'message' },
            {
              title: 'Durum',
              key: 'state',
              render: (_, row) =>
                row.acknowledged_at ? (
                  `Okundu · ${formatDateTime(row.acknowledged_at)}`
                ) : (
                  <Button size="small" loading={ack.isPending && ack.variables === row.id} onClick={() => ack.mutate(row.id)}>
                    Okundu işaretle
                  </Button>
                ),
            },
          ]}
        />
      </Card>
    </Page>
  )
}
