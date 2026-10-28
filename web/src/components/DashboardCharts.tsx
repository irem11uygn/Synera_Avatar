// Ana sayfa paneli: EKP geçmişi ve model tahmini, hedef/gerçekleşen, maliyet dağılımı,
// izometrik 3B parça maliyetleri, müşteri sevkiyatı ve açık alarmlar.

import { useQuery } from '@tanstack/react-query'
import { Button, Col, Row, Segmented, Skeleton } from 'antd'
import { useState } from 'react'
import { api } from '../api/client'
import type { AlertSummary, Charts } from '../api/types'
import { formatDate, formatDateTime, formatDecimal, formatMoney, formatQty } from '../lib/format'
import { t } from '../lib/i18n'
import { ALERT_KIND } from '../lib/labels'
import { navigate } from '../lib/router'
import { SeverityIcon } from './AlarmBell'
import { ActualForecastLine, ChartCard, Donut, Gauge, HBars, IsoColumns } from './charts'
import { QueryError } from './QueryError'

export function DashboardCharts() {
  const charts = useQuery({ queryKey: ['dashboard', 'charts'], queryFn: () => api<Charts>('/dashboard/charts'), refetchInterval: 300_000 })
  const alarms = useQuery({ queryKey: ['alerts', 'summary'], queryFn: () => api<AlertSummary>('/alerts/summary') })
  const data = charts.data
  const [source, setSource] = useState<'real' | 'synthetic' | null>(null)

  if (charts.isError) return <QueryError error={charts.error} onRetry={() => charts.refetch()} />
  if (!data) return <Skeleton active paragraph={{ rows: 6 }} />

  // Sistemde 3'ten az emir varken çizgi anlamsız: model test verisi (sentetik) önce gösterilir.
  const chosen = source ?? (data.ekp_history.length >= 3 || data.ekp_synthetic.length === 0 ? 'real' : 'synthetic')
  const points = chosen === 'real' ? data.ekp_history : data.ekp_synthetic
  const shipmentQty = (s: Charts['shipments'][number]) =>
    Object.entries(s.qty_by_unit)
      .map(([unit, qty]) => formatQty(qty, unit === 'adet' ? 'ADET' : 'KG'))
      .join(' + ')

  return (
    <>
      <Row gutter={[16, 16]}>
        <Col xs={24} xl={16}>
          <ChartCard
            title={t('Birim maliyet (EKP): gerçek ve model tahmini')}
            subtitle={
              chosen === 'real'
                ? t('Sistemdeki tamamlanmış dış üretim emirleri; kesikli çizgi emir açılırken kaydedilen model tahmini.')
                : t('Sentetik geçmiş: modelin eğitimde görmediği test emirleri (gerçek kayıt değildir).')
            }
            extra={
              <Segmented
                size="small"
                value={chosen}
                onChange={(value) => setSource(value as 'real' | 'synthetic')}
                options={[
                  { value: 'real', label: t('Sistemdeki emirler ({n})', { n: data.ekp_history.length }) },
                  { value: 'synthetic', label: t('Model testi (sentetik)') },
                ]}
              />
            }
            table={{
              columns: [
                { key: 'label', title: t('Emir') },
                { key: 'day', title: t('Tarih') },
                { key: 'actual', title: t('Gerçek EKP'), align: 'right' },
                { key: 'forecast', title: t('Model tahmini'), align: 'right' },
              ],
              rows: points.map((p) => ({
                key: p.label,
                label: p.label,
                day: formatDate(p.day),
                actual: formatMoney(p.actual),
                forecast: p.forecast ? formatMoney(p.forecast) : '—',
              })),
            }}
          >
            <ActualForecastLine points={points} unit="€" actualLabel={t('Gerçek EKP')} forecastLabel={t('Model tahmini')} />
          </ChartCard>
        </Col>
        <Col xs={24} md={12} xl={8}>
          <ChartCard title={t('Hedef / gerçekleşen')} subtitle={t('Son 30 gün dış üretim: planlanan ve teslim alınan miktar')}>
            <Gauge
              percent={data.fill_rate_pct}
              caption={
                data.target_qty === '0' || Number(data.target_qty) === 0
                  ? t('Son 30 günde tamamlanan emir yok')
                  : t('{a} / {p} teslim alındı', { a: formatDecimal(data.actual_qty, 0, 3), p: formatDecimal(data.target_qty, 0, 3) })
              }
            />
          </ChartCard>
        </Col>
        <Col xs={24} md={12} xl={12}>
          <ChartCard
            title={t('Maliyet dağılımı')}
            subtitle={data.cost_order_no ? t('{no}: EKP’yi oluşturan kalemler', { no: data.cost_order_no }) : t('Henüz tamamlanmış dış üretim yok.')}
            table={{
              columns: [
                { key: 'label', title: t('Kalem') },
                { key: 'value', title: t('Tutar'), align: 'right' },
              ],
              rows: data.cost_slices.map((s) => ({ key: s.label, label: s.label, value: formatMoney(s.value) })),
            }}
          >
            {data.cost_slices.length > 0 ? (
              <Donut slices={data.cost_slices} center={formatMoney(data.cost_ekp)} centerHint={t('EKP / adet')} />
            ) : (
              <p className="muted">{t('Gösterilecek kayıt yok.')}</p>
            )}
          </ChartCard>
        </Col>
        <Col xs={24} xl={12}>
          <ChartCard
            title={t('Parça maliyetleri (3B)')}
            subtitle={data.parts_cutting_no ? t('{no}: parça başına maliyet, €/kg', { no: data.parts_cutting_no }) : t('Henüz onaylanmış parçalama yok.')}
            table={{
              columns: [
                { key: 'label', title: t('Parça') },
                { key: 'kg', title: t('Ağırlık'), align: 'right' },
                { key: 'cost', title: t('€/kg'), align: 'right' },
              ],
              rows: data.part_costs.map((p) => ({ key: p.label, label: p.label, kg: formatQty(p.kg, 'KG'), cost: formatMoney(p.unit_cost) })),
            }}
          >
            <IsoColumns unit="€/kg" items={data.part_costs.map((p) => ({ label: p.label, value: p.unit_cost, hint: formatQty(p.kg, 'KG') }))} />
          </ChartCard>
        </Col>
        <Col xs={24} xl={12}>
          <ChartCard
            title={t('Müşteri sevkiyatı')}
            subtitle={t('Son 30 gün, satış tutarına göre')}
            table={{
              columns: [
                { key: 'customer', title: t('Müşteri') },
                { key: 'qty', title: t('Miktar'), align: 'right' },
                { key: 'amount', title: t('Tutar'), align: 'right' },
              ],
              rows: data.shipments.map((s) => ({ key: s.customer, customer: s.customer, qty: shipmentQty(s), amount: formatMoney(s.amount) })),
            }}
          >
            <HBars
              items={data.shipments.map((s) => ({
                label: s.customer,
                value: Number(s.amount),
                text: formatMoney(s.amount),
                hint: shipmentQty(s),
              }))}
            />
          </ChartCard>
        </Col>
        <Col xs={24} xl={12}>
          <ChartCard title={t('Açık alarmlar')} subtitle={t('{c} kritik · {w} uyarı', { c: alarms.data?.open_critical ?? 0, w: alarms.data?.open_warning ?? 0 })}>
            {alarms.data && alarms.data.latest.length > 0 ? (
              <ul className="alarm-mini">
                {alarms.data.latest.map((a) => (
                  <li key={a.id}>
                    <SeverityIcon severity={a.severity} />
                    <span>
                      <strong>{ALERT_KIND[a.kind]}</strong>
                      <span className="muted"> · {formatDateTime(a.created_at)}</span>
                      <br />
                      <span className="alarm-mini-text">{a.message}</span>
                    </span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="muted">{t('Açık alarm yok.')}</p>
            )}
            <Button type="link" style={{ paddingInline: 0 }} onClick={() => navigate('/alarmlar')}>
              {t('Alarm merkezine git')}
            </Button>
          </ChartCard>
        </Col>
      </Row>
    </>
  )
}
