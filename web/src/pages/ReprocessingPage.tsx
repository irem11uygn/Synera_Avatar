// Yeniden işleme (FR-303): işletme içinde lotlardan yeni lot (ör. iade gelen sucuğun yeniden
// paketlenmesi). Girdiler ana depodan tüketilir; yeni lotun değeri = girdilerin değeri + ek maliyet.

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Button, Card, Form, Input, Select, Space, Table, Typography } from 'antd'
import { useState } from 'react'
import { api } from '../api/client'
import { refreshBusinessData, useProducts } from '../api/queries'
import type { Reprocess } from '../api/types'
import { FormModal } from '../components/FormModal'
import { Link } from '../components/Link'
import { Page } from '../components/Page'
import { QueryError } from '../components/QueryError'
import { formatDate, formatDateTime, formatMoney, formatQty, formatUnitCost } from '../lib/format'
import { decimalRule, textOrNull, toApiDecimal } from '../lib/rules'

type Values = {
  inputs: { lot_no?: string; qty?: string }[]
  output_product_id: number
  output_qty: string
  extra_cost?: string
  note?: string
}

function NewReprocessModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const queryClient = useQueryClient()
  const products = useProducts()
  const mutation = useMutation({
    mutationFn: (values: Values) =>
      api<Reprocess>('/reprocessing', {
        method: 'POST',
        body: {
          inputs: values.inputs.map((i) => ({ lot_no: i.lot_no!.trim(), qty: toApiDecimal(i.qty, 3) })),
          output_product_id: values.output_product_id,
          output_qty: toApiDecimal(values.output_qty, 3),
          extra_cost: toApiDecimal(values.extra_cost, 2) ?? '0',
          note: textOrNull(values.note),
        },
      }),
    onSuccess: () => refreshBusinessData(queryClient),
  })
  return (
    <FormModal<Values>
      title="Yeni yeniden işleme"
      open={open}
      onClose={onClose}
      width={640}
      initialValues={{ inputs: [{}], extra_cost: '0' }}
      onSubmit={(values) => mutation.mutateAsync(values)}
      okText="İşle ve yeni lotu aç"
    >
      <Typography.Paragraph type="secondary">
        Girdiler ana depodan tüketilir. Bloke lot kullanılamaz. Yeni lot girdilerine miktarlarıyla bağlanır; izleme
        ekranında görünür.
      </Typography.Paragraph>
      <Form.List name="inputs">
        {(fields, { add, remove }) => (
          <>
            {fields.map((field) => (
              <Space key={field.key} align="start" wrap>
                <Form.Item
                  name={[field.name, 'lot_no']}
                  label="Girdi lotu"
                  rules={[{ required: true, message: 'Lot numarasını yazın.' }]}
                >
                  <Input placeholder="SUC-2026-045" style={{ width: 200 }} />
                </Form.Item>
                <Form.Item name={[field.name, 'qty']} label="Miktar" rules={[decimalRule('Miktar', { maxFraction: 3 })]}>
                  <Input inputMode="decimal" style={{ width: 120 }} />
                </Form.Item>
                {fields.length > 1 && (
                  <Button style={{ marginTop: 30 }} onClick={() => remove(field.name)}>
                    Sil
                  </Button>
                )}
              </Space>
            ))}
            <Button onClick={() => add({})} style={{ marginBottom: 16 }}>
              Girdi ekle
            </Button>
          </>
        )}
      </Form.List>
      <Form.Item name="output_product_id" label="Çıktı ürünü" rules={[{ required: true, message: 'Ürünü seçin.' }]}>
        <Select
          showSearch
          optionFilterProp="label"
          options={(products.data ?? []).map((p) => ({ value: p.id, label: `${p.code} · ${p.name}` }))}
        />
      </Form.Item>
      <Space wrap>
        <Form.Item name="output_qty" label="Çıktı miktarı" rules={[decimalRule('Çıktı miktarı', { maxFraction: 3 })]}>
          <Input inputMode="decimal" style={{ width: 160 }} />
        </Form.Item>
        <Form.Item
          name="extra_cost"
          label="Ek maliyet (€)"
          rules={[decimalRule('Ek maliyet', { maxFraction: 2, allowZero: true, required: false })]}
          extra="İşçilik, ambalaj"
        >
          <Input inputMode="decimal" style={{ width: 160 }} />
        </Form.Item>
      </Space>
      <Form.Item name="note" label="Açıklama">
        <Input maxLength={500} placeholder="İade gelen paketler yeniden etiketlendi" />
      </Form.Item>
    </FormModal>
  )
}

export default function ReprocessingPage() {
  const records = useQuery({ queryKey: ['reprocessing'], queryFn: () => api<Reprocess[]>('/reprocessing') })
  const [open, setOpen] = useState(false)
  return (
    <Page
      title="Yeniden işleme"
      extra={
        <Button type="primary" onClick={() => setOpen(true)}>
          Yeni yeniden işleme
        </Button>
      }
    >
      <Card size="small">
        {records.isError && <QueryError error={records.error} onRetry={() => records.refetch()} />}
        <Table<Reprocess>
          rowKey="id"
          size="small"
          loading={records.isPending}
          dataSource={records.data}
          pagination={false}
          scroll={{ x: 'max-content' }}
          locale={{ emptyText: 'Henüz yeniden işleme yok. Örnek: iade gelen sucuğun yeniden paketlenmesi.' }}
          columns={[
            { title: 'Belge', dataIndex: 'order_no' },
            { title: 'Zaman', dataIndex: 'completed_at', render: formatDateTime },
            {
              title: 'Girdiler',
              key: 'inputs',
              render: (_, r) =>
                r.inputs.map((i) => (
                  <div key={i.lot_no}>
                    <Link to={`/lotlar/${i.lot_no}`}>{i.lot_no}</Link> · {formatQty(i.qty, i.base_unit)} ·{' '}
                    {formatMoney(i.value)}
                  </div>
                )),
            },
            {
              title: 'Yeni lot',
              dataIndex: 'output_lot_no',
              render: (no: string | null) => (no ? <Link to={`/lotlar/${no}`}>{no}</Link> : '—'),
            },
            { title: 'Ürün', dataIndex: 'output_product_name' },
            { title: 'Miktar', dataIndex: 'output_qty', align: 'right', render: (v: string, r) => formatQty(v, r.base_unit) },
            { title: 'Ek maliyet', dataIndex: 'extra_cost', align: 'right', render: formatMoney },
            { title: 'Lot değeri', dataIndex: 'total_value', align: 'right', render: formatMoney },
            { title: 'Birim maliyet', dataIndex: 'unit_cost', align: 'right', render: formatUnitCost },
            { title: 'SKT', dataIndex: 'expiry_date', render: formatDate },
            { title: 'Açıklama', dataIndex: 'note', render: (v: string | null) => v ?? '—' },
          ]}
        />
      </Card>
      <NewReprocessModal open={open} onClose={() => setOpen(false)} />
    </Page>
  )
}
