// Ne olur hesaplayıcıları: kayıt açmadan "fiyat şöyle olsaydı EKP ne olurdu?", "parçaları değere göre
// dağıtsak but kaça gelir?" Hesabı sunucu, gerçek kayıtta kullanılan aynı fonksiyonlarla yapar.

import { DeleteOutlined, PlusOutlined, UndoOutlined } from '@ant-design/icons'
import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { Alert, Button, Card, Checkbox, Col, Input, Row, Segmented, Space, Table, Tabs, Tag } from 'antd'
import { useState } from 'react'
import { api } from '../api/client'
import type { AllocationMethod, CuttingCalc, CuttingCalcInput, EkpCalc, EkpCalcInput, Recipe } from '../api/types'
import { Donut, IsoColumns } from '../components/charts'
import { Page } from '../components/Page'
import { QueryError } from '../components/QueryError'
import { Stat } from '../components/Stat'
import { parseUserDecimal } from '../lib/decimal'
import { formatDecimal, formatMoney, formatPercent, formatQty, formatUnitCost } from '../lib/format'
import { t } from '../lib/i18n'
import { ALLOCATION_METHOD } from '../lib/labels'
import { useDebounced } from '../lib/useDebounced'

type RawLine = { name: string; qty: string; unit_price: string }
type EkpState = {
  raw: RawLine[]
  service_unit_price: string
  received_qty: string
  invoiced_qty: string
  service_invoice_amount: string
  sale_price: string
}

// Görev 1 senaryosu: 100 kg et + 2 kg baharat + 5 kg bağırsak, 85 paket, hizmet 5,50 €/paket.
const EKP_SCENARIO: EkpState = {
  raw: [
    { name: t('Sucukluk et'), qty: '100', unit_price: '9,70' },
    { name: t('Sucuk baharatı'), qty: '2', unit_price: '24' },
    { name: t('Doğal bağırsak'), qty: '5', unit_price: '11,60' },
  ],
  service_unit_price: '5,50',
  received_qty: '85',
  invoiced_qty: '',
  service_invoice_amount: '',
  sale_price: '',
}

const dec = (text: string, places: number) => (text.trim() ? parseUserDecimal(text, places) : null)

function ekpInput(state: EkpState): EkpCalcInput | null {
  const raw = state.raw.map((line) => ({ name: line.name.trim() || '—', qty: dec(line.qty, 3), unit_price: dec(line.unit_price, 4) }))
  const fee = dec(state.service_unit_price, 4)
  const received = dec(state.received_qty, 3)
  if (raw.length === 0 || raw.some((l) => l.qty == null || l.unit_price == null) || fee == null || !received || received === '0')
    return null
  const optional = (text: string, places: number) => (text.trim() ? dec(text, places) : undefined)
  const values = {
    invoiced_qty: optional(state.invoiced_qty, 3),
    service_invoice_amount: optional(state.service_invoice_amount, 2),
    sale_price: optional(state.sale_price, 2),
  }
  if (Object.values(values).some((v) => v === null)) return null
  return {
    raw_lines: raw.map((l) => ({ name: l.name, qty: l.qty!, unit_price: l.unit_price! })),
    service_unit_price: fee,
    received_qty: received,
    invoiced_qty: values.invoiced_qty ?? null,
    service_invoice_amount: values.service_invoice_amount ?? null,
    sale_price: values.sale_price ?? null,
  }
}

function Field({ label, value, onChange, suffix, hint }: { label: string; value: string; onChange: (v: string) => void; suffix?: string; hint?: string }) {
  return (
    <label className="calc-field">
      <span className="calc-field-label">{label}</span>
      <Input value={value} onChange={(event) => onChange(event.target.value)} suffix={suffix} inputMode="decimal" autoComplete="off" />
      {hint && <span className="muted calc-field-hint">{hint}</span>}
    </label>
  )
}

