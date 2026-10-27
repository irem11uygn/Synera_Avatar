// Lot ayrıntısı (FR-112, FR-302): köken, depo bakiyeleri, lot ağı (kaynak ve çıktı lotları) ve
// bütün hareketler — kim, ne zaman, hangi belgeyle, ne kadar, hangi tutar. Hareketlerin toplamı
// lotun kalan miktar ve değerine eşit olmalıdır (NFR-004); ekranda bu denetim de gösterilir.

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  Button,
  Card,
  Col,
  Descriptions,
  Empty,
  Form,
  Input,
  Row,
  Select,
  Spin,
  Table,
  Tag,
  Typography,
  type TableColumnsType,
} from 'antd'
import { useState } from 'react'
import { api } from '../api/client'
import { refreshBusinessData, useWarehouses } from '../api/queries'
import type { BaseUnit, LotDetail, Movement, MovementType } from '../api/types'
import { FormModal } from '../components/FormModal'
import { Link } from '../components/Link'
import { Page } from '../components/Page'
import { QueryError } from '../components/QueryError'
import { LotStatusTag } from '../components/StatusTags'
import { compare, sum } from '../lib/decimal'
import { formatDate, formatDateTime, formatMoney, formatQty, formatUnitCost } from '../lib/format'
import { LINK_PROCESS, LOT_ORIGIN, MOVEMENT_TYPE } from '../lib/labels'
import { tracePath } from '../lib/paths'
import { navigate } from '../lib/router'
import { decimalRule, toApiDecimal } from '../lib/rules'

type LinkRow = LotDetail['parents'][number]

// Belgesi ekranı olan hareketler belgeye bağlanır.
const DOC_PAGE: Partial<Record<Movement['doc_type'], string>> = { URETIM: '/uretim', PARCALAMA: '/parcalama' }

function documentCell(movement: Movement) {
  const number = movement.doc_no ?? `#${movement.doc_id}`
  // Yeniden işleme de üretim belgesidir (URETIM) ama kendi ekranı vardır (YIS-… numaralı).
  const page = number.startsWith('YIS-') ? '/yeniden-isleme' : DOC_PAGE[movement.doc_type]
  if (page === '/yeniden-isleme') return <Link to={page}>{number}</Link>
  return page ? <Link to={`${page}/${movement.doc_id}`}>{number}</Link> : number
}

// Ters kayıtla düzeltilebilen hareketler (sunucuda aynı kural): fire, iade, elle transfer.
const REVERSIBLE = new Set<MovementType>(['FIRE', 'IADE_GIRIS', 'TRANSFER_CIKIS', 'TRANSFER_GIRIS'])

