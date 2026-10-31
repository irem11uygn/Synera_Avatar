// Lot ayrıntısı (FR-112, FR-302): köken, depo bakiyeleri, lot ağı (kaynak ve çıktı lotları) ve
// bütün hareketler — kim, ne zaman, hangi belgeyle, ne kadar, hangi tutar. Hareketlerin toplamı
// lotun kalan miktar ve değerine eşit olmalıdır (NFR-004); ekranda bu denetim de gösterilir.
// Kalite blokesi (karantina): geri çağırmadan bağımsız; lotu satışa ve kullanıma kapatır, nedeni ve
// geçmişi burada görünür (yalnız yönetici ve kalite koyar/kaldırır).

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  Alert,
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
import type { BaseUnit, LotDetail, Movement, MovementType, QualityHold } from '../api/types'
import { useSession } from '../auth/context'
import { FormModal } from '../components/FormModal'
import { Link } from '../components/Link'
import { Page } from '../components/Page'
import { QueryError } from '../components/QueryError'
import { LotStatusTag } from '../components/StatusTags'
import { compare, sum } from '../lib/decimal'
import { formatDate, formatDateTime, formatMoney, formatQty, formatUnitCost } from '../lib/format'
import { LINK_PROCESS, LOT_ORIGIN, MOVEMENT_TYPE } from '../lib/labels'
import { tracePath } from '../lib/paths'
import { can } from '../lib/roles'
import { navigate } from '../lib/router'
import { decimalRule, toApiDecimal } from '../lib/rules'
import { t } from '../lib/i18n'

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
    { title: t('Zaman'), dataIndex: 'posted_at', render: formatDateTime },
    {
      title: t('Hareket'),
      dataIndex: 'type',
      render: (type: MovementType, row) => (
        <>
          {MOVEMENT_TYPE[type]}
          {row.reversal_of_id && <Tag style={{ marginInlineStart: 8 }}>{t('#{id} kaydının tersi', { id: row.reversal_of_id })}</Tag>}
        </>
      ),
    },
    { title: t('Depo'), dataIndex: 'warehouse_code' },
    { title: t('Miktar'), dataIndex: 'qty', align: 'right', render: (qty: string) => formatQty(qty, unit) },
    { title: t('Değer'), dataIndex: 'value', align: 'right', render: formatMoney },
    { title: t('Belge'), key: 'doc', render: (_, row) => documentCell(row) },
    { title: t('Kullanıcı'), dataIndex: 'user_name', render: (v: string | null) => v ?? t('Örnek kayıt') },
    { title: t('Not'), dataIndex: 'note', render: (v: string | null) => v ?? '—' },
    {
      title: t('Düzeltme'),
      key: 'reverse',
      render: (_, row) =>
        reversed.has(row.id) ? (
          <Tag>{t('Geri alındı')}</Tag>
        ) : REVERSIBLE.has(row.type) && !row.reversal_of_id ? (
          <Button size="small" onClick={() => onReverse(row)}>
            {t('Geri al')}
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
      okText={t('Fireyi kaydet')}
    >
      <Form.Item name="warehouse_id" label={t('Depo')} rules={[{ required: true, message: t('Depoyu seçin.') }]}>
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
        label={t('Miktar')}
        rules={[decimalRule(t('Miktar'), { maxFraction: 3, integer: lot.base_unit === 'ADET' })]}
      >
        <Input inputMode="decimal" autoComplete="off" />
      </Form.Item>
      <Form.Item name="reason" label={t('Gerekçe')} rules={[{ required: true, message: t('Gerekçeyi yazın.') }]}>
        <Input maxLength={255} placeholder={t('Soğuk zincir kırıldı')} />
      </Form.Item>
      <Typography.Text type="secondary">
        {t('Lot değeri ortalama birim maliyetle düşer; satışa kapalı lotta da yapılabilir.')}
      </Typography.Text>
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
      title={`Geri al: ${MOVEMENT_TYPE[movement.type]} (${lotNo})`}
      open
      onClose={onClose}
      onSubmit={(values) => mutation.mutateAsync(values)}
      okText={t('Geri al')}
    >
      <Typography.Paragraph>
        {t('Defterde hiçbir hareket silinmez ya da değiştirilmez. Bu hareketin tam tersi yeni bir hareket olarak yazılır')}
        {movement.type.startsWith('TRANSFER') ? t(' (transferin iki hareketi birlikte)') : ''}.
      </Typography.Paragraph>
      <Form.Item name="reason" label={t('Gerekçe')} rules={[{ required: true, message: t('Gerekçeyi yazın.') }]}>
        <Input maxLength={255} placeholder={t('Yanlış lot seçilmiş')} />
      </Form.Item>
    </FormModal>
  )
}