function EkpCalculator() {
  const [state, setState] = useState<EkpState>(EKP_SCENARIO)
  const body = useDebounced(ekpInput(state), 350)
  const result = useQuery({
    queryKey: ['calc', 'ekp', body],
    queryFn: () => api<EkpCalc>('/calc/ekp', { method: 'POST', body }),
    enabled: body != null,
    placeholderData: keepPreviousData,
  })
  const set = (patch: Partial<EkpState>) => setState((s) => ({ ...s, ...patch }))
  const setLine = (i: number, patch: Partial<RawLine>) => set({ raw: state.raw.map((l, k) => (k === i ? { ...l, ...patch } : l)) })
  const data = result.data

  return (
    <Row gutter={[16, 16]}>
      <Col xs={24} lg={11}>
        <Card
          title={t('Girdiler')}
          extra={
            <Button size="small" icon={<UndoOutlined />} onClick={() => setState(EKP_SCENARIO)}>
              {t('Senaryoya dön')}
            </Button>
          }
        >
          <div className="calc-subtitle">{t('Hammaddeler (miktar × birim fiyat)')}</div>
          {state.raw.map((line, i) => (
            <div className="calc-line" key={i}>
              <Input aria-label={t('Hammadde')} value={line.name} onChange={(e) => setLine(i, { name: e.target.value })} />
              <Input aria-label={t('Miktar')} value={line.qty} onChange={(e) => setLine(i, { qty: e.target.value })} suffix="kg" inputMode="decimal" />
              <Input aria-label={t('Birim fiyat')} value={line.unit_price} onChange={(e) => setLine(i, { unit_price: e.target.value })} suffix="€" inputMode="decimal" />
              <Button
                aria-label={t('Satırı sil')}
                icon={<DeleteOutlined />}
                disabled={state.raw.length === 1}
                onClick={() => set({ raw: state.raw.filter((_, k) => k !== i) })}
              />
            </div>
          ))}
          <Button size="small" icon={<PlusOutlined />} onClick={() => set({ raw: [...state.raw, { name: '', qty: '', unit_price: '' }] })} style={{ marginBottom: 16 }}>
            {t('Hammadde ekle')}
          </Button>
          <div className="calc-grid">
            <Field label={t('Hizmet ücreti (adet başına)')} value={state.service_unit_price} onChange={(v) => set({ service_unit_price: v })} suffix="€" />
            <Field label={t('Teslim alınan adet')} value={state.received_qty} onChange={(v) => set({ received_qty: v })} suffix={t('adet')} />
            <Field
              label={t('Faturadaki adet')}
              value={state.invoiced_qty}
              onChange={(v) => set({ invoiced_qty: v })}
              hint={t('Boşsa teslim alınanla aynı sayılır.')}
            />
            <Field
              label={t('Hizmet faturası tutarı')}
              value={state.service_invoice_amount}
              onChange={(v) => set({ service_invoice_amount: v })}
              suffix="€"
              hint={t('Boşsa adet × ücret.')}
            />
            <Field label={t('Satış fiyatı (VKP)')} value={state.sale_price} onChange={(v) => set({ sale_price: v })} suffix="€" hint={t('Kâr ve marj için.')} />
          </div>
        </Card>
      </Col>
      <Col xs={24} lg={13}>
        {body == null && <Alert type="warning" showIcon title={t('Bir alan eksik ya da sayı geçersiz; hesap için düzeltin.')} style={{ marginBottom: 12 }} />}
        {result.isError && <QueryError error={result.error} onRetry={() => result.refetch()} />}
        {data && (
          <>
            <Row gutter={[12, 12]}>
              <Col xs={12} md={8}>
                <Stat label={t('EKP (birim maliyet)')} value={formatMoney(data.ekp_display)} tone="brand" hint={t('6 basamak: {v} €', { v: formatDecimal(data.ekp, 6, 6) })} />
              </Col>
              <Col xs={12} md={8}>
                <Stat label={t('Toplam maliyet')} value={formatMoney(data.total)} hint={t('Hammadde + hizmet')} />
              </Col>
              <Col xs={24} md={8}>
                <Stat
                  label={t('Brüt kâr / adet')}
                  value={data.gross_profit_per_unit ? formatMoney(data.gross_profit_per_unit) : '—'}
                  tone={data.gross_profit_per_unit == null ? 'neutral' : data.gross_profit_per_unit.startsWith('-') ? 'danger' : 'success'}
                  hint={data.margin_pct ? t('Marj {m} · toplam {p}', { m: formatPercent(data.margin_pct), p: formatMoney(data.total_gross_profit) }) : t('VKP girilmedi')}
                />
              </Col>
            </Row>
            {data.warnings.map((warning) => (
              <Alert key={warning} type="warning" showIcon title={warning} style={{ marginTop: 12 }} />
            ))}
            <Card size="small" title={t('Maliyetin dağılımı')} style={{ marginTop: 12 }}>
              <Donut
                slices={[...data.raw_lines.map((l) => ({ label: l.name, value: l.amount })), { label: t('Dış üretim hizmeti'), value: data.service_used }]}
                center={formatMoney(data.ekp_display)}
                centerHint={t('/ adet')}
              />
            </Card>
          </>
        )}
      </Col>
    </Row>
  )
}

