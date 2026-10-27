// Parçalama ayrıntısı (FR-203…FR-208). Taslakta: fiili kg'lar girilir; her değişiklikte sunucudan
// kaydetmeden ön izleme alınır (ağırlık dengesi + maliyet dağıtımı), ekrandaki rakamlar sunucunun
// hesabıyla birebir aynıdır. Onaylıda: dağıtım dökümü ve açılan parça lotları.

import { keepPreviousData, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  Alert,
  App,
  Button,
  Card,
  Col,
  Descriptions,
  Flex,
  Input,
  Popconfirm,
  Row,
  Segmented,
  Spin,
  Statistic,
  Table,
  Tag,
  Typography,
  type TableColumnsType,
} from 'antd'
import { useMemo, useState } from 'react'
import { api, errorMessage } from '../api/client'
import { refreshBusinessData } from '../api/queries'
import type { ActualsInput, AllocationMethod, Cutting, RecipeLineType } from '../api/types'
import { Link } from '../components/Link'
import { Page } from '../components/Page'
import { QueryError } from '../components/QueryError'
import { CuttingStatusTag } from '../components/StatusTags'
import { multiply, parseUserDecimal, sum } from '../lib/decimal'
import { formatDateTime, formatDecimal, formatMoney, formatQty, formatUnitCost } from '../lib/format'
import { ALLOCATION_METHOD, options, PURCHASE_COST_KIND, RECIPE_LINE_TYPE } from '../lib/labels'
import { fromApiDecimal } from '../lib/rules'
import { useDebounced } from '../lib/useDebounced'
import { t } from '../lib/i18n'

type Line = Cutting['lines'][number]

const lineName = (line: Line) => line.product_name ?? t('Fire')

/** Standart oran yüzde olarak: "0.2700" → "%27" (ondalık hesap, kayan nokta yok). */
function percent(ratio: string): string {
  return `%${formatDecimal(multiply(ratio, '100', 2), 0, 2)}`
}

const TYPE_COLOR: Record<RecipeLineType, string> = { PARCA: 'blue', YAN_URUN: 'purple', FIRE: 'default' }

export default function CuttingDetailPage({ id }: { id: number }) {
  const cutting = useQuery({ queryKey: ['cutting', id], queryFn: () => api<Cutting>(`/cuttings/${id}`) })

  if (cutting.isError) {
    return (
      <Page title={t('Parçalama')}>
        <QueryError error={cutting.error} onRetry={() => cutting.refetch()} />
      </Page>
    )
  }
  if (cutting.isPending) return <Spin />

  const data = cutting.data
  return (
    <Page title={t('Parçalama {no}', { no: data.cutting_no })} back={{ to: '/parcalama', label: t('Parçalama') }}>
      <Card size="small" style={{ marginBottom: 16 }}>
        <Descriptions
          size="small"
          column={{ xs: 1, sm: 2, lg: 3 }}
          items={[
            { key: 'status', label: t('Durum'), children: <CuttingStatusTag status={data.status} /> },
            { key: 'recipe', label: t('Reçete'), children: `${data.recipe_code} · ${data.recipe_name}` },
            {
              key: 'lot',
              label: t('Giriş lotu'),
              children: (
                <>
                  <Link to={`/lotlar/${data.input_lot_no}`}>{data.input_lot_no}</Link> · {data.input_product_name}
                </>
              ),
            },
            { key: 'qty', label: t('Giriş ağırlığı'), children: formatQty(data.input_qty, 'KG') },
            { key: 'cost', label: t('Toplam maliyet'), children: formatMoney(data.total_cost) },
            { key: 'cut', label: t('Açılış'), children: formatDateTime(data.cut_at) },
            ...(data.approved_at ? [{ key: 'approved', label: t('Onay'), children: formatDateTime(data.approved_at) }] : []),
          ]}
        />
      </Card>
      <InputCost cutting={data} />
      {data.status === 'TASLAK' ? <Weighing key={data.id} cutting={data} /> : <Result cutting={data} />}
    </Page>
  )
}