/** Kalite blokesi koy (reason) ya da kaldır (note); yanıt lotun güncel hâlidir. */
function HoldModal({ lot, mode, onClose }: { lot: LotDetail; mode: 'hold' | 'release' | null; onClose: () => void }) {
  const queryClient = useQueryClient()
  const mutation = useMutation({
    mutationFn: (values: { reason?: string; note?: string }) =>
      api<LotDetail>(`/lots/${encodeURIComponent(lot.lot_no)}/${mode}`, { method: 'POST', body: values }),
    onSuccess: (data) => {
      queryClient.setQueryData(['lot', lot.lot_no], data)
      return refreshBusinessData(queryClient)
    },
  })
  if (!mode) return null
  const hold = mode === 'hold'
  return (
    <FormModal<{ reason?: string; note?: string }>
      title={hold ? t('{lot}: kalite blokesi koy', { lot: lot.lot_no }) : t('{lot}: kalite blokesini kaldır', { lot: lot.lot_no })}
      open
      onClose={onClose}
      onSubmit={(values) => mutation.mutateAsync(values)}
      okText={hold ? t('Blokeye al') : t('Blokeyi kaldır')}
    >
      <Typography.Paragraph>
        {hold
          ? t('Lot soruşturma bitene kadar satışa ve kullanıma kapanır: mağazada ve araçta satılamaz, aktarılamaz, üretimde kullanılamaz. Bu lottan yapılmış lotlar etkilenmez; şüphe doğrulanırsa geri çağırma başlatın.')
          : t('Lot açık bir geri çağırmada değilse yeniden satışa açılır. Kayıt silinmez; kim, ne zaman, hangi notla kaldırdı saklanır.')}
      </Typography.Paragraph>
      {hold ? (
        <Form.Item name="reason" label={t('Neden')} rules={[{ required: true, whitespace: true, message: t('Nedeni yazın.') }]}>
          <Input.TextArea rows={2} maxLength={500} placeholder={t('Ambalajda şişme; laboratuvar sonucu bekleniyor')} />
        </Form.Item>
      ) : (
        <Form.Item name="note" label={t('Not')}>
          <Input.TextArea rows={2} maxLength={500} placeholder={t('Laboratuvar sonucu temiz')} />
        </Form.Item>
      )}
    </FormModal>
  )
}

const HOLD_COLUMNS: TableColumnsType<QualityHold> = [
  { title: t('Konuldu'), dataIndex: 'placed_at', render: formatDateTime },
  { title: t('Neden'), dataIndex: 'reason' },
  { title: t('Koyan'), dataIndex: 'placed_by_name', render: (v: string | null) => v ?? '—' },
  {
    title: t('Kaldırıldı'),
    dataIndex: 'released_at',
    render: (v: string | null) => (v ? formatDateTime(v) : <Tag color="error">{t('Açık')}</Tag>),
  },
  { title: t('Kaldıran'), dataIndex: 'released_by_name', render: (v: string | null) => v ?? '—' },
  { title: t('Not'), dataIndex: 'release_note', render: (v: string | null) => v ?? '—' },
]

