// Görev 3 — lot izleme (FR-304, FR-305, FR-308). İleri izleme: lottan türeyen lotlar, bizdeki stok,
// alıcılar (miktar, satış belgesi, iletişim, ikinci kademe). Geri izleme: kaynak lotlar, tedarikçiler,
// üretim emirleri ve parçalamalar. Buradan geri çağırma da başlatılır (FR-306).

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  Button,
  Card,
  Col,
  Empty,
  Form,
  Input,
  Row,
  Segmented,
  Space,
  Spin,
  Table,
  Tag,
  Typography,
} from 'antd'
import { useState } from 'react'
import { api } from '../api/client'
import { refreshBusinessData } from '../api/queries'
import type { Recall, Recipient, Trace } from '../api/types'
import { Stat } from '../components/Stat'
import { FormModal } from '../components/FormModal'
import { Link } from '../components/Link'
import { Page } from '../components/Page'
import { QueryError } from '../components/QueryError'
import { LotPicker } from '../components/LotPicker'
import { LotStatusTag } from '../components/StatusTags'
import { ContactInfo } from '../components/ContactInfo'
import { RECIPIENT_COLUMNS } from '../components/recipientColumns'
import { TraceFlow } from '../components/TraceFlow'
import { sum } from '../lib/decimal'
import { formatDate, formatQty } from '../lib/format'
import { LINK_PROCESS, WAREHOUSE_KIND } from '../lib/labels'
import { tracePath } from '../lib/paths'
import { navigate } from '../lib/router'
import { t } from '../lib/i18n'

type Direction = 'forward' | 'backward'

function totalsByUnit(rows: { qty: string; base_unit: 'KG' | 'ADET' }[]): string {
  const units = ['ADET', 'KG'] as const
  const parts = units
    .map((unit) => {
      const values = rows.filter((r) => r.base_unit === unit).map((r) => r.qty)
      return values.length ? formatQty(sum(values, 3), unit) : null
    })
    .filter(Boolean)
  return parts.length ? parts.join(' + ') : '0'
}

function RecallButton({ trace }: { trace: Trace }) {
  const [open, setOpen] = useState(false)
  const queryClient = useQueryClient()
  const start = useMutation({
    mutationFn: (values: { reason: string }) =>
      api<Recall>('/recalls', { method: 'POST', body: { lot_no: trace.source.lot_no, reason: values.reason } }),
    onSuccess: async (recall) => {
      await refreshBusinessData(queryClient)
      navigate(`/geri-cagirma/${recall.id}`)
    },
  })
  if (trace.source.status === 'BLOKE') return <Tag color="red">{t('Bu lot zaten satışa kapalı')}</Tag>
  return (
    <>
      <Button danger type="primary" onClick={() => setOpen(true)}>
        {t('Geri çağırma başlat')}
      </Button>
      <FormModal<{ reason: string }>
        title={t('{lot} için geri çağırma', { lot: trace.source.lot_no })}
        open={open}
        onClose={() => setOpen(false)}
        onSubmit={(values) => start.mutateAsync(values)}
        okText={t('Başlat ve satışa kapat')}
      >
        <Typography.Paragraph>
          {t('{lot} ve ondan yapılan {n} lot tek işlemde satışa kapatılır: mağazada ve araçta satılamaz, aktarılamaz, üretimde kullanılamaz.', {
            lot: trace.source.lot_no,
            n: trace.lots.length - 1,
          })}
        </Typography.Paragraph>
        <Form.Item name="reason" label={t('Neden')} rules={[{ required: true, message: t('Nedeni yazın.') }]}>
          <Input.TextArea rows={3} maxLength={500} placeholder={t('Tedarikçi laboratuvar sonucu: uygunsuz')} />
        </Form.Item>
      </FormModal>
    </>
  )
}