/** Giriş lotunun maliyet kalemleri (FR-203): fatura + ek maliyetler = lot değeri. */
function InputCost({ cutting }: { cutting: Cutting }) {
  const cost = cutting.input_cost
  if (!cost) return null
  const partial = cutting.total_cost !== null && cutting.total_cost !== cost.lot_value
  return (
    <Card size="small" title={t('Giriş maliyeti (alış kalemleri)')} style={{ marginBottom: 16 }}>
      <Descriptions
        size="small"
        column={{ xs: 1, sm: 2, lg: 3 }}
        items={[
          { key: 'doc', label: t('Alış belgesi'), children: `${cost.doc_no} · ${cost.supplier_name}` },
          {
            key: 'computed',
            label: t('Miktar × fiyat'),
            children: `${formatQty(cost.qty, 'KG')} × ${formatUnitCost(cost.unit_price)} = ${formatMoney(cost.computed_amount)}`,
          },
          {
            key: 'invoice',
            label: t('Fatura tutarı'),
            children:
              cost.invoice_amount === cost.computed_amount
                ? formatMoney(cost.invoice_amount)
                : `${formatMoney(cost.invoice_amount)} (${cost.discrepancy_note ?? 'fark'})`,
          },
          ...cost.extra_costs.map((extra, index) => ({
            key: `extra-${index}`,
            label: PURCHASE_COST_KIND[extra.kind],
            children: `${formatMoney(extra.amount)}${extra.note ? ` · ${extra.note}` : ''}`,
          })),
          { key: 'value', label: t('Lot değeri'), children: <strong>{formatMoney(cost.lot_value)}</strong> },
        ]}
      />
      {partial && (
        <Typography.Text type="secondary">
          {t('Bu parçalama lotun {qty} kadarını kullanıyor; maliyet payı {cost}.', {
            qty: formatQty(cutting.input_qty, 'KG'),
            cost: formatMoney(cutting.total_cost),
          })}
        </Typography.Text>
      )}
    </Card>
  )
}