const LINK_COLUMNS: TableColumnsType<LinkRow> = [
  { title: t('Lot'), dataIndex: 'lot_no', render: (lotNo: string) => <Link to={`/lotlar/${lotNo}`}>{lotNo}</Link> },
  { title: t('Miktar'), dataIndex: 'qty', align: 'right', render: (qty: string) => formatQty(qty) },
  {
    title: t('Süreç'),
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
  const { user } = useSession()
  const [wasting, setWasting] = useState(false)
  const [reversing, setReversing] = useState<Movement | null>(null)
  const [holdMode, setHoldMode] = useState<'hold' | 'release' | null>(null)

  if (lot.isError) {
    return (
      <Page title={`Lot ${lotNo}`}>
        <QueryError error={lot.error} onRetry={() => lot.refetch()} />
      </Page>
    )
  }
  if (lot.isPending) return <Spin />

  const data = lot.data
  const activeHold = data.holds.find((h) => !h.released_at)
  const canHold = can(user.role, 'quality')
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
      back={{ to: '/lotlar', label: t('Lotlar') }}
      extra={
        <>
          <Button onClick={() => navigate(tracePath(data.lot_no))}>{t('İleri izle')}</Button>
          <Button onClick={() => navigate(tracePath(data.lot_no, 'backward'))}>{t('Geri izle')}</Button>
          {data.balances.length > 0 && <Button onClick={() => setWasting(true)}>{t('Fire / imha')}</Button>}
          {canHold &&
            (activeHold ? (
              <Button onClick={() => setHoldMode('release')}>{t('Blokeyi kaldır')}</Button>
            ) : (
              <Button danger onClick={() => setHoldMode('hold')}>
                {t('Kalite blokesi koy')}
              </Button>
            ))}
        </>
      }
    >
      {data.status === 'BLOKE' && (
        <Alert
          type="error"
          showIcon
          style={{ marginBottom: 16 }}
          title={t('Satışa ve kullanıma kapalı')}
          description={
            <>
              {activeHold && (
                <div>
                  {t('Kalite blokesi: {reason} — {who}, {at}', {
                    reason: activeHold.reason,
                    who: activeHold.placed_by_name ?? '—',
                    at: formatDateTime(activeHold.placed_at),
                  })}
                </div>
              )}
              {data.open_recalls.length > 0 && (
                <div>
                  {t('Açık geri çağırma: {list}', { list: data.open_recalls.join(', ') })}{' '}
                  <Link to="/geri-cagirma">{t('Geri çağırmalar')}</Link>
                </div>
              )}
            </>
          }
        />
      )}
      <Card size="small" style={{ marginBottom: 16 }}>
        <Descriptions
          size="small"
          column={{ xs: 1, sm: 2, lg: 3 }}
          items={[
            { key: 'product', label: t('Ürün'), children: `${data.product_code} · ${data.product_name}` },
            { key: 'origin', label: t('Köken'), children: LOT_ORIGIN[data.origin] },
            { key: 'status', label: t('Durum'), children: <LotStatusTag status={data.status} /> },
            { key: 'supplier', label: t('Tedarikçi'), children: data.supplier_name ?? '—' },
            { key: 'produced', label: t('Üretim / giriş'), children: formatDate(data.produced_at) },
            { key: 'expiry', label: t('Son kullanma'), children: formatDate(data.expiry_date) },
            {
              key: 'initial',
              label: t('Başlangıç'),
              children: `${formatQty(data.initial_qty, data.base_unit)} · ${formatMoney(data.initial_value)}`,
            },
            {
              key: 'remaining',
              label: t('Kalan'),
              children: `${formatQty(data.remaining_qty, data.base_unit)} · ${formatMoney(data.remaining_value)}`,
            },
            { key: 'unit_cost', label: t('Birim maliyet'), children: formatUnitCost(data.unit_cost) },
          ]}
        />
      </Card>

      <Row gutter={16}>
        <Col xs={24} lg={8}>
          <Card size="small" title={t('Depo bakiyeleri')} style={{ marginBottom: 16 }}>
            {data.balances.length === 0 ? (
              <Empty description={t('Hiçbir depoda kalmadı')} />
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
          <Card size="small" title={t('Kaynak lotlar (geri izleme)')} style={{ marginBottom: 16 }}>
            <Table<LinkRow>
              rowKey={(row) => `${row.lot_no}-${row.process_id}`}
              size="small"
              columns={LINK_COLUMNS}
              dataSource={data.parents}
              pagination={false}
              locale={{ emptyText: t('Kaynak lot yok (alışla geldi).') }}
            />
          </Card>
        </Col>
        <Col xs={24} lg={8}>
          <Card size="small" title={t('Bu lottan üretilenler (ileri izleme)')} style={{ marginBottom: 16 }}>
            <Table<LinkRow>
              rowKey={(row) => `${row.lot_no}-${row.process_id}`}
              size="small"
              columns={LINK_COLUMNS}
              dataSource={data.children}
              pagination={false}
              locale={{ emptyText: t('Bu lottan henüz üretim yapılmadı.') }}
            />
          </Card>
        </Col>
      </Row>

      <Card size="small" title={t('Hareket geçmişi')}>
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
                  <Typography.Text strong>{t('Toplam')}</Typography.Text>
                </Table.Summary.Cell>
                <Table.Summary.Cell index={3} align="right">
                  <Typography.Text strong>{formatQty(totalQty, data.base_unit)}</Typography.Text>
                </Table.Summary.Cell>
                <Table.Summary.Cell index={4} align="right">
                  <Typography.Text strong>{formatMoney(totalValue)}</Typography.Text>
                </Table.Summary.Cell>
                <Table.Summary.Cell index={5} colSpan={4}>
                  {consistent ? (
                    <Tag color="green">{t('Kalan miktar ve değerle tutarlı')}</Tag>
                  ) : (
                    <Tag color="red">{t('Kalanla tutarsız — bütünlük raporuna bakın')}</Tag>
                  )}
                </Table.Summary.Cell>
              </Table.Summary.Row>
            )
          }
        />
      </Card>
      <WasteModal lot={data} open={wasting} onClose={() => setWasting(false)} />
      {data.holds.length > 0 && (
        <Card size="small" title={t('Kalite blokeleri')} style={{ marginBottom: 16 }}>
          <Table<QualityHold> rowKey="id" size="small" pagination={false} scroll={{ x: 'max-content' }} dataSource={data.holds} columns={HOLD_COLUMNS} />
        </Card>
      )}
      <HoldModal lot={data} mode={holdMode} onClose={() => setHoldMode(null)} />
      <ReverseModal movement={reversing} lotNo={data.lot_no} onClose={() => setReversing(null)} />
    </Page>
  )
}
