// Geri çağırma ayrıntısı (FR-306…FR-308, FR-310): etkilenen lotlar, bizdeki stok, market bazında
// miktar + iletişim + satış belgeleri + ikinci kademe; CSV iletişim listesi; iade alma, ikinci kademe
// kaydı ve kapatma (imha / serbest).

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  Alert,
  App as AntApp,
  Button,
  Card,
  Col,
  DatePicker,
  Form,
  Input,
  Radio,
  Row,
  Select,
  Space,
  Spin,
  Table,
  Tag,
  Typography,
  type TableColumnsType,
} from 'antd'
import { useState } from 'react'
import { api, errorMessage } from '../api/client'
import { refreshBusinessData, usePartners, useWarehouses } from '../api/queries'
import type { Recall, RecallResolution, Recipient, Trace } from '../api/types'
import { Stat } from '../components/Stat'
import { FormModal } from '../components/FormModal'
import { Link } from '../components/Link'
import { Page } from '../components/Page'
import { QueryError } from '../components/QueryError'
import { LotStatusTag } from '../components/StatusTags'
import { RECIPIENT_COLUMNS } from '../components/recipientColumns'
import { TraceFlow } from '../components/TraceFlow'
import { compare, sum } from '../lib/decimal'
import { downloadFile } from '../lib/download'
import { formatDateTime, formatQty, unitLabel } from '../lib/format'
import { LOT_ORIGIN, RECALL_RESOLUTION, RECALL_STATUS, WAREHOUSE_KIND, options } from '../lib/labels'
import { tracePath } from '../lib/paths'
import { decimalRule, toApiDecimal } from '../lib/rules'
import { t } from '../lib/i18n'

type ReturnValues = { sale_line_id: number; qty: string; warehouse_id?: number; reason?: string }
type OnwardValues = {
  sale_line_id: number
  recipient_partner_id: number
  qty: string
  delivered_at?: { format: (pattern: string) => string }
  source_note?: string
}

function ReturnModal({ recipient, onClose }: { recipient: Recipient | null; onClose: () => void }) {
  const queryClient = useQueryClient()
  const warehouses = useWarehouses()
  const mutation = useMutation({
    mutationFn: (values: ReturnValues) =>
      api('/returns', { method: 'POST', body: { ...values, qty: toApiDecimal(values.qty, 3) } }),
    onSuccess: () => refreshBusinessData(queryClient),
  })
  if (!recipient) return null
  return (
    <FormModal<ReturnValues>
      title={`${recipient.customer} — iade al (${recipient.lot_no})`}
      open
      onClose={onClose}
      onSubmit={(values) => mutation.mutateAsync(values)}
      initialValues={{ sale_line_id: recipient.sales[0]?.sale_line_id, reason: t('Geri çağırma') }}
      okText={t('İadeyi kaydet')}
    >
      <Form.Item name="sale_line_id" label={t('Satış')} rules={[{ required: true }]}>
        <Select
          options={recipient.sales.map((s) => ({
            value: s.sale_line_id,
            label: `${s.sale_no} · ${formatQty(s.qty, recipient.base_unit)} (iade ${formatQty(s.returned_qty, recipient.base_unit)})`,
          }))}
        />
      </Form.Item>
      <Form.Item
        name="qty"
        label={t('Miktar ({unit}) — müşteride {qty}', { unit: unitLabel(recipient.base_unit), qty: formatQty(recipient.qty, recipient.base_unit) })}
        rules={[decimalRule(t('Miktar'), { maxFraction: 3, integer: recipient.base_unit === 'ADET' })]}
      >
        <Input inputMode="decimal" autoComplete="off" />
      </Form.Item>
      <Form.Item name="warehouse_id" label={t('Giriş deposu')} extra={t('Boş bırakılırsa ana depo')}>
        <Select
          allowClear
          options={(warehouses.data ?? []).map((w) => ({ value: w.id, label: `${w.name} (${WAREHOUSE_KIND[w.kind]})` }))}
        />
      </Form.Item>
      <Form.Item name="reason" label={t('Neden')}>
        <Input maxLength={255} />
      </Form.Item>
      <Typography.Text type="secondary">
        {t('Mal aynı lot numarasıyla depoya döner; satışa kapalı lota da iade alınır. Değeri satıştaki maliyetin payıdır.')}
      </Typography.Text>
    </FormModal>
  )
}