function ForwardDetails({ trace }: { trace: Trace }) {
  return (
    <>
      <Card size="small" title={t('Elimizdeki stok (ana depo, araçlar, fasoncu)')} style={{ marginBottom: 16 }}>
        <Table
          rowKey={(row) => `${row.lot_no}-${row.warehouse_code}`}
          size="small"
          pagination={false}
          dataSource={trace.stock}
          locale={{ emptyText: t('Bu zincirden bizde stok kalmadı.') }}
          columns={[
            { title: t('Lot'), dataIndex: 'lot_no', render: (lotNo: string) => <Link to={`/lotlar/${lotNo}`}>{lotNo}</Link> },
            { title: t('Ürün'), dataIndex: 'product_name' },
            { title: t('Depo'), dataIndex: 'warehouse_name' },
            { title: t('Depo türü'), dataIndex: 'warehouse_kind', render: (k: keyof typeof WAREHOUSE_KIND) => WAREHOUSE_KIND[k] },
            { title: t('Miktar'), dataIndex: 'qty', align: 'right', render: (v: string, r) => formatQty(v, r.base_unit) },
          ]}
        />
      </Card>
      <Card size="small" title={t('Alıcılar (satış kayıtlarından)')}>
        <Table<Recipient>
          rowKey={(r) => `${r.customer_id}-${r.lot_no}`}
          size="small"
          pagination={false}
          scroll={{ x: 'max-content' }}
          dataSource={trace.recipients}
          columns={RECIPIENT_COLUMNS}
          locale={{ emptyText: t('Bu zincirden henüz satış yapılmadı.') }}
        />
      </Card>
    </>
  )
}

function BackwardDetails({ trace }: { trace: Trace }) {
  return (
    <Row gutter={16}>
      <Col xs={24} xl={14}>
        <Card size="small" title={t('Hammadde lotları ve tedarikçiler')} style={{ marginBottom: 16 }}>
          <Table
            rowKey="lot_no"
            size="small"
            pagination={false}
            scroll={{ x: 'max-content' }}
            dataSource={trace.suppliers}
            locale={{ emptyText: t('Alışla gelen kaynak lot yok.') }}
            columns={[
              { title: t('Lot'), dataIndex: 'lot_no', render: (lotNo: string) => <Link to={`/lotlar/${lotNo}`}>{lotNo}</Link> },
              { title: t('Tedarikçi'), dataIndex: 'supplier' },
              { title: t('İletişim'), key: 'contact', render: (_, r) => <ContactInfo contact={r.contact} /> },
              { title: t('Alış belgesi'), dataIndex: 'purchase_doc_no' },
              { title: t('Tarih'), dataIndex: 'purchase_date', render: formatDate },
              { title: t('Miktar'), dataIndex: 'qty', align: 'right', render: (v: string) => formatQty(v) },
            ]}
          />
        </Card>
      </Col>
      <Col xs={24} xl={10}>
        <Card size="small" title={t('Üretim emirleri ve parçalamalar')} style={{ marginBottom: 16 }}>
          <Table
            rowKey={(row) => `${row.process}-${row.doc_no}`}
            size="small"
            pagination={false}
            dataSource={trace.processes}
            locale={{ emptyText: t('Lot alışla geldi; işlem yok.') }}
            columns={[
              { title: t('Süreç'), dataIndex: 'process', render: (p: keyof typeof LINK_PROCESS) => LINK_PROCESS[p] },
              { title: t('Belge'), dataIndex: 'doc_no' },
              { title: t('Girdi lotları'), dataIndex: 'input_lots', render: (lots: string[]) => lots.join(', ') },
              { title: t('Çıktı lotları'), dataIndex: 'output_lots', render: (lots: string[]) => lots.join(', ') },
            ]}
          />
        </Card>
      </Col>
    </Row>
  )
}