type CutLine = { name: string; kg: string; value_per_kg: string; is_fire: boolean }
type CutState = { input_kg: string; input_cost: string; invoice_kg: string; method: AllocationMethod; tolerance_kg: string; lines: CutLine[] }

// Görev 2 senaryosu: 25 kg kuzu, alış 25 × 11,50 + kesim 40 + nakliye 23,50 = 351,00 €.
const DEMO_KG: Record<string, string> = { 'KUZU-BUT': '7', 'KUZU-SIRT': '4', 'KUZU-OMUZ': '5', 'KUZU-KABURGA': '3', 'KUZU-KIYMA': '3' }

function scenario(recipe: Recipe | undefined): CutState {
  const lines = (recipe?.lines ?? [])
    .slice()
    .sort((a, b) => a.sort_order - b.sort_order)
    .map((line) => ({
      name: line.product_name ?? t('Fire'),
      kg: line.line_type === 'FIRE' ? '3' : DEMO_KG[line.product_code ?? ''] ?? '0',
      value_per_kg: line.value_per_kg ? formatDecimal(line.value_per_kg, 0, 4) : '',
      is_fire: line.line_type === 'FIRE',
    }))
  return {
    input_kg: '25',
    input_cost: '351',
    invoice_kg: '',
    method: recipe?.default_method ?? 'DEGER',
    tolerance_kg: recipe ? formatDecimal(recipe.tolerance_kg, 0, 3) : '0,5',
    lines,
  }
}

function cuttingInput(state: CutState): CuttingCalcInput | null {
  const inputKg = dec(state.input_kg, 3)
  const cost = dec(state.input_cost, 2)
  const tolerance = dec(state.tolerance_kg, 3)
  const invoice = state.invoice_kg.trim() ? dec(state.invoice_kg, 3) : undefined
  const lines = state.lines.map((l) => ({
    name: l.name.trim() || '—',
    kg: dec(l.kg, 3),
    value_per_kg: l.value_per_kg.trim() ? dec(l.value_per_kg, 4) : undefined,
    is_fire: l.is_fire,
  }))
  if (!inputKg || inputKg === '0' || cost == null || tolerance == null || invoice === null || lines.length === 0) return null
  if (lines.some((l) => l.kg == null || l.value_per_kg === null)) return null
  return {
    input_kg: inputKg,
    input_cost: cost,
    invoice_kg: invoice ?? null,
    method: state.method,
    tolerance_kg: tolerance,
    lines: lines.map((l) => ({ name: l.name, kg: l.kg!, value_per_kg: l.value_per_kg ?? null, is_fire: l.is_fire, bears_cost: true })),
  }
}