/** Taslak: tartım girişi, canlı denge ve dağıtım, kaydet/onayla. */
function Weighing({ cutting }: { cutting: Cutting }) {
  const { message } = App.useApp()
  const queryClient = useQueryClient()
  const [method, setMethod] = useState<AllocationMethod>(cutting.method)
  const [texts, setTexts] = useState<Record<number, string>>(() =>
    Object.fromEntries(cutting.lines.map((line) => [line.recipe_line_id, fromApiDecimal(line.actual_kg) ?? ''])),
  )
  const [busy, setBusy] = useState<'save' | 'approve' | null>(null)
  const [error, setError] = useState<string | null>(null)

  // Geçersiz yazılan kg "tartılmadı" sayılır ve alanda işaretlenir.
  const invalid = useMemo(() => {
    const wrong = cutting.lines.filter((line) => {
      const text = texts[line.recipe_line_id]?.trim()
      return text && parseUserDecimal(text, 3) === null
    })
    return new Set(wrong.map((line) => line.recipe_line_id))
  }, [cutting.lines, texts])
  const body: ActualsInput = useMemo(
    () => ({
      method,
      outputs: cutting.lines.map((line) => ({
        recipe_line_id: line.recipe_line_id,
        actual_qty: parseUserDecimal(texts[line.recipe_line_id] ?? '', 3),
      })),
    }),
    [cutting.lines, method, texts],
  )
  const debounced = useDebounced(body)
  const preview = useQuery({
    queryKey: ['cutting-preview', cutting.id, debounced],
    queryFn: () => api<Cutting>(`/cuttings/${cutting.id}/preview`, { method: 'POST', body: debounced }),
    placeholderData: keepPreviousData,
  })
  const shown = preview.data ?? cutting
  const byLine = new Map(shown.lines.map((line) => [line.recipe_line_id, line]))

  async function save(): Promise<boolean> {
    if (invalid.size) {
      setError(t('Geçersiz ağırlıkları düzeltin (en çok 3 ondalık, binlik ayırıcı olmadan).'))
      return false
    }
    await api<Cutting>(`/cuttings/${cutting.id}`, { method: 'PUT', body })
    return true
  }

  async function run(action: 'save' | 'approve') {
    setBusy(action)
    setError(null)
    try {
      if (!(await save())) return
      if (action === 'approve') {
        const done = await api<Cutting>(`/cuttings/${cutting.id}/approve`, { method: 'POST' })
        message.success(t('{no} onaylandı: {amount} parçalara dağıtıldı.', { no: done.cutting_no, amount: formatMoney(done.allocated_total) }))
      } else {
        message.success(t('Tartım kaydedildi.'))
      }
      await refreshBusinessData(queryClient)
    } catch (caught) {
      setError(errorMessage(caught))
    } finally {
      setBusy(null)
    }
  }

  const columns: TableColumnsType<Line> = [
    {
      title: t('Kalem'),
      key: 'name',
      render: (_, line) => (
        <>
          {lineName(line)} <Tag color={TYPE_COLOR[line.line_type]}>{RECIPE_LINE_TYPE[line.line_type]}</Tag>
        </>
      ),
    },
    { title: t('Standart oran'), dataIndex: 'standard_ratio', align: 'right', render: percent },
    { title: t('Standart (referans)'), dataIndex: 'standard_kg', align: 'right', render: (v: string) => formatQty(v, 'KG') },
    {
      title: t('YZ tahmini (Model B)'),
      dataIndex: 'predicted_kg',
      align: 'right',
      render: (v: string | null) => formatQty(v, 'KG'),
    },
    {
      title: t('Fiili ağırlık'),
      key: 'actual',
      width: 160,
      render: (_, line) => (
        <Input
          aria-label={t('{name} fiili ağırlık (kg)', { name: lineName(line) })}
          inputMode="decimal"
          autoComplete="off"
          suffix="kg"
          status={invalid.has(line.recipe_line_id) ? 'error' : undefined}
          placeholder={line.line_type === 'FIRE' ? t('yoksa 0') : undefined}
          value={texts[line.recipe_line_id] ?? ''}
          onChange={(event) => setTexts((current) => ({ ...current, [line.recipe_line_id]: event.target.value }))}
        />
      ),
    },
    ...(method === 'DEGER'
      ? [
          {
            title: t('Değer katsayısı'),
            dataIndex: 'value_per_kg',
            align: 'right' as const,
            render: (v: string | null, line: Line) => (line.bears_cost ? `${formatUnitCost(v)}/kg` : '—'),
          },
        ]
      : []),
    {
      title: t('Maliyet payı'),
      key: 'share',
      align: 'right',
      render: (_, line) => formatMoney(byLine.get(line.recipe_line_id)?.allocated_cost),
    },
    {
      title: t('Birim maliyet'),
      key: 'per_kg',
      align: 'right',
      render: (_, line) => {
        const value = byLine.get(line.recipe_line_id)?.cost_per_kg
        return value ? `${formatUnitCost(value)}/kg` : '—'
      },
    },
  ]

  return (
    <Card
      size="small"
      title={t('Tartım ve maliyet dağıtımı')}
      extra={<Segmented<AllocationMethod> value={method} onChange={setMethod} options={options(ALLOCATION_METHOD)} />}
      style={{ marginBottom: 16 }}
    >
      {error && <Alert type="error" showIcon role="alert" title={error} style={{ marginBottom: 16 }} />}
      <BalanceNotice cutting={shown} />
      <Table<Line>
        rowKey="recipe_line_id"
        size="small"
        columns={columns}
        dataSource={cutting.lines}
        pagination={false}
        scroll={{ x: 'max-content' }}
        loading={preview.isFetching && !preview.data}
        summary={() => (
          <Table.Summary.Row>
            <Table.Summary.Cell index={0} colSpan={2}>
              <Typography.Text strong>{t('Toplam')}</Typography.Text>
            </Table.Summary.Cell>
            <Table.Summary.Cell index={2} align="right">
              {formatQty(sum(cutting.lines.map((l) => l.standard_kg), 3), 'KG')}
            </Table.Summary.Cell>
            <Table.Summary.Cell index={3} align="right">
              {cutting.lines.some((l) => l.predicted_kg)
                ? formatQty(sum(cutting.lines.map((l) => l.predicted_kg ?? '0'), 3), 'KG')
                : '—'}
            </Table.Summary.Cell>
            <Table.Summary.Cell index={4} align="right">
              <Typography.Text strong>{formatQty(shown.balance.outputs_kg, 'KG')}</Typography.Text>
            </Table.Summary.Cell>
            {method === 'DEGER' && <Table.Summary.Cell index={5} />}
            <Table.Summary.Cell index={method === 'DEGER' ? 6 : 5} align="right">
              <Typography.Text strong>{formatMoney(shown.allocated_total)}</Typography.Text>
            </Table.Summary.Cell>
            <Table.Summary.Cell index={method === 'DEGER' ? 7 : 6} />
          </Table.Summary.Row>
        )}
      />
      {shown.allocation_note && (
        <Typography.Paragraph type="secondary" style={{ marginTop: 12 }}>
          {shown.allocation_note}
        </Typography.Paragraph>
      )}
      <Typography.Paragraph type="secondary" style={{ marginTop: 12 }}>
        {t('Fire maliyet almaz; toplam maliyet ({cost}) parçalara ve yan ürünlere dağıtılır, kuruş farkı en büyük kalan yöntemiyle kapatılır. "Standart (referans)" sütunu reçetenin standart oranıdır; "YZ tahmini" Model B’nin parçalama açılırken kaydettiği beklentidir.', { cost: formatMoney(shown.total_cost) })}
      </Typography.Paragraph>
      <Flex gap="small" wrap>
        <Popconfirm
          title={t('Parçalama onaylansın mı?')}
          description={t('Giriş lotu tüketilir, parça lotları açılır; onaydan sonra değiştirilemez.')}
          okText={t('Onayla')}
          cancelText={t('Vazgeç')}
          onConfirm={() => run('approve')}
        >
          <Button type="primary" loading={busy === 'approve'}>
            {t('Onayla')}
          </Button>
        </Popconfirm>
        <Button loading={busy === 'save'} onClick={() => run('save')}>
          {t('Tartımı kaydet')}
        </Button>
      </Flex>
    </Card>
  )
}

