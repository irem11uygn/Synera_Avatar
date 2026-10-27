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
  if (trace.source.status === 'BLOKE') return <Tag color="red">Bu lot zaten satışa kapalı</Tag>
  return (
    <>
      <Button danger type="primary" onClick={() => setOpen(true)}>
        Geri çağırma başlat
      </Button>
      <FormModal<{ reason: string }>
        title={`${trace.source.lot_no} için geri çağırma`}
        open={open}
        onClose={() => setOpen(false)}
        onSubmit={(values) => start.mutateAsync(values)}
        okText="Başlat ve satışa kapat"
      >
        <Typography.Paragraph>
          {trace.source.lot_no} ve ondan türeyen <strong>{trace.lots.length - 1}</strong> lot tek işlemde
          satışa kapatılır: mağazada ve araçta satılamaz, aktarılamaz, üretimde kullanılamaz.
        </Typography.Paragraph>
        <Form.Item name="reason" label="Neden" rules={[{ required: true, message: 'Nedeni yazın.' }]}>
          <Input.TextArea rows={3} maxLength={500} placeholder="Tedarikçi laboratuvar sonucu: uygunsuz" />
        </Form.Item>
      </FormModal>
    </>
  )
}

function ForwardDetails({ trace }: { trace: Trace }) {
  return (
    <>
      <Card size="small" title="Elimizdeki stok (ana depo, araçlar, fasoncu)" style={{ marginBottom: 16 }}>
        <Table
          rowKey={(row) => `${row.lot_no}-${row.warehouse_code}`}
          size="small"
          pagination={false}
          dataSource={trace.stock}
          locale={{ emptyText: 'Bu zincirden bizde stok kalmadı.' }}
          columns={[
            { title: 'Lot', dataIndex: 'lot_no', render: (lotNo: string) => <Link to={`/lotlar/${lotNo}`}>{lotNo}</Link> },
            { title: 'Ürün', dataIndex: 'product_name' },
            { title: 'Depo', dataIndex: 'warehouse_name' },
            { title: 'Depo türü', dataIndex: 'warehouse_kind', render: (k: keyof typeof WAREHOUSE_KIND) => WAREHOUSE_KIND[k] },
            { title: 'Miktar', dataIndex: 'qty', align: 'right', render: (v: string, r) => formatQty(v, r.base_unit) },
          ]}
        />
      </Card>
      <Card size="small" title="Alıcılar (satış kayıtlarından)">
        <Table<Recipient>
          rowKey={(r) => `${r.customer_id}-${r.lot_no}`}
          size="small"
          pagination={false}
          scroll={{ x: 'max-content' }}
          dataSource={trace.recipients}
          columns={RECIPIENT_COLUMNS}
          locale={{ emptyText: 'Bu zincirden henüz satış yapılmadı.' }}
        />
      </Card>
    </>
  )
}