function CuttingCalculator() {
  const recipes = useQuery({ queryKey: ['recipes'], queryFn: () => api<Recipe[]>('/cutting-recipes') })
  const recipe = recipes.data?.[0]
  const [state, setState] = useState<CutState | null>(null)
  const current = state ?? (recipe ? scenario(recipe) : null)
  const body = useDebounced(current ? cuttingInput(current) : null, 350)
  const result = useQuery({
    queryKey: ['calc', 'cutting', body],
    queryFn: () => api<CuttingCalc>('/calc/cutting', { method: 'POST', body }),
    enabled: body != null,
    placeholderData: keepPreviousData,
  })
  if (recipes.isError) return <QueryError error={recipes.error} onRetry={() => recipes.refetch()} />
  if (!current) return <Card loading />
  const set = (patch: Partial<CutState>) => setState({ ...current, ...patch })
  const setLine = (i: number, patch: Partial<CutLine>) => set({ lines: current.lines.map((l, k) => (k === i ? { ...l, ...patch } : l)) })
  const data = result.data

  return (
    <Row gutter={[16, 16]}>
      <Col xs={24} lg={11}>
        <Card
          title={t('Girdiler')}
          extra={
            <Button size="small" icon={<UndoOutlined />} onClick={() => setState(scenario(recipe))}>
              {t('Senaryoya dön')}
            </Button>
          }
        >
          <div className="calc-grid">
            <Field label={t('Giriş ağırlığı (tartılan)')} value={current.input_kg} onChange={(v) => set({ input_kg: v })} suffix="kg" />
            <Field label={t('Toplam maliyet')} value={current.input_cost} onChange={(v) => set({ input_cost: v })} suffix="€" hint={t('Alış + kesim + nakliye')} />
            <Field label={t('Faturadaki ağırlık')} value={current.invoice_kg} onChange={(v) => set({ invoice_kg: v })} suffix="kg" hint={t('Tartımla karşılaştırmak için.')} />
            <Field label={t('Tartım toleransı')} value={current.tolerance_kg} onChange={(v) => set({ tolerance_kg: v })} suffix="kg" />
          </div>
          <div className="calc-subtitle" style={{ marginTop: 8 }}>
            {t('Dağıtım yöntemi')}
          </div>
          <Segmented<AllocationMethod>
            value={current.method}
            onChange={(method) => set({ method })}
            options={[
              { value: 'DEGER', label: ALLOCATION_METHOD.DEGER },
              { value: 'MIKTAR', label: ALLOCATION_METHOD.MIKTAR },
            ]}
            style={{ marginBottom: 12 }}
          />
          <div className="calc-subtitle">{t('Çıkan parçalar (kg · piyasa değeri €/kg)')}</div>
          {current.lines.map((line, i) => (
            <div className="calc-line" key={i}>
              <Input aria-label={t('Parça')} value={line.name} onChange={(e) => setLine(i, { name: e.target.value })} />
              <Input aria-label={t('Ağırlık')} value={line.kg} onChange={(e) => setLine(i, { kg: e.target.value })} suffix="kg" inputMode="decimal" />
              <Input
                aria-label={t('Değer €/kg')}
                value={line.value_per_kg}
                disabled={line.is_fire}
                onChange={(e) => setLine(i, { value_per_kg: e.target.value })}
                suffix="€/kg"
                inputMode="decimal"
              />
              <Checkbox checked={line.is_fire} onChange={(e) => setLine(i, { is_fire: e.target.checked })}>
                {t('Fire')}
              </Checkbox>
            </div>
          ))}
        </Card>
      </Col>
      <Col xs={24} lg={13}>
        {body == null && <Alert type="warning" showIcon title={t('Bir alan eksik ya da sayı geçersiz; hesap için düzeltin.')} style={{ marginBottom: 12 }} />}
        {result.isError && <QueryError error={result.error} onRetry={() => result.refetch()} />}
        {data && (
          <>
            <Row gutter={[12, 12]}>
              <Col xs={12} md={8}>
                <Stat label={t('Giriş birim maliyeti')} value={formatUnitCost(data.input_unit_cost)} tone="brand" hint={t('€/kg')} />
              </Col>
              <Col xs={12} md={8}>
                <Stat label={t('Fire')} value={formatQty(data.fire_kg, 'KG')} hint={formatPercent(data.fire_pct)} tone="warning" />
              </Col>
              <Col xs={24} md={8}>
                <Stat
                  label={t('Ağırlık dengesi')}
                  value={data.balance_ok ? t('Tutuyor') : t('Tutmuyor')}
                  tone={data.balance_ok ? 'success' : 'danger'}
                  hint={t('Fark {d}', { d: formatQty(data.difference_kg, 'KG') })}
                />
              </Col>
            </Row>
            {data.warnings.map((warning) => (
              <Alert key={warning} type="warning" showIcon title={warning} style={{ marginTop: 12 }} />
            ))}
            <Card size="small" title={t('Parça maliyeti (€/kg) — 3B')} style={{ marginTop: 12 }}>
              <IsoColumns
                unit="€/kg"
                items={data.lines.filter((l) => l.unit_cost).map((l) => ({ label: l.name, value: l.unit_cost!, hint: formatQty(l.kg, 'KG') }))}
              />
            </Card>
            <Card size="small" style={{ marginTop: 12 }}>
              <Table
                size="small"
                rowKey="name"
                pagination={false}
                dataSource={data.lines}
                scroll={{ x: 'max-content' }}
                summary={() => (
                  <Table.Summary.Row>
                    <Table.Summary.Cell index={0}>
                      <strong>{t('Toplam')}</strong>
                    </Table.Summary.Cell>
                    <Table.Summary.Cell index={1} align="right">
                      {formatQty(data.outputs_kg, 'KG')}
                    </Table.Summary.Cell>
                    <Table.Summary.Cell index={2} />
                    <Table.Summary.Cell index={3} align="right">
                      <strong>{formatMoney(data.total_allocated)}</strong>
                    </Table.Summary.Cell>
                    <Table.Summary.Cell index={4} />
                  </Table.Summary.Row>
                )}
                columns={[
                  { title: t('Parça'), dataIndex: 'name', render: (name: string, row) => (row.is_fire ? <Tag>{name}</Tag> : name) },
                  { title: t('Ağırlık'), dataIndex: 'kg', align: 'right', render: (v: string) => formatQty(v, 'KG') },
                  { title: t('Pay'), dataIndex: 'share_pct', align: 'right', render: formatPercent },
                  { title: t('Maliyet payı'), dataIndex: 'allocated_cost', align: 'right', render: formatMoney },
                  { title: t('Birim maliyet'), dataIndex: 'unit_cost', align: 'right', render: (v: string | null) => (v ? `${formatUnitCost(v)} / kg` : '—') },
                ]}
              />
            </Card>
          </>
        )}
      </Col>
    </Row>
  )
}

export default function CalculatorsPage() {
  return (
    <Page
      title={t('Ne olur hesaplayıcıları')}
      description={t('Kayıt açmadan dener gibi hesaplayın: fiyat, adet ya da tartım değişirse birim maliyet ne olur? Hesap, gerçek kayıtlarda kullanılan aynı kurallarla sunucuda yapılır; hiçbir şey kaydedilmez.')}
    >
      <Space orientation="vertical" style={{ width: '100%' }}>
        <Tabs
          items={[
            { key: 'ekp', label: t('Dış üretim EKP'), children: <EkpCalculator /> },
            { key: 'cutting', label: t('Parçalama maliyeti'), children: <CuttingCalculator /> },
          ]}
        />
      </Space>
    </Page>
  )
}
