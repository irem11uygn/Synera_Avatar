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
import { t } from '../lib/i18n'

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
  'KUZU-BUT': t('But'),
  'KUZU-SIRT': t('Sırt'),
  'KUZU-OMUZ': t('Omuz'),
  'KUZU-KABURGA': t('Kaburga'),
  'KUZU-KIYMA': t('Kıyma'),
  FIRE: t('Fire'),
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
        <span>{t('Referans')}</span>
        <div className="bar-track" aria-hidden="true">
          <div className="bar-fill is-baseline" style={{ width: `${(baseline / max) * 100}%` }} />
        </div>
        <span style={{ textAlign: 'right' }}>
          {num(baseline, 3)} {unit}
        </span>
        <span>{t('Model')}</span>
        <div className="bar-track" aria-hidden="true">
          <div className="bar-fill" style={{ width: `${(model / max) * 100}%` }} />
        </div>
        <span style={{ textAlign: 'right' }}>
          {num(model, 3)} {unit} {better ? <Tag color="green">{t('daha iyi')}</Tag> : <Tag color="orange">{t('daha kötü')}</Tag>}
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
          { key: 'target', label: t('Tahmin edilen'), children: meta.target },
          { key: 'algo', label: t('Seçilen yöntem'), children: meta.algorithm },
          {
            key: 'cv',
            label: t('Çapraz doğrulama hatası'),
            children: Object.entries(meta.cv_mae)
              .map(([name, value]) => `${name}: ${num(value, 5)}`)
              .join(' · '),
          },
          { key: 'rows', label: t('Eğitim / test'), children: t('{train} / {test} kayıt', { train: meta.rows.train, test: meta.rows.test }) },
          { key: 'baseline', label: t('Referans yöntem'), children: meta.baseline },
          { key: 'features', label: t('Özellikler'), children: meta.features.join(', ') },
        ]}
      />
      {children}
    </Card>
  )
}

const REAL_COLUMNS = [
  { title: t('Model'), dataIndex: 'model', render: (m: string) => <Tag color={m === 'A' ? 'blue' : 'purple'}>Model {m}</Tag> },
  { title: t('Belge'), dataIndex: 'document_no' },
  { title: t('Kalem'), dataIndex: 'item' },
  { title: t('Tahmin'), dataIndex: 'predicted', align: 'right' as const, render: (v: string, r: RealComparison) => `${formatDecimal(v, 0, 3)} ${r.unit}` },
  { title: t('Gerçek'), dataIndex: 'actual', align: 'right' as const, render: (v: string, r: RealComparison) => `${formatDecimal(v, 0, 3)} ${r.unit}` },
  {
    title: t('Sapma (gerçek − tahmin)'),
    dataIndex: 'deviation',
    align: 'right' as const,
    render: (v: string, r: RealComparison) => `${v.startsWith('-') ? '' : '+'}${formatDecimal(v, 0, 3)} ${r.unit}`,
  },
]