function TraceResult({ lotNo, direction }: { lotNo: string; direction: Direction }) {
  const trace = useQuery({
    queryKey: ['trace', direction, lotNo],
    queryFn: () => api<Trace>(`/trace/${direction}/${encodeURIComponent(lotNo)}`),
  })
  if (trace.isError) return <QueryError error={trace.error} onRetry={() => trace.refetch()} />
  if (trace.isPending) return <Spin />
  const data = trace.data
  const forward = direction === 'forward'
  return (
    <>
      <Card size="small" style={{ marginBottom: 16 }}>
        <Space wrap align="center" style={{ justifyContent: 'space-between', width: '100%' }}>
          <Space wrap>
            <Typography.Text strong style={{ fontSize: 16 }}>
              {data.source.lot_no}
            </Typography.Text>
            <span>{data.source.product_name}</span>
            <LotStatusTag status={data.source.status} />
            {data.source.supplier_name && <span>{t('Tedarikçi: {name}', { name: data.source.supplier_name })}</span>}
          </Space>
          {forward && <RecallButton trace={data} />}
        </Space>
      </Card>

      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        {forward ? (
          <>
            <Col xs={12} lg={6}>
              <Stat label={t('Etkilenen lot')} value={data.lots.length} hint={t('Kaynak + türevler')} />
            </Col>
            <Col xs={12} lg={6}>
              <Stat label={t('Bizdeki stok')} value={totalsByUnit(data.stock)} tone="warning" />
            </Col>
            <Col xs={12} lg={6}>
              <Stat label={t('Alıcı')} value={new Set(data.recipients.map((r) => r.customer_id)).size} tone="success" />
            </Col>
            <Col xs={12} lg={6}>
              <Stat label={t('Müşterilerde')} value={totalsByUnit(data.recipients)} tone="danger" />
            </Col>
          </>
        ) : (
          <>
            <Col xs={12} lg={8}>
              <Stat label={t('Kaynak lot')} value={data.lots.length - 1} />
            </Col>
            <Col xs={12} lg={8}>
              <Stat label={t('Tedarikçi')} value={new Set(data.suppliers.map((s) => s.supplier)).size} tone="success" />
            </Col>
            <Col xs={24} lg={8}>
              <Stat label={t('Üretim / parçalama')} value={data.processes.length} tone="warning" />
            </Col>
          </>
        )}
      </Row>

      <Card size="small" title={t('Lot zinciri')} style={{ marginBottom: 16 }}>
        <TraceFlow lots={data.lots} links={data.links} recipients={data.recipients} direction={direction} />
        <Typography.Text type="secondary">
          {t('Şema yalnız kayıtlardan çizilir (lot bağları, satış satırları); tahmin kullanılmaz. Bir bloğa tıklayınca lot ayrıntısı açılır.')}
        </Typography.Text>
      </Card>

      {forward ? <ForwardDetails trace={data} /> : <BackwardDetails trace={data} />}
    </>
  )
}

export default function TracePage({ lotNo, direction = 'forward' }: { lotNo?: string; direction?: Direction }) {
  const [text, setText] = useState(lotNo ?? '')
  const go = (value: string, dir: Direction = direction) => value.trim() && navigate(tracePath(value.trim().toUpperCase(), dir))

  return (
    <Page
      title={t('Lot izleme')}
      description={t('Bir lot numarası yazın: ileri izlemede o maldan ne yapıldığını ve hangi müşterilere gittiğini, geri izlemede hangi hammaddeden ve tedarikçiden geldiğini görürsünüz.')}
    >
      <Card size="small" style={{ marginBottom: 16 }}>
        <Space wrap>
          <LotPicker value={text} onChange={setText} onPick={(v) => go(v)} />
          <Segmented<Direction>
            value={direction}
            onChange={(dir) => (lotNo ? go(lotNo, dir) : undefined)}
            options={[
              { value: 'forward', label: t('İleri izle'), title: t('Nereye gitti? Türev lotlar ve alıcılar') },
              { value: 'backward', label: t('Geri izle'), title: t('Neyden yapıldı? Kaynak lotlar ve tedarikçiler') },
            ]}
          />
          <Button type="primary" onClick={() => go(text)}>
            {t('İzle')}
          </Button>
        </Space>
      </Card>
      {lotNo ? (
        <TraceResult key={`${direction}-${lotNo}`} lotNo={lotNo} direction={direction} />
      ) : (
        <Card size="small">
          <Empty description={t('Bir lot numarası yazın ya da örnek senaryoyla başlayın.')}>
            <Space wrap>
              <Button onClick={() => go('ET-2026-001', 'forward')}>ET-2026-001 · {t('İleri izle')}</Button>
              <Button onClick={() => go('SUC-2026-045', 'backward')}>SUC-2026-045 · {t('Geri izle')}</Button>
            </Space>
          </Empty>
        </Card>
      )}
    </Page>
  )
}
