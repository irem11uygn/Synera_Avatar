// Model A kartı (FR-502): emir açılırken kaydedilen tahmin, kabulden sonra gerçek ve sapma.
// Tahmin sonradan değişmez; sapma bu kayda göre hesaplanır.

import { Card, Col, Row, Tag, Typography } from 'antd'
import type { Forecast, Order } from '../api/types'
import { formatDateTime, formatMoney, formatPercent, formatQty } from '../lib/format'
import { Link } from './Link'
import { Stat } from './Stat'

function signed(value: string | null | undefined, format: (v: string) => string): string {
  if (value == null) return '—'
  return value.startsWith('-') ? format(value) : `+${format(value)}`
}

export function ForecastCard({ order }: { order: Order }) {
  const forecast: Forecast | null | undefined = order.forecast
  const unit = order.base_unit
  if (!forecast) {
    return (
      <Card size="small" title="Yapay zekâ tahmini (Model A)" style={{ marginBottom: 16 }}>
        <Typography.Text type="secondary">
          Bu emir için tahmin kaydı yok (model dosyası yoktu ya da emir yapay zekâ eklenmeden açıldı). İş akışı
          tahminsiz de çalışır.
        </Typography.Text>
      </Card>
    )
  }
  const done = order.received_qty != null
  return (
    <Card
      size="small"
      title="Yapay zekâ tahmini (Model A) — tahmin, gerçek, sapma"
      extra={<Link to="/yapay-zeka">Model değerlendirmesi</Link>}
      style={{ marginBottom: 16 }}
    >
      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} lg={6}>
          <Stat
            label="Beklenen miktar (tahmin)"
            value={formatQty(forecast.expected_qty, unit)}
            hint={`Et bazlı verim ${formatPercent(forecast.yield_main_pct)}`}
          />
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Stat
            label="Gerçekleşen"
            value={done ? formatQty(order.received_qty, unit) : 'Kabul bekleniyor'}
            hint={done ? `Sapma ${signed(forecast.qty_deviation, (v) => formatQty(v, unit))}` : undefined}
            tone="success"
          />
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Stat label="Tahmini birim maliyet" value={formatMoney(forecast.ekp)} hint="Hammadde değeri + hizmet × tahmini adet" />
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Stat
            label="Gerçek birim maliyet"
            value={done ? formatMoney(order.cost?.ekp_display) : '—'}
            hint={done ? `Sapma ${signed(forecast.ekp_deviation, formatMoney)}` : undefined}
            tone="success"
          />
        </Col>
      </Row>
      <Typography.Paragraph type="secondary" style={{ marginTop: 12, marginBottom: 0 }}>
        Referans yöntem (geçmiş ortalama verim): {formatQty(forecast.baseline_qty, unit)} · birim maliyet{' '}
        {formatMoney(forecast.baseline_ekp)}
        {done && forecast.baseline_qty_deviation != null && (
          <> · referans sapması {signed(forecast.baseline_qty_deviation, (v) => formatQty(v, unit))}</>
        )}
        . <Tag>{forecast.model_version}</Tag> {formatDateTime(forecast.created_at)} tarihinde, emir açılırken kaydedildi.
      </Typography.Paragraph>
    </Card>
  )
}
