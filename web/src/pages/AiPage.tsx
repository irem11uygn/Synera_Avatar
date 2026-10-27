// Yapay zekâ değerlendirmesi (FR-501…FR-507, CR-006): yöntem, veri, referans yöntemle karşılaştırma,
// hata ölçümleri, örnek tahminler, sınırlılıklar ve sistemdeki gerçek kayıtlarla karşılaştırma.
// Rakamlar sunucudan (ml/models/metadata.json); bu ekran hesap yapmaz, yalnız gösterir.

import { useQuery } from '@tanstack/react-query'
import { Alert, Card, Col, Descriptions, Row, Spin, Table, Tag, Typography } from 'antd'
import type { ReactNode } from 'react'
import { api } from '../api/client'
import type { AiEvaluation, RealComparison } from '../api/types'
import { Stat } from '../components/Stat'
import { Page } from '../components/Page'
import { QueryError } from '../components/QueryError'
import { formatDecimal } from '../lib/format'

type Metrics = Record<string, number | Record<string, number>>
type ModelMeta = {
  version: string
  target: string
  algorithm: string
  cv_mae: Record<string, number>
  features: string[]
  rows: { train: number; test: number }
  baseline: string
  test: { baseline: Metrics; model: Metrics; improvement_pct: Record<string, number> }
  samples: Record<string, unknown>[]
}
type Metadata = {
  trained_at: string
  seed: number
  data: { production_rows: number; cutting_rows: number; period: string; source: string }
  split: string
  model_a: ModelMeta
  model_b: ModelMeta
  limitations: string[]
}

const PART_NAME: Record<string, string> = {
  'KUZU-BUT': 'But',
  'KUZU-SIRT': 'Sırt',
  'KUZU-OMUZ': 'Omuz',
  'KUZU-KABURGA': 'Kaburga',
  'KUZU-KIYMA': 'Kıyma',
  FIRE: 'Fire',
}

const num = (value: number, digits = 2) => formatDecimal(value.toFixed(digits), 0, digits)

/** Referans ve model hatasını yan yana çubukla gösterir; kısa çubuk daha iyi. */
function CompareBars({ label, baseline, model, unit }: { label: string; baseline: number; model: number; unit: string }) {
  const max = Math.max(baseline, model) || 1
  const better = model < baseline
  return (
    <div style={{ marginBottom: 14 }}>
      <Typography.Text strong>{label}</Typography.Text>
      <div style={{ display: 'grid', gridTemplateColumns: '84px 1fr 96px', gap: 8, alignItems: 'center', marginTop: 6 }}>
        <span>Referans</span>
        <div className="bar-track" aria-hidden="true">
          <div className="bar-fill is-baseline" style={{ width: `${(baseline / max) * 100}%` }} />
        </div>
        <span style={{ textAlign: 'right' }}>
          {num(baseline, 3)} {unit}
        </span>
        <span>Model</span>
        <div className="bar-track" aria-hidden="true">
          <div className="bar-fill" style={{ width: `${(model / max) * 100}%` }} />
        </div>
        <span style={{ textAlign: 'right' }}>
          {num(model, 3)} {unit} {better ? <Tag color="green">daha iyi</Tag> : <Tag color="orange">daha kötü</Tag>}
        </span>
      </div>
    </div>
  )
}

function ModelSection({ title, meta, children }: { title: string; meta: ModelMeta; children: ReactNode }) {
  return (
    <Card size="small" title={title} extra={<Tag>{meta.version}</Tag>} style={{ marginBottom: 16 }}>
      <Descriptions
        size="small"
        column={{ xs: 1, xxl: 2 }}
        style={{ marginBottom: 12 }}
        items={[
          { key: 'target', label: 'Tahmin edilen', children: meta.target },
          { key: 'algo', label: 'Seçilen yöntem', children: meta.algorithm },
          {
            key: 'cv',
            label: 'Çapraz doğrulama hatası',
            children: Object.entries(meta.cv_mae)
              .map(([name, value]) => `${name}: ${num(value, 5)}`)
              .join(' · '),
          },
          { key: 'rows', label: 'Eğitim / test', children: `${meta.rows.train} / ${meta.rows.test} kayıt` },
          { key: 'baseline', label: 'Referans yöntem', children: meta.baseline },
          { key: 'features', label: 'Özellikler', children: meta.features.join(', ') },
        ]}
      />
      {children}
    </Card>
  )
}