function OnwardModal({ recipient, onClose }: { recipient: Recipient | null; onClose: () => void }) {
  const queryClient = useQueryClient()
  const partners = usePartners()
  const mutation = useMutation({
    mutationFn: ({ sale_line_id, delivered_at, ...values }: OnwardValues) =>
      api(`/sale-lines/${sale_line_id}/onward-deliveries`, {
        method: 'POST',
        body: { ...values, qty: toApiDecimal(values.qty, 3), delivered_at: delivered_at?.format('YYYY-MM-DD') },
      }),
    onSuccess: () => refreshBusinessData(queryClient),
  })
  if (!recipient) return null
  return (
    <FormModal<OnwardValues>
      title={t('{customer} — müşterinin dağıttığı yer', { customer: recipient.customer })}
      open
      onClose={onClose}
      onSubmit={(values) => mutation.mutateAsync(values)}
      initialValues={{ sale_line_id: recipient.sales[0]?.sale_line_id }}
    >
      <Form.Item name="sale_line_id" label={t('Satış')} rules={[{ required: true }]}>
        <Select options={recipient.sales.map((s) => ({ value: s.sale_line_id, label: s.sale_no }))} />
      </Form.Item>
      <Form.Item name="recipient_partner_id" label={t('Müşterinin alıcısı (şube, bayi…)')} rules={[{ required: true }]}>
        <Select
          showSearch
          optionFilterProp="label"
          options={(partners.data ?? [])
            .filter((p) => p.id !== recipient.customer_id)
            .map((p) => ({ value: p.id, label: p.name }))}
        />
      </Form.Item>
      <Form.Item
        name="qty"
        label={`Miktar (${unitLabel(recipient.base_unit)})`}
        rules={[decimalRule(t('Miktar'), { maxFraction: 3, integer: recipient.base_unit === 'ADET' })]}
      >
        <Input inputMode="decimal" autoComplete="off" />
      </Form.Item>
      <Form.Item name="delivered_at" label={t('Teslim tarihi')}>
        <DatePicker format="DD.MM.YYYY" style={{ width: '100%' }} />
      </Form.Item>
      <Form.Item name="source_note" label={t('Bilginin kaynağı')}>
        <Input maxLength={255} placeholder={t("Market B'nin e-postası")} />
      </Form.Item>
      <Typography.Text type="secondary">
        {t('Müşteri malı kendi şubesine ya da alıcısına verdiyse buraya yazın; geri çağırmada onlara da ulaşılır.')}
      </Typography.Text>
    </FormModal>
  )
}

function CloseModal({ recall, open, onClose }: { recall: Recall; open: boolean; onClose: () => void }) {
  const queryClient = useQueryClient()
  const mutation = useMutation({
    mutationFn: (values: { resolution: RecallResolution; note?: string }) =>
      api<Recall>(`/recalls/${recall.id}/close`, { method: 'POST', body: values }),
    onSuccess: () => refreshBusinessData(queryClient),
  })
  return (
    <FormModal<{ resolution: RecallResolution; note?: string }>
      title={`${recall.recall_no} kapat`}
      open={open}
      onClose={onClose}
      onSubmit={(values) => mutation.mutateAsync(values)}
      initialValues={{ resolution: 'IMHA' }}
      okText={t('Kapat')}
    >
      <Form.Item name="resolution" label={t('Sonuç')} rules={[{ required: true }]}>
        <Radio.Group options={options(RECALL_RESOLUTION)} style={{ display: 'grid', gap: 8 }} />
      </Form.Item>
      <Form.Item name="note" label={t('Not')}>
        <Input.TextArea rows={2} maxLength={500} />
      </Form.Item>
    </FormModal>
  )
}