function BackwardDetails({ trace }: { trace: Trace }) {
  return (
    <Row gutter={16}>
      <Col xs={24} xl={14}>
        <Card size="small" title="Hammadde lotları ve tedarikçiler" style={{ marginBottom: 16 }}>
          <Table
            rowKey="lot_no"
            size="small"
            pagination={false}
            scroll={{ x: 'max-content' }}
            dataSource={trace.suppliers}
            locale={{ emptyText: 'Alışla gelen kaynak lot yok.' }}
            columns={[
              { title: 'Lot', dataIndex: 'lot_no', render: (lotNo: string) => <Link to={`/lotlar/${lotNo}`}>{lotNo}</Link> },
              { title: 'Tedarikçi', dataIndex: 'supplier' },
              { title: 'İletişim', key: 'contact', render: (_, r) => <ContactInfo contact={r.contact} /> },
              { title: 'Alış belgesi', dataIndex: 'purchase_doc_no' },
              { title: 'Tarih', dataIndex: 'purchase_date', render: formatDate },
              { title: 'Miktar', dataIndex: 'qty', align: 'right', render: (v: string) => formatQty(v) },
            ]}
          />
        </Card>
      </Col>
      <Col xs={24} xl={10}>
        <Card size="small" title="Üretim emirleri ve parçalamalar" style={{ marginBottom: 16 }}>
          <Table
            rowKey={(row) => `${row.process}-${row.doc_no}`}
            size="small"
            pagination={false}
            dataSource={trace.processes}
            locale={{ emptyText: 'Lot alışla geldi; işlem yok.' }}
            columns={[
              { title: 'Süreç', dataIndex: 'process', render: (p: keyof typeof LINK_PROCESS) => LINK_PROCESS[p] },
              { title: 'Belge', dataIndex: 'doc_no' },
              { title: 'Girdi lotları', dataIndex: 'input_lots', render: (lots: string[]) => lots.join(', ') },
              { title: 'Çıktı lotları', dataIndex: 'output_lots', render: (lots: string[]) => lots.join(', ') },
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
            {data.source.supplier_name && <span>Tedarikçi: {data.source.supplier_name}</span>}
          </Space>
          {forward && <RecallButton trace={data} />}
        </Space>
      </Card>

      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        {forward ? (
          <>
            <Col xs={12} lg={6}>
              <Stat label="Etkilenen lot" value={data.lots.length} hint="Kaynak + türevler" />
            </Col>
            <Col xs={12} lg={6}>
              <Stat label="Bizdeki stok" value={totalsByUnit(data.stock)} tone="warning" />
            </Col>
            <Col xs={12} lg={6}>
              <Stat label="Alıcı" value={new Set(data.recipients.map((r) => r.customer_id)).size} tone="success" />
            </Col>
            <Col xs={12} lg={6}>
              <Stat label="Müşterilerde" value={totalsByUnit(data.recipients)} tone="danger" />
            </Col>
          </>
        ) : (
          <>
            <Col xs={12} lg={8}>
              <Stat label="Kaynak lot" value={data.lots.length - 1} />
            </Col>
            <Col xs={12} lg={8}>
              <Stat label="Tedarikçi" value={new Set(data.suppliers.map((s) => s.supplier)).size} tone="success" />
            </Col>
            <Col xs={24} lg={8}>
              <Stat label="Üretim / parçalama" value={data.processes.length} tone="warning" />
            </Col>
          </>
        )}
      </Row>

      <Card size="small" title="Lot zinciri" style={{ marginBottom: 16 }}>
        <TraceFlow lots={data.lots} links={data.links} recipients={data.recipients} direction={direction} />
        <Typography.Text type="secondary">
          Şema yalnız kayıtlardan çizilir (lot bağları, satış satırları); tahmin kullanılmaz. Bir bloğa tıklayınca lot
          ayrıntısı açılır.
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
      title="Lot izleme"
      description="Bir lot numarası yazın: ileri izlemede o maldan ne yapıldığını ve hangi müşterilere gittiğini, geri izlemede hangi hammaddeden ve tedarikçiden geldiğini görürsünüz."
    >
      <Card size="small" style={{ marginBottom: 16 }}>
        <Space wrap>
          <LotPicker value={text} onChange={setText} onPick={(v) => go(v)} />
          <Segmented<Direction>
            value={direction}
            onChange={(dir) => (lotNo ? go(lotNo, dir) : undefined)}
            options={[
              { value: 'forward', label: 'İleri izle', title: 'Nereye gitti? Türev lotlar ve alıcılar' },
              { value: 'backward', label: 'Geri izle', title: 'Neyden yapıldı? Kaynak lotlar ve tedarikçiler' },
            ]}
          />
          <Button type="primary" onClick={() => go(text)}>
            İzle
          </Button>
        </Space>
      </Card>
      {lotNo ? (
        <TraceResult key={`${direction}-${lotNo}`} lotNo={lotNo} direction={direction} />
      ) : (
        <Card size="small">
          <Empty description="Bir lot numarası yazın ya da şartname senaryosuyla başlayın.">
            <Space wrap>
              <Button onClick={() => go('ET-2026-001', 'forward')}>ET-2026-001 ileri izle</Button>
              <Button onClick={() => go('SUC-2026-045', 'backward')}>SUC-2026-045 geri izle</Button>
            </Space>
          </Empty>
        </Card>
      )}
    </Page>
  )
}