function movementColumns(
  unit: BaseUnit,
  reversed: Set<number>,
  onReverse: (movement: Movement) => void,
): TableColumnsType<Movement> {
  return [
    { title: 'Zaman', dataIndex: 'posted_at', render: formatDateTime },
    {
      title: 'Hareket',
      dataIndex: 'type',
      render: (type: MovementType, row) => (
        <>
          {MOVEMENT_TYPE[type]}
          {row.reversal_of_id && <Tag style={{ marginInlineStart: 8 }}>#{row.reversal_of_id} kaydının tersi</Tag>}
        </>
      ),
    },
    { title: 'Depo', dataIndex: 'warehouse_code' },
    { title: 'Miktar', dataIndex: 'qty', align: 'right', render: (qty: string) => formatQty(qty, unit) },
    { title: 'Değer', dataIndex: 'value', align: 'right', render: formatMoney },
    { title: 'Belge', key: 'doc', render: (_, row) => documentCell(row) },
    { title: 'Kullanıcı', dataIndex: 'user_name', render: (v: string | null) => v ?? 'Örnek kayıt' },
    { title: 'Not', dataIndex: 'note', render: (v: string | null) => v ?? '—' },
    {
      title: 'Düzeltme',
      key: 'reverse',
      render: (_, row) =>
        reversed.has(row.id) ? (
          <Tag>Ters kayıtla düzeltildi</Tag>
        ) : REVERSIBLE.has(row.type) && !row.reversal_of_id ? (
          <Button size="small" onClick={() => onReverse(row)}>
            Ters kayıt
          </Button>
        ) : null,
    },
  ]
}

type WasteValues = { warehouse_id: number; qty: string; reason: string }

function WasteModal({ lot, open, onClose }: { lot: LotDetail; open: boolean; onClose: () => void }) {
  const queryClient = useQueryClient()
  const warehouses = useWarehouses()
  const codes = new Set(lot.balances.map((b) => b.warehouse_code))
  const mutation = useMutation({
    mutationFn: (values: WasteValues) =>
      api('/adjustments', {
        method: 'POST',
        body: { ...values, lot_no: lot.lot_no, qty: toApiDecimal(values.qty, 3) },
      }),
    onSuccess: () => refreshBusinessData(queryClient),
  })
  return (
    <FormModal<WasteValues>
      title={`${lot.lot_no} — fire / imha`}
      open={open}
      onClose={onClose}
      onSubmit={(values) => mutation.mutateAsync(values)}
      okText="Fireyi kaydet"
    >
      <Form.Item name="warehouse_id" label="Depo" rules={[{ required: true, message: 'Depoyu seçin.' }]}>
        <Select
          options={(warehouses.data ?? [])
            .filter((w) => codes.has(w.code))
            .map((w) => ({
              value: w.id,
              label: `${w.name} — ${formatQty(lot.balances.find((b) => b.warehouse_code === w.code)?.qty, lot.base_unit)}`,
            }))}
        />
      </Form.Item>
      <Form.Item
        name="qty"
        label="Miktar"
        rules={[decimalRule('Miktar', { maxFraction: 3, integer: lot.base_unit === 'ADET' })]}
      >
        <Input inputMode="decimal" autoComplete="off" />
      </Form.Item>
      <Form.Item name="reason" label="Gerekçe" rules={[{ required: true, message: 'Gerekçeyi yazın.' }]}>
        <Input maxLength={255} placeholder="Soğuk zincir kırıldı" />
      </Form.Item>
      <Typography.Text type="secondary">Lot değeri ortalama birim maliyetle düşer; bloke lotta da yapılabilir.</Typography.Text>
    </FormModal>
  )
}

function ReverseModal({ movement, lotNo, onClose }: { movement: Movement | null; lotNo: string; onClose: () => void }) {
  const queryClient = useQueryClient()
  const mutation = useMutation({
    mutationFn: (values: { reason: string }) =>
      api(`/movements/${movement!.id}/reverse`, { method: 'POST', body: values }),
    onSuccess: () => refreshBusinessData(queryClient),
  })
  if (!movement) return null
  return (
    <FormModal<{ reason: string }>
      title={`Ters kayıt: ${MOVEMENT_TYPE[movement.type]} (${lotNo})`}
      open
      onClose={onClose}
      onSubmit={(values) => mutation.mutateAsync(values)}
      okText="Ters kaydı yaz"
    >
      <Typography.Paragraph>
        Defterde hiçbir hareket silinmez ya da değiştirilmez. Bu hareketin tam tersi yeni bir hareket olarak yazılır
        {movement.type.startsWith('TRANSFER') ? ' (transferin iki hareketi birlikte)' : ''}.
      </Typography.Paragraph>
      <Form.Item name="reason" label="Gerekçe" rules={[{ required: true, message: 'Gerekçeyi yazın.' }]}>
        <Input maxLength={255} placeholder="Yanlış lot seçilmiş" />
      </Form.Item>
    </FormModal>
  )
}

const LINK_COLUMNS: TableColumnsType<LinkRow> = [
  { title: 'Lot', dataIndex: 'lot_no', render: (lotNo: string) => <Link to={`/lotlar/${lotNo}`}>{lotNo}</Link> },
  { title: 'Miktar', dataIndex: 'qty', align: 'right', render: (qty: string) => formatQty(qty) },
  {
    title: 'Süreç',
    dataIndex: 'process',
    render: (process: LinkRow['process'], row) => {
      const page = process === 'URETIM' ? '/uretim' : process === 'PARCALAMA' ? '/parcalama' : null
      return page ? <Link to={`${page}/${row.process_id}`}>{LINK_PROCESS[process]}</Link> : LINK_PROCESS[process]
    },
  },
]

export default function LotDetailPage({ lotNo }: { lotNo: string }) {
  const lot = useQuery({
    queryKey: ['lot', lotNo],
    queryFn: () => api<LotDetail>(`/lots/${encodeURIComponent(lotNo)}`),
  })
  const movements = useQuery({
    queryKey: ['movements', lotNo],
    queryFn: () => api<Movement[]>(`/lots/${encodeURIComponent(lotNo)}/movements`),
  })
  const [wasting, setWasting] = useState(false)
  const [reversing, setReversing] = useState<Movement | null>(null)

  if (lot.isError) {
    return (
      <Page title={`Lot ${lotNo}`}>
        <QueryError error={lot.error} onRetry={() => lot.refetch()} />
      </Page>
    )
  }
  if (lot.isPending) return <Spin />

  const data = lot.data
  const totalQty = movements.data ? sum(movements.data.map((m) => m.qty), 3) : null
  const totalValue = movements.data ? sum(movements.data.map((m) => m.value), 2) : null
  const reversed = new Set((movements.data ?? []).flatMap((m) => (m.reversal_of_id ? [m.reversal_of_id] : [])))
  const consistent =
    totalQty !== null &&
    totalValue !== null &&
    compare(totalQty, data.remaining_qty) === 0 &&
    compare(totalValue, data.remaining_value) === 0

  return (
    <Page
      title={`Lot ${data.lot_no}`}
      extra={
        <>
          <Button onClick={() => navigate(tracePath(data.lot_no))}>İleri izle</Button>
          <Button onClick={() => navigate(tracePath(data.lot_no, 'backward'))}>Geri izle</Button>
          {data.balances.length > 0 && <Button onClick={() => setWasting(true)}>Fire / imha</Button>}
        </>
      }
    >
      <Card size="small" style={{ marginBottom: 16 }}>
        <Descriptions
          size="small"
          column={{ xs: 1, sm: 2, lg: 3 }}
          items={[
            { key: 'product', label: 'Ürün', children: `${data.product_code} · ${data.product_name}` },
            { key: 'origin', label: 'Köken', children: LOT_ORIGIN[data.origin] },
            { key: 'status', label: 'Durum', children: <LotStatusTag status={data.status} /> },
            { key: 'supplier', label: 'Tedarikçi', children: data.supplier_name ?? '—' },
            { key: 'produced', label: 'Üretim / giriş', children: formatDate(data.produced_at) },
            { key: 'expiry', label: 'Son kullanma', children: formatDate(data.expiry_date) },
            {
              key: 'initial',
              label: 'Başlangıç',
              children: `${formatQty(data.initial_qty, data.base_unit)} · ${formatMoney(data.initial_value)}`,
            },
            {
              key: 'remaining',
              label: 'Kalan',
              children: `${formatQty(data.remaining_qty, data.base_unit)} · ${formatMoney(data.remaining_value)}`,
            },
            { key: 'unit_cost', label: 'Birim maliyet', children: formatUnitCost(data.unit_cost) },
          ]}
        />
      </Card>

      <Row gutter={16}>
        <Col xs={24} lg={8}>
          <Card size="small" title="Depo bakiyeleri" style={{ marginBottom: 16 }}>
            {data.balances.length === 0 ? (
              <Empty description="Hiçbir depoda kalmadı" />
            ) : (
              <Descriptions
                size="small"
                column={1}
                items={data.balances.map((b) => ({
                  key: b.warehouse_code,
                  label: b.warehouse_name,
                  children: formatQty(b.qty, data.base_unit),
                }))}
              />
            )}
          </Card>
        </Col>
        <Col xs={24} lg={8}>
          <Card size="small" title="Kaynak lotlar (geri izleme)" style={{ marginBottom: 16 }}>
            <Table<LinkRow>
              rowKey={(row) => `${row.lot_no}-${row.process_id}`}
              size="small"
              columns={LINK_COLUMNS}
              dataSource={data.parents}
              pagination={false}
              locale={{ emptyText: 'Kaynak lot yok (alışla geldi).' }}
            />
          </Card>
        </Col>
        <Col xs={24} lg={8}>
          <Card size="small" title="Bu lottan üretilenler (ileri izleme)" style={{ marginBottom: 16 }}>
            <Table<LinkRow>
              rowKey={(row) => `${row.lot_no}-${row.process_id}`}
              size="small"
              columns={LINK_COLUMNS}
              dataSource={data.children}
              pagination={false}
              locale={{ emptyText: 'Bu lottan henüz üretim yapılmadı.' }}
            />
          </Card>
        </Col>
      </Row>

      <Card size="small" title="Hareket geçmişi">
        {movements.isError && <QueryError error={movements.error} onRetry={() => movements.refetch()} />}
        <Table<Movement>
          rowKey="id"
          size="small"
          loading={movements.isPending}
          columns={movementColumns(data.base_unit, reversed, setReversing)}
          dataSource={movements.data}
          pagination={false}
          scroll={{ x: 'max-content' }}
          summary={() =>
            totalQty === null ? null : (
              <Table.Summary.Row>
                <Table.Summary.Cell index={0} colSpan={3}>
                  <Typography.Text strong>Toplam</Typography.Text>
                </Table.Summary.Cell>
                <Table.Summary.Cell index={3} align="right">
                  <Typography.Text strong>{formatQty(totalQty, data.base_unit)}</Typography.Text>
                </Table.Summary.Cell>
                <Table.Summary.Cell index={4} align="right">
                  <Typography.Text strong>{formatMoney(totalValue)}</Typography.Text>
                </Table.Summary.Cell>
                <Table.Summary.Cell index={5} colSpan={4}>
                  {consistent ? (
                    <Tag color="green">Kalan miktar ve değerle tutarlı</Tag>
                  ) : (
                    <Tag color="red">Kalanla tutarsız — bütünlük raporuna bakın</Tag>
                  )}
                </Table.Summary.Cell>
              </Table.Summary.Row>
            )
          }
        />
      </Card>
      <WasteModal lot={data} open={wasting} onClose={() => setWasting(false)} />
      <ReverseModal movement={reversing} lotNo={data.lot_no} onClose={() => setReversing(null)} />
    </Page>
  )
}