export default function RecallDetailPage({ id }: { id: number }) {
  const { message } = AntApp.useApp()
  const recall = useQuery({ queryKey: ['recall', id], queryFn: () => api<Recall>(`/recalls/${id}`) })
  const sourceLot = recall.data?.source_lot_no
  const trace = useQuery({
    queryKey: ['trace', 'forward', sourceLot],
    queryFn: () => api<Trace>(`/trace/forward/${encodeURIComponent(sourceLot!)}`),
    enabled: Boolean(sourceLot),
  })
  const [returning, setReturning] = useState<Recipient | null>(null)
  const [onward, setOnward] = useState<Recipient | null>(null)
  const [closing, setClosing] = useState(false)
  const [downloading, setDownloading] = useState(false)

  if (recall.isError) {
    return (
      <Page title={t('Geri çağırma')}>
        <QueryError error={recall.error} onRetry={() => recall.refetch()} />
      </Page>
    )
  }
  if (recall.isPending) return <Spin />
  const data = recall.data
  const open = data.status === 'ACIK'

  async function download() {
    setDownloading(true)
    try {
      await downloadFile(`/recalls/${data.id}/export.csv`, {}, `${data.recall_no}.csv`)
    } catch (error) {
      message.error(errorMessage(error))
    } finally {
      setDownloading(false)
    }
  }

  const heldText =
    Object.entries(data.held_by_customers)
      .map(([unit, qty]) => formatQty(qty, unit as 'KG' | 'ADET'))
      .join(' + ') || '0'
  const stockText =
    (['ADET', 'KG'] as const)
      .map((unit) => {
        const rows = data.stock.filter((s) => s.base_unit === unit)
        return rows.length ? formatQty(sum(rows.map((s) => s.qty), 3), unit) : null
      })
      .filter(Boolean)
      .join(' + ') || '0'

  const actionColumn: TableColumnsType<Recipient>[number] = {
    title: t('İşlem'),
    key: 'actions',
    fixed: 'right',
    render: (_, r) => (
      <Space orientation="vertical" size={4}>
        <Button size="small" onClick={() => setReturning(r)} disabled={compare(r.qty, '0') <= 0}>
          {t('İade al')}
        </Button>
        <Button size="small" onClick={() => setOnward(r)}>
          {t('Dağıttığı yeri ekle')}
        </Button>
      </Space>
    ),
  }

  return (
    <Page
      title={t('Geri çağırma {no}', { no: data.recall_no })}
      back={{ to: '/geri-cagirma', label: t('Geri çağırmalar') }}
      extra={
        <>
          <Button onClick={download} loading={downloading}>
            {t('İletişim listesi (CSV)')}
          </Button>
          <Link to={tracePath(data.source_lot_no)}>{t('İzleme ekranı')}</Link>
          {open && (
            <Button type="primary" onClick={() => setClosing(true)}>
              {t('Geri çağırmayı kapat')}
            </Button>
          )}
        </>
      }
    >
      <Alert
        type={open ? 'error' : 'info'}
        showIcon
        style={{ marginBottom: 16 }}
        title={
          open
            ? t('Açık: {lot} ve ondan yapılan bütün lotlar satışa kapalı — mağazada ve araçta satılamaz, aktarılamaz, üretimde kullanılamaz.', { lot: data.source_lot_no })
            : t('Kapandı ({how}) — {at}', { how: data.resolution ? RECALL_RESOLUTION[data.resolution] : '', at: formatDateTime(data.closed_at) })
        }
        description={t('Neden: {reason} · Başlatan: {who} · {at}', { reason: data.reason, who: data.started_by_name ?? '—', at: formatDateTime(data.started_at) })}
      />

      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col xs={12} lg={6}>
          <Stat label={t('Etkilenen lot')} value={data.lot_count} tone="danger" hint={t('Hepsi satışa kapalı')} />
        </Col>
        <Col xs={12} lg={6}>
          <Stat label={t('Alıcı (market)')} value={data.customer_count} tone="brand" />
        </Col>
        <Col xs={12} lg={6}>
          <Stat label={t('Müşterilerde kalan')} value={heldText} tone="warning" />
        </Col>
        <Col xs={12} lg={6}>
          <Stat
            label={t('Bizdeki stok')}
            value={stockText}
            tone="success"
            hint={data.violation_count ? t('{n} çevrimdışı ihlal', { n: data.violation_count }) : t('İhlal yok')}
          />
        </Col>
      </Row>

      <Card size="small" title={t('Etkilenen zincir')} style={{ marginBottom: 16 }}>
        {trace.data ? (
          <TraceFlow lots={trace.data.lots} links={trace.data.links} recipients={trace.data.recipients} direction="forward" />
        ) : (
          <Spin />
        )}
      </Card>

      <Card size="small" title={t('Geri çağırma listesi: alıcılar, miktarlar, iletişim')} style={{ marginBottom: 16 }}>
        <Table<Recipient>
          rowKey={(r) => `${r.customer_id}-${r.lot_no}`}
          size="small"
          pagination={false}
          scroll={{ x: 'max-content' }}
          dataSource={data.recipients}
          columns={[...RECIPIENT_COLUMNS, actionColumn]}
          locale={{ emptyText: t('Etkilenen lotlardan satış yapılmamış.') }}
        />
      </Card>

      <Row gutter={16}>
        <Col xs={24} lg={12}>
          <Card size="small" title={t('Etkilenen lotlar')} style={{ marginBottom: 16 }}>
            <Table
              rowKey="lot_no"
              size="small"
              pagination={false}
              dataSource={data.lots}
              columns={[
                { title: t('Lot'), dataIndex: 'lot_no', render: (no: string) => <Link to={`/lotlar/${no}`}>{no}</Link> },
                { title: t('Ürün'), dataIndex: 'product_name' },
                { title: t('Köken'), dataIndex: 'origin', render: (o: keyof typeof LOT_ORIGIN) => LOT_ORIGIN[o] },
                { title: t('Kademe'), dataIndex: 'depth', align: 'right' },
                { title: t('Durum'), dataIndex: 'status', render: (s: 'AKTIF' | 'BLOKE') => <LotStatusTag status={s} /> },
              ]}
            />
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card size="small" title={t('Bizdeki stok')} style={{ marginBottom: 16 }}>
            <Table
              rowKey={(r) => `${r.lot_no}-${r.warehouse_code}`}
              size="small"
              pagination={false}
              dataSource={data.stock}
              locale={{ emptyText: t('Bizde stok yok.') }}
              columns={[
                { title: t('Lot'), dataIndex: 'lot_no' },
                { title: t('Depo'), dataIndex: 'warehouse_name' },
                { title: t('Miktar'), dataIndex: 'qty', align: 'right', render: (v: string, r) => formatQty(v, r.base_unit) },
              ]}
            />
            {open && data.stock.length > 0 && (
              <Typography.Paragraph type="secondary" style={{ marginTop: 8, marginBottom: 0 }}>
                {t('"İmha" ile kapatınca bu stok fire/imha olarak düşülür.')}
              </Typography.Paragraph>
            )}
          </Card>
        </Col>
      </Row>

      <Tag>{RECALL_STATUS[data.status]}</Tag>
      <ReturnModal recipient={returning} onClose={() => setReturning(null)} />
      <OnwardModal recipient={onward} onClose={() => setOnward(null)} />
      <CloseModal recall={data} open={closing} onClose={() => setClosing(false)} />
    </Page>
  )
}