/** Ağırlık dengesi göstergesi (FR-205): giriş = parçalar + yan ürünler + fire, tolerans içinde. */
function BalanceNotice({ cutting }: { cutting: Cutting }) {
  const b = cutting.balance
  const numbers = t('giriş {input}, çıkışlar {outputs}, fark {diff} (tolerans {tol})', {
    input: formatQty(b.input_kg, 'KG'),
    outputs: formatQty(b.outputs_kg, 'KG'),
    diff: formatQty(b.difference_kg, 'KG'),
    tol: formatQty(b.tolerance_kg, 'KG'),
  })
  if (b.missing_lines > 0) {
    return (
      <Alert
        type="info"
        showIcon
        style={{ marginBottom: 16 }}
        title={t('{n} kalemin ağırlığı girilmedi (fire yoksa 0 yazın).', { n: b.missing_lines })}
        description={t('Şu ana kadar: {numbers}.', { numbers })}
        aria-live="polite"
      />
    )
  }
  return (
    <Alert
      type={b.ok ? 'success' : 'error'}
      showIcon
      style={{ marginBottom: 16 }}
      title={b.ok ? t('Ağırlık dengesi tutuyor.') : t('Ağırlık dengesi tutmuyor; onaylanamaz.')}
      description={b.ok ? t('Denge: {numbers}.', { numbers }) : t('{numbers}. Eksik fire veya yan ürünü girin.', { numbers })}
      aria-live="polite"
    />
  )
}