export default function AiPage() {
  const evaluation = useQuery({ queryKey: ['ai-evaluation'], queryFn: () => api<AiEvaluation>('/ai/evaluation') })
  if (evaluation.isError) {
    return (
      <Page title={t('Yapay zekâ')}>
        <QueryError error={evaluation.error} onRetry={() => evaluation.refetch()} />
      </Page>
    )
  }
  if (evaluation.isPending) return <Spin />
  const data = evaluation.data
  const meta = data.metadata as Metadata | null

  return (
    <Page
      title={t('Yapay zekâ tahminleri')}
      description={t('İki model: fason üretimde kaç paket çıkacağını ve birim maliyeti, parçalamada her parçanın kaç kilo çıkacağını tahmin eder. Gerçek sonuç girilince tahminle karşılaştırılır.')}
    >
      {!data.available || !meta ? (
        <Alert type="warning" showIcon title={t('Model dosyaları bulunamadı')} description={data.message} />
      ) : (
        <>
          <Typography.Paragraph>
            {t('İki model zorunlu: Model A fason üretimde beklenen paket sayısını ve birim maliyeti (EKP), Model B parçalamada beklenen parça ağırlıklarını tahmin eder. Tahmin, emir ya da parçalama açılırken kaydedilir ve sonradan değişmez; gerçek sonuç gelince sapma bu kayda göre hesaplanır. İzleme ve geri çağırma tahmin kullanmaz.')}
          </Typography.Paragraph>
          <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
            <Col xs={12} lg={6}>
              <Stat
                label={t('Model A — paket hatası')}
                value={`−%${num(meta.model_a.test.improvement_pct.packages_mae, 1)}`}
                hint={t('Referansa göre daha az hata: {a} → {b} paket', {
                  a: num(meta.model_a.test.baseline.packages_mae as number),
                  b: num(meta.model_a.test.model.packages_mae as number),
                })}
              />
            </Col>
            <Col xs={12} lg={6}>
              <Stat
                label={t('Model A — birim maliyet hatası')}
                value={`−%${num(meta.model_a.test.improvement_pct.ekp_mae_eur, 1)}`}
                hint={t('Referansa göre daha az hata: {a} € → {b} €', {
                  a: num(meta.model_a.test.baseline.ekp_mae_eur as number),
                  b: num(meta.model_a.test.model.ekp_mae_eur as number),
                })}
                tone="success"
              />
            </Col>
            <Col xs={12} lg={6}>
              <Stat
                label={t('Model B — parça kg hatası')}
                value={`−%${num(meta.model_b.test.improvement_pct.mae_kg, 1)}`}
                hint={t('Referansa göre daha az hata: {a} → {b} kg', {
                  a: num(meta.model_b.test.baseline.mae_kg as number, 3),
                  b: num(meta.model_b.test.model.mae_kg as number, 3),
                })}
                tone="brand"
              />
            </Col>
            <Col xs={12} lg={6}>
              <Stat
                label={t('Veri')}
                value={`${meta.data.production_rows} + ${meta.data.cutting_rows}`}
                hint={t('Sentetik üretim + parçalama kaydı')}
                tone="warning"
              />
            </Col>
          </Row>

          <ModelSection title={t('Model A — fason üretim verimi ve birim maliyet')} meta={meta.model_a}>
            <CompareBars
              label={t('Paket sayısı ortalama mutlak hatası')}
              baseline={meta.model_a.test.baseline.packages_mae as number}
              model={meta.model_a.test.model.packages_mae as number}
              unit="paket"
            />
            <CompareBars
              label={t('Birim maliyet: ortalama hata (€)')}
              baseline={meta.model_a.test.baseline.ekp_mae_eur as number}
              model={meta.model_a.test.model.ekp_mae_eur as number}
              unit="€"
            />
            <CompareBars
              label={t('Birim maliyet: ortalama hata (%)')}
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
              title={() => t('Test verisinden örnek tahminler')}
              columns={[
                { title: t('Emir'), dataIndex: 'order_no' },
                { title: t('Fasoncu'), dataIndex: 'subcontractor' },
                { title: t('Tedarikçi'), dataIndex: 'meat_supplier' },
                { title: t('Et kg'), dataIndex: 'meat_kg', align: 'right' },
                { title: t('Gerçek paket'), dataIndex: 'actual_packages', align: 'right' },
                { title: t('Referans'), dataIndex: 'baseline_packages', align: 'right' },
                { title: t('Model'), dataIndex: 'model_packages', align: 'right' },
                { title: t('Gerçek birim maliyet'), dataIndex: 'actual_ekp', align: 'right', render: (v: number) => `${num(v)} €` },
                { title: t('Tahmini birim maliyet'), dataIndex: 'model_ekp', align: 'right', render: (v: number) => `${num(v)} €` },
              ]}
            />
          </ModelSection>

          <ModelSection title={t('Model B — parçalama verimi')} meta={meta.model_b}>
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

          <Card size="small" title={t('Sistemdeki gerçek kayıtlar: tahmin – gerçek – sapma')} style={{ marginBottom: 16 }}>
            <Table<RealComparison>
              rowKey={(r) => `${r.document_no}-${r.item}`}
              size="small"
              pagination={false}
              dataSource={data.real}
              columns={REAL_COLUMNS}
              scroll={{ x: 'max-content' }}
              locale={{ emptyText: t('Tahmini kaydedilmiş ve sonucu belli olmuş emir ya da parçalama yok.') }}
            />
          </Card>

          <Row gutter={16}>
            <Col xs={24} lg={12}>
              <Card size="small" title={t('Yöntem ve veri')} style={{ marginBottom: 16 }}>
                <Descriptions
                  size="small"
                  column={1}
                  items={[
                    { key: 'split', label: t('Ayırma'), children: meta.split },
                    { key: 'data', label: t('Veri'), children: `${meta.data.source}; ${meta.data.period}` },
                    { key: 'seed', label: t('Tohum'), children: meta.seed },
                    { key: 'trained', label: t('Eğitim zamanı'), children: meta.trained_at },
                  ]}
                />
              </Card>
            </Col>
            <Col xs={24} lg={12}>
              <Card size="small" title={t('Sınırlılıklar')} style={{ marginBottom: 16 }}>
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