const REAL_COLUMNS = [
  { title: 'Model', dataIndex: 'model', render: (m: string) => <Tag color={m === 'A' ? 'blue' : 'purple'}>Model {m}</Tag> },
  { title: 'Belge', dataIndex: 'document_no' },
  { title: 'Kalem', dataIndex: 'item' },
  { title: 'Tahmin', dataIndex: 'predicted', align: 'right' as const, render: (v: string, r: RealComparison) => `${formatDecimal(v, 0, 3)} ${r.unit}` },
  { title: 'Gerçek', dataIndex: 'actual', align: 'right' as const, render: (v: string, r: RealComparison) => `${formatDecimal(v, 0, 3)} ${r.unit}` },
  {
    title: 'Sapma (gerçek − tahmin)',
    dataIndex: 'deviation',
    align: 'right' as const,
    render: (v: string, r: RealComparison) => `${v.startsWith('-') ? '' : '+'}${formatDecimal(v, 0, 3)} ${r.unit}`,
  },
]

export default function AiPage() {
  const evaluation = useQuery({ queryKey: ['ai-evaluation'], queryFn: () => api<AiEvaluation>('/ai/evaluation') })
  if (evaluation.isError) {
    return (
      <Page title="Yapay zekâ">
        <QueryError error={evaluation.error} onRetry={() => evaluation.refetch()} />
      </Page>
    )
  }
  if (evaluation.isPending) return <Spin />
  const data = evaluation.data
  const meta = data.metadata as Metadata | null

  return (
    <Page
      title="Yapay zekâ tahminleri"
      description="İki model: fason üretimde kaç paket çıkacağını ve birim maliyeti, parçalamada her parçanın kaç kilo çıkacağını tahmin eder. Gerçek sonuç girilince tahminle karşılaştırılır."
    >
      {!data.available || !meta ? (
        <Alert type="warning" showIcon title="Model dosyaları bulunamadı" description={data.message} />
      ) : (
        <>
          <Typography.Paragraph>
            İki model zorunlu: <strong>Model A</strong> fason üretimde beklenen paket sayısını ve birim maliyeti
            (EKP), <strong>Model B</strong> parçalamada beklenen parça ağırlıklarını tahmin eder. Tahmin, emir ya da
            parçalama açılırken kaydedilir ve sonradan değişmez; gerçek sonuç gelince sapma bu kayda göre hesaplanır.
            İzleme ve geri çağırma tahmin kullanmaz.
          </Typography.Paragraph>
          <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
            <Col xs={12} lg={6}>
              <Stat
                label="Model A — paket hatası"
                value={`−%${num(meta.model_a.test.improvement_pct.packages_mae, 1)}`}
                hint={`Referansa göre daha az hata: ${num(meta.model_a.test.baseline.packages_mae as number)} → ${num(meta.model_a.test.model.packages_mae as number)} paket`}
              />
            </Col>
            <Col xs={12} lg={6}>
              <Stat
                label="Model A — birim maliyet hatası"
                value={`−%${num(meta.model_a.test.improvement_pct.ekp_mae_eur, 1)}`}
                hint={`Referansa göre daha az hata: ${num(meta.model_a.test.baseline.ekp_mae_eur as number)} € → ${num(meta.model_a.test.model.ekp_mae_eur as number)} €`}
                tone="success"
              />
            </Col>
            <Col xs={12} lg={6}>
              <Stat
                label="Model B — parça kg hatası"
                value={`−%${num(meta.model_b.test.improvement_pct.mae_kg, 1)}`}
                hint={`Referansa göre daha az hata: ${num(meta.model_b.test.baseline.mae_kg as number, 3)} → ${num(meta.model_b.test.model.mae_kg as number, 3)} kg`}
                tone="brand"
              />
            </Col>
            <Col xs={12} lg={6}>
              <Stat
                label="Veri"
                value={`${meta.data.production_rows} + ${meta.data.cutting_rows}`}
                hint="Sentetik üretim + parçalama kaydı"
                tone="warning"
              />
            </Col>
          </Row>

          <ModelSection title="Model A — fason üretim verimi ve birim maliyet" meta={meta.model_a}>
            <CompareBars
              label="Paket sayısı ortalama mutlak hatası"
              baseline={meta.model_a.test.baseline.packages_mae as number}
              model={meta.model_a.test.model.packages_mae as number}
              unit="paket"
            />
            <CompareBars
              label="Birim maliyet: ortalama hata (€)"
              baseline={meta.model_a.test.baseline.ekp_mae_eur as number}
              model={meta.model_a.test.model.ekp_mae_eur as number}
              unit="€"
            />
            <CompareBars
              label="Birim maliyet: ortalama hata (%)"
              baseline={meta.model_a.test.baseline.ekp_mape_pct as number}
              model={meta.model_a.test.model.ekp_mape_pct as number}
              unit="%"
            />
            <Table
              rowKey="order_no"
              size="small"
              pagination={false}
              scroll={{ x: 'max-content' }}
              dataSource={meta.model_a.samples}
              title={() => 'Test verisinden örnek tahminler'}
              columns={[
                { title: 'Emir', dataIndex: 'order_no' },
                { title: 'Fasoncu', dataIndex: 'subcontractor' },
                { title: 'Tedarikçi', dataIndex: 'meat_supplier' },
                { title: 'Et kg', dataIndex: 'meat_kg', align: 'right' },
                { title: 'Gerçek paket', dataIndex: 'actual_packages', align: 'right' },
                { title: 'Referans', dataIndex: 'baseline_packages', align: 'right' },
                { title: 'Model', dataIndex: 'model_packages', align: 'right' },
                { title: 'Gerçek birim maliyet', dataIndex: 'actual_ekp', align: 'right', render: (v: number) => `${num(v)} €` },
                { title: 'Tahmini birim maliyet', dataIndex: 'model_ekp', align: 'right', render: (v: number) => `${num(v)} €` },
              ]}
            />
          </ModelSection>

          <ModelSection title="Model B — parçalama verimi" meta={meta.model_b}>
            {Object.entries(meta.model_b.test.baseline.mae_kg_by_part as Record<string, number>).map(([part, base]) => (
              <CompareBars
                key={part}
                label={`${PART_NAME[part] ?? part} — ortalama mutlak hata`}
                baseline={base}
                model={(meta.model_b.test.model.mae_kg_by_part as Record<string, number>)[part]}
                unit="kg"
              />
            ))}
          </ModelSection>

          <Card size="small" title="Sistemdeki gerçek kayıtlar: tahmin – gerçek – sapma" style={{ marginBottom: 16 }}>
            <Table<RealComparison>
              rowKey={(r) => `${r.document_no}-${r.item}`}
              size="small"
              pagination={false}
              dataSource={data.real}
              columns={REAL_COLUMNS}
              scroll={{ x: 'max-content' }}
              locale={{ emptyText: 'Tahmini kaydedilmiş ve sonucu belli olmuş emir ya da parçalama yok.' }}
            />
          </Card>

          <Row gutter={16}>
            <Col xs={24} lg={12}>
              <Card size="small" title="Yöntem ve veri" style={{ marginBottom: 16 }}>
                <Descriptions
                  size="small"
                  column={1}
                  items={[
                    { key: 'split', label: 'Ayırma', children: meta.split },
                    { key: 'data', label: 'Veri', children: `${meta.data.source}; ${meta.data.period}` },
                    { key: 'seed', label: 'Tohum', children: meta.seed },
                    { key: 'trained', label: 'Eğitim zamanı', children: meta.trained_at },
                  ]}
                />
              </Card>
            </Col>
            <Col xs={24} lg={12}>
              <Card size="small" title="Sınırlılıklar" style={{ marginBottom: 16 }}>
                <ol style={{ margin: 0, paddingInlineStart: 20, display: 'grid', gap: 8 }}>
                  {meta.limitations.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ol>
              </Card>
            </Col>
          </Row>
        </>
      )}
    </Page>
  )
}