/** Onaylı parçalama: dağıtım dökümü ve açılan lotlar. */
function Result({ cutting }: { cutting: Cutting }) {
  const fire = cutting.lines.filter((l) => l.line_type === 'FIRE' && l.actual_kg)
  const columns: TableColumnsType<Line> = [
    {
      title: t('Kalem'),
      key: 'name',
      render: (_, line) => (
        <>
          {lineName(line)} <Tag color={TYPE_COLOR[line.line_type]}>{RECIPE_LINE_TYPE[line.line_type]}</Tag>
        </>
      ),
    },
    { title: t('Standart (referans)'), dataIndex: 'standard_kg', align: 'right', render: (v: string) => formatQty(v, 'KG') },
    {
      title: t('YZ tahmini (Model B)'),
      dataIndex: 'predicted_kg',
      align: 'right',
      render: (v: string | null) => formatQty(v, 'KG'),
    },
    { title: t('Fiili'), dataIndex: 'actual_kg', align: 'right', render: (v: string | null) => formatQty(v, 'KG') },
    { title: t('Maliyet payı'), dataIndex: 'allocated_cost', align: 'right', render: formatMoney },
    {
      title: t('Birim maliyet'),
      dataIndex: 'cost_per_kg',
      align: 'right',
      render: (v: string | null) => (v ? `${formatUnitCost(v)}/kg` : '—'),
    },
    {
      title: t('Lot'),
      dataIndex: 'output_lot_no',
      render: (lotNo: string | null) => (lotNo ? <Link to={`/lotlar/${lotNo}`}>{lotNo}</Link> : '—'),
    },
  ]
  return (
    <>
      <Row gutter={16}>
        <Col xs={24} sm={12} lg={6}>
          <Card size="small" style={{ marginBottom: 16 }}>
            <Statistic title={t('Toplam maliyet')} value={formatMoney(cutting.total_cost)} />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card size="small" style={{ marginBottom: 16 }}>
            <Statistic title={t('Dağıtılan')} value={formatMoney(cutting.allocated_total)} />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card size="small" style={{ marginBottom: 16 }}>
            <Statistic title={t('Yöntem')} value={ALLOCATION_METHOD[cutting.method]} />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card size="small" style={{ marginBottom: 16 }}>
            <Statistic
              title={t('Fire')}
              value={fire.length ? formatQty(sum(fire.map((l) => l.actual_kg!), 3), 'KG') : t('0 kg')}
            />
          </Card>
        </Col>
      </Row>
      <Card size="small" title={t('Dağıtım dökümü ve parça lotları')}>
        <Table<Line>
          rowKey="recipe_line_id"
          size="small"
          columns={columns}
          dataSource={cutting.lines}
          pagination={false}
          scroll={{ x: 'max-content' }}
          summary={() => (
            <Table.Summary.Row>
              <Table.Summary.Cell index={0} colSpan={3}>
                <Typography.Text strong>{t('Toplam')}</Typography.Text>
              </Table.Summary.Cell>
              <Table.Summary.Cell index={3} align="right">
                <Typography.Text strong>{formatQty(cutting.balance.outputs_kg, 'KG')}</Typography.Text>
              </Table.Summary.Cell>
              <Table.Summary.Cell index={4} align="right">
                <Typography.Text strong>{formatMoney(cutting.allocated_total)}</Typography.Text>
              </Table.Summary.Cell>
              <Table.Summary.Cell index={5} colSpan={2} />
            </Table.Summary.Row>
          )}
        />
      </Card>
    </>
  )
}
