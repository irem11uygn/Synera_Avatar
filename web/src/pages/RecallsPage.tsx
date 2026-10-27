// Geri çağırmalar listesi ve yeni geri çağırma (FR-306, FR-606).

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Button, Card, Form, Input, Table, Tag, Typography, type TableColumnsType } from 'antd'
import { useState } from 'react'
import { api } from '../api/client'
import { refreshBusinessData } from '../api/queries'
import type { Recall, RecallSummary } from '../api/types'
import { FormModal } from '../components/FormModal'
import { Link } from '../components/Link'
import { LotPicker } from '../components/LotPicker'
import { Page } from '../components/Page'
import { QueryError } from '../components/QueryError'
import { formatDateTime, formatQty } from '../lib/format'
import { RECALL_STATUS } from '../lib/labels'
import { navigate } from '../lib/router'

const COLUMNS: TableColumnsType<RecallSummary> = [
  {
    title: 'Geri çağırma',
    dataIndex: 'recall_no',
    render: (no: string, r) => <Link to={`/geri-cagirma/${r.id}`}>{no}</Link>,
  },
  { title: 'Başlangıç', dataIndex: 'started_at', render: formatDateTime },
  {
    title: 'Durum',
    dataIndex: 'status',
    render: (status: RecallSummary['status'], r) => (
      <Tag color={status === 'ACIK' ? 'red' : 'default'}>
        {RECALL_STATUS[status]}
        {r.resolution ? ` · ${r.resolution === 'IMHA' ? 'imha' : 'serbest'}` : ''}
      </Tag>
    ),
  },
  { title: 'Kaynak lot', dataIndex: 'source_lot_no' },
  { title: 'Neden', dataIndex: 'reason' },
  { title: 'Etkilenen lot', dataIndex: 'lot_count', align: 'right' },
  { title: 'Alıcı', dataIndex: 'customer_count', align: 'right' },
  {
    title: 'Müşterilerde',
    dataIndex: 'held_by_customers',
    align: 'right',
    render: (held: RecallSummary['held_by_customers']) =>
      Object.entries(held)
        .map(([unit, qty]) => formatQty(qty, unit as 'KG' | 'ADET'))
        .join(' + ') || '—',
  },
  {
    title: 'İhlal',
    dataIndex: 'violation_count',
    align: 'right',
    render: (count: number) => (count ? <Tag color="orange">{count}</Tag> : '0'),
  },
]

export function NewRecallModal({ open, onClose, lotNo = '' }: { open: boolean; onClose: () => void; lotNo?: string }) {
  const queryClient = useQueryClient()
  const [lot, setLot] = useState(lotNo)
  const start = useMutation({
    mutationFn: (values: { reason: string }) =>
      api<Recall>('/recalls', { method: 'POST', body: { lot_no: lot.trim(), reason: values.reason } }),
    onSuccess: async (recall) => {
      await refreshBusinessData(queryClient)
      navigate(`/geri-cagirma/${recall.id}`)
    },
  })
  return (
    <FormModal<{ reason: string }>
      title="Yeni geri çağırma"
      open={open}
      onClose={onClose}
      onSubmit={(values) => start.mutateAsync(values)}
      okText="Başlat ve satışa kapat"
    >
      <Form.Item label="Kaynak lot" required>
        <LotPicker value={lot} onChange={setLot} />
      </Form.Item>
      <Form.Item name="reason" label="Neden" rules={[{ required: true, message: 'Nedeni yazın.' }]}>
        <Input.TextArea rows={3} maxLength={500} placeholder="Tedarikçi laboratuvar sonucu: uygunsuz" />
      </Form.Item>
      <Typography.Text type="secondary">
        Kaynak lot ve ondan yapılan bütün lotlar tek işlemde satışa kapatılır; kime gittiği hemen listelenir.
      </Typography.Text>
    </FormModal>
  )
}

export default function RecallsPage() {
  const recalls = useQuery({ queryKey: ['recalls'], queryFn: () => api<RecallSummary[]>('/recalls') })
  const [open, setOpen] = useState(false)
  return (
    <Page
      title="Geri çağırmalar"
      description="Sorunlu bir lot için geri çağırma başlatın: o lot ve ondan yapılan bütün ürünler hemen satışa kapanır, malın gittiği müşteriler listelenir."
      extra={
        <Button danger type="primary" onClick={() => setOpen(true)}>
          Yeni geri çağırma
        </Button>
      }
    >
      <Card size="small">
        {recalls.isError && <QueryError error={recalls.error} onRetry={() => recalls.refetch()} />}
        <Table<RecallSummary>
          rowKey="id"
          size="small"
          loading={recalls.isPending}
          columns={COLUMNS}
          dataSource={recalls.data}
          pagination={false}
          scroll={{ x: 'max-content' }}
          locale={{ emptyText: 'Henüz geri çağırma yok. Bir lotu izleme ekranından ya da buradan geri çağırabilirsiniz.' }}
        />
      </Card>
      <NewRecallModal open={open} onClose={() => setOpen(false)} />
    </Page>
  )
}
