// Elle çizilmiş SVG grafikler (ek kütüphane yok). Sayılar API'den metin gelir; yalnız çizim için
// sayıya çevrilir, ekrandaki her değer metinden biçimlenir (ADR-006).
// Kurallar: ince çizgiler (2 px), çubuk ≤ 24 px, 4 px yuvarlak uç, açık ızgara, her grafikte
// fareyle değer kutusu, yanında "Tablo" görünümü; renk tek başına bilgi taşımaz (etiket + gösterge).

import { Segmented, Table } from 'antd'
import { useEffect, useRef, useState, type ReactNode } from 'react'
import { formatDate, formatDecimal } from '../lib/format'
import { t } from '../lib/i18n'
import { tiltHandlers } from './Tilt'

const num = (value: string | number | null | undefined) => (value == null ? 0 : Number(value))

function useWidth<T extends HTMLElement>(fallback = 600) {
  const ref = useRef<T>(null)
  const [width, setWidth] = useState(fallback)
  useEffect(() => {
    const el = ref.current
    if (!el) return
    const observer = new ResizeObserver(([entry]) => setWidth(Math.max(240, Math.floor(entry.contentRect.width))))
    observer.observe(el)
    return () => observer.disconnect()
  }, [])
  return [ref, width] as const
}

// --- Kart: başlık, açıklama, Grafik / Tablo seçimi -----------------------------------------

type TableRow = Record<string, ReactNode> & { key: string }

export function ChartCard({
  title,
  subtitle,
  children,
  table,
  extra,
}: {
  title: string
  subtitle?: ReactNode
  children: ReactNode
  /** Aynı veri tablo olarak (erişilebilirlik ve kesin değerler için). */
  table?: { columns: { key: string; title: string; align?: 'right' }[]; rows: TableRow[] }
  extra?: ReactNode
}) {
  const [view, setView] = useState<'chart' | 'table'>('chart')
  return (
    <section className="chart-card glass tilt" {...tiltHandlers(2)}>
      <header className="chart-card-head">
        <div>
          <h3 className="chart-card-title">{title}</h3>
          {subtitle && <div className="chart-card-sub">{subtitle}</div>}
        </div>
        <div className="chart-card-tools">
          {extra}
          {table && (
            <Segmented
              size="small"
              value={view}
              onChange={(value) => setView(value as 'chart' | 'table')}
              options={[
                { value: 'chart', label: t('Grafik') },
                { value: 'table', label: t('Tablo') },
              ]}
            />
          )}
        </div>
      </header>
      {view === 'chart' || !table ? (
        children
      ) : (
        <Table<TableRow>
          size="small"
          pagination={false}
          rowKey="key"
          dataSource={table.rows}
          scroll={{ x: 'max-content' }}
          columns={table.columns.map((c) => ({ key: c.key, dataIndex: c.key, title: c.title, align: c.align }))}
        />
      )}
    </section>
  )
}

function Tooltip({ x, y, children, width }: { x: number; y: number; children: ReactNode; width: number }) {
  const left = Math.min(Math.max(x + 12, 4), width - 200)
  return (
    <div className="chart-tooltip" style={{ left, top: Math.max(y - 10, 0) }} role="status">
      {children}
    </div>
  )
}

function Legend({ items }: { items: { label: string; color: string; dashed?: boolean }[] }) {
  return (
    <ul className="chart-legend">
      {items.map((item) => (
        <li key={item.label}>
          <svg width="22" height="10" aria-hidden="true">
            <line
              x1="1"
              y1="5"
              x2="21"
              y2="5"
              stroke={item.color}
              strokeWidth="2.5"
              strokeLinecap="round"
              strokeDasharray={item.dashed ? '5 4' : undefined}
            />
          </svg>
          {item.label}
        </li>
      ))}
    </ul>
  )
}

// --- Çizgi: gerçek ve model tahmini (kesikli) ------------------------------------------------

export type LinePoint = { label: string; day: string; actual: string; forecast?: string | null }

export function ActualForecastLine({
  points,
  unit,
  actualLabel,
  forecastLabel,
  height = 240,
}: {
  points: LinePoint[]
  unit: string
  actualLabel: string
  forecastLabel: string
  height?: number
}) {
  const [ref, width] = useWidth<HTMLDivElement>()
  const [hover, setHover] = useState<number | null>(null)
  const pad = { top: 16, right: 56, bottom: 28, left: 52 }
  const values = points.flatMap((p) => [num(p.actual), ...(p.forecast ? [num(p.forecast)] : [])])
  const min = Math.min(...values)
  const max = Math.max(...values)
  const span = max - min || 1
  const lo = min - span * 0.15
  const hi = max + span * 0.15
  const innerW = width - pad.left - pad.right
  const innerH = height - pad.top - pad.bottom
  const x = (i: number) => pad.left + (points.length === 1 ? innerW / 2 : (i / (points.length - 1)) * innerW)
  const y = (v: number) => pad.top + (1 - (v - lo) / (hi - lo)) * innerH
  const path = (pick: (p: LinePoint) => string | null | undefined) =>
    points
      .map((p, i) => [i, pick(p)] as const)
      .filter(([, v]) => v != null)
      .map(([i, v], k) => `${k === 0 ? 'M' : 'L'}${x(i).toFixed(1)},${y(num(v)).toFixed(1)}`)
      .join(' ')
  const ticks = [0, 1, 2, 3].map((k) => lo + ((hi - lo) * k) / 3)
  const last = points.length - 1
  const lastForecast = [...points].reverse().find((p) => p.forecast)
  const xLabels = points.length > 2 ? [0, Math.floor(last / 2), last] : points.map((_, i) => i)
  const showDots = points.length <= 24
  const band = points.length > 1 ? innerW / (points.length - 1) : innerW

  if (points.length === 0) return <p className="muted">{t('Gösterilecek kayıt yok.')}</p>
  return (
    <div ref={ref} className="chart-area" onPointerLeave={() => setHover(null)}>
      <Legend
        items={[
          { label: actualLabel, color: 'var(--series-1)' },
          { label: forecastLabel, color: 'var(--series-2)', dashed: true },
        ]}
      />
      <svg width={width} height={height} role="img" aria-label={`${actualLabel} / ${forecastLabel}`}>
        {ticks.map((v) => (
          <g key={v}>
            <line x1={pad.left} x2={width - pad.right} y1={y(v)} y2={y(v)} stroke="var(--grid)" strokeWidth="1" />
            <text x={pad.left - 8} y={y(v) + 4} textAnchor="end" className="chart-axis">
              {formatDecimal(v.toFixed(2), 2, 2)}
            </text>
          </g>
        ))}
        {xLabels.map((i) => (
          <text key={i} x={x(i)} y={height - 8} textAnchor={i === 0 && points.length > 1 ? 'start' : i === last && points.length > 1 ? 'end' : 'middle'} className="chart-axis">
            {formatDate(points[i].day)}
          </text>
        ))}
        {hover != null && (
          <line x1={x(hover)} x2={x(hover)} y1={pad.top} y2={pad.top + innerH} stroke="var(--ink-3)" strokeWidth="1" />
        )}
        <path d={path((p) => p.forecast)} fill="none" stroke="var(--series-2)" strokeWidth="2" strokeDasharray="6 5" strokeLinecap="round" />
        <path d={path((p) => p.actual)} fill="none" stroke="var(--series-1)" strokeWidth="2" strokeLinejoin="round" strokeLinecap="round" className="chart-draw" />
        {points.map((p, i) =>
          showDots || hover === i ? (
            <circle key={p.label} cx={x(i)} cy={y(num(p.actual))} r={hover === i ? 5.5 : 4} fill="var(--series-1)" stroke="#fff" strokeWidth="2" />
          ) : null,
        )}
        {/* Seçili doğrudan etiketler: yalnız son noktalar */}
        <text x={x(last) + 8} y={y(num(points[last].actual)) + 4} className="chart-direct">
          {formatDecimal(points[last].actual, 2, 2)}
        </text>
        {lastForecast && Math.abs(y(num(lastForecast.forecast)) - y(num(points[last].actual))) > 14 && (
          <text x={x(points.lastIndexOf(lastForecast)) + 8} y={y(num(lastForecast.forecast)) + 4} className="chart-direct is-muted">
            {formatDecimal(lastForecast.forecast!, 2, 2)}
          </text>
        )}
        {points.map((p, i) => (
          <rect
            key={`hit-${p.label}`}
            x={x(i) - band / 2}
            y={pad.top}
            width={Math.max(band, 12)}
            height={innerH}
            fill="transparent"
            onPointerEnter={() => setHover(i)}
          />
        ))}
      </svg>
      {hover != null && (
        <Tooltip x={x(hover)} y={y(num(points[hover].actual))} width={width}>
          <strong>{points[hover].label}</strong> · {formatDate(points[hover].day)}
          <br />
          {actualLabel}: {formatDecimal(points[hover].actual, 2, 2)} {unit}
          {points[hover].forecast && (
            <>
              <br />
              {forecastLabel}: {formatDecimal(points[hover].forecast!, 2, 2)} {unit}
              <br />
              {t('Fark')}: {formatDecimal((num(points[hover].actual) - num(points[hover].forecast)).toFixed(2), 2, 2)} {unit}
            </>
          )}
        </Tooltip>
      )}
    </div>
  )
}

// --- Yarım daire gösterge: hedef / gerçekleşen ------------------------------------------------

export function Gauge({ percent, caption }: { percent: string | null; caption: ReactNode }) {
  const value = percent == null ? 0 : Math.max(0, num(percent))
  const shown = Math.min(value, 100)
  const r = 80
  const cx = 100
  const cy = 96
  const arc = (to: number) => {
    const angle = Math.PI * (1 - to / 100)
    return `M${cx - r},${cy} A${r},${r} 0 0 1 ${(cx + r * Math.cos(angle)).toFixed(2)},${(cy - r * Math.sin(angle)).toFixed(2)}`
  }
  return (
    <div className="gauge">
      <svg viewBox="0 0 200 112" role="img" aria-label={percent == null ? t('Veri yok') : `%${percent}`}>
        <path d={arc(100)} fill="none" stroke="var(--grid)" strokeWidth="16" strokeLinecap="round" />
        {shown > 0 && (
          <path d={arc(shown)} fill="none" stroke="var(--series-1)" strokeWidth="16" strokeLinecap="round" pathLength={100} className="gauge-fill" />
        )}
      </svg>
      <div className="gauge-value">{percent == null ? '—' : `%${formatDecimal(percent, 0, 1)}`}</div>
      <div className="gauge-caption">{caption}</div>
    </div>
  )
}

// --- Halka: maliyet kalemleri ----------------------------------------------------------------

const SERIES = ['var(--series-1)', 'var(--series-2)', 'var(--series-3)', 'var(--series-4)']

export function Donut({
  slices,
  center,
  centerHint,
  unit = '€',
}: {
  slices: { label: string; value: string }[]
  center: ReactNode
  centerHint: ReactNode
  unit?: string
}) {
  const [hover, setHover] = useState<number | null>(null)
  // 4'ten fazla kalem "Diğer"de toplanır: renkler hiçbir zaman döngüyle tekrarlanmaz.
  const sorted = [...slices].sort((a, b) => num(b.value) - num(a.value))
  const shown =
    sorted.length <= 4
      ? sorted
      : [...sorted.slice(0, 3), { label: t('Diğer'), value: sorted.slice(3).reduce((s, x) => s + num(x.value), 0).toFixed(2) }]
  const total = shown.reduce((s, x) => s + num(x.value), 0) || 1
  const r = 70
  const c = 2 * Math.PI * r
  const lengths = shown.map((slice) => (num(slice.value) / total) * c)
  const starts = lengths.map((_, i) => lengths.slice(0, i).reduce((s, x) => s + x, 0))
  return (
    <div className="donut">
      <div className="donut-figure">
        <svg viewBox="0 0 180 180" role="img" aria-label={shown.map((s) => `${s.label} ${s.value} ${unit}`).join(', ')}>
          <g transform="rotate(-90 90 90)">
            {shown.map((slice, i) => (
              <circle
                key={slice.label}
                cx="90"
                cy="90"
                r={r}
                fill="none"
                stroke={SERIES[i]}
                strokeWidth={hover === i ? 24 : 20}
                strokeDasharray={`${Math.max(lengths[i] - 2, 0)} ${c}`} // 2 px yüzey boşluğu
                strokeDashoffset={-starts[i]}
                onPointerEnter={() => setHover(i)}
                onPointerLeave={() => setHover(null)}
                className="donut-slice"
              />
            ))}
          </g>
        </svg>
        <div className="donut-center">
          <div className="donut-center-value">{center}</div>
          <div className="donut-center-hint">{centerHint}</div>
        </div>
      </div>
      <ul className="donut-legend">
        {shown.map((slice, i) => (
          <li key={slice.label} className={hover === i ? 'is-active' : undefined} onPointerEnter={() => setHover(i)} onPointerLeave={() => setHover(null)}>
            <span className="swatch" style={{ background: SERIES[i] }} aria-hidden="true" />
            <span className="donut-legend-label">{slice.label}</span>
            <span className="num">
              {formatDecimal(slice.value, 2, 2)} {unit}
            </span>
            <span className="num muted">%{formatDecimal(((num(slice.value) / total) * 100).toFixed(1), 0, 1)}</span>
          </li>
        ))}
      </ul>
    </div>
  )
}

// --- İzometrik 3B sütunlar ---------------------------------------------------------------------

export function IsoColumns({
  items,
  unit,
  height = 230,
}: {
  items: { label: string; value: string; hint?: string }[]
  unit: string
  height?: number
}) {
  const [ref, width] = useWidth<HTMLDivElement>()
  const [hover, setHover] = useState<number | null>(null)
  if (items.length === 0) return <p className="muted">{t('Gösterilecek kayıt yok.')}</p>
  const max = Math.max(...items.map((i) => num(i.value))) || 1
  const top = 34
  const base = height - 44
  const slot = (width - 24) / items.length
  const w = Math.min(46, slot * 0.46)
  const dx = w * 0.5 // derinlik (30°)
  const dy = w * 0.29
  return (
    <div ref={ref} className="chart-area" onPointerLeave={() => setHover(null)}>
      <svg width={width} height={height} role="img" aria-label={items.map((i) => `${i.label} ${i.value} ${unit}`).join(', ')}>
        <defs>
          <linearGradient id="iso-front" x1="0" x2="0" y1="0" y2="1">
            <stop offset="0" stopColor="#14b8a6" />
            <stop offset="1" stopColor="#0d9488" />
          </linearGradient>
        </defs>
        <line x1="8" x2={width - 8} y1={base} y2={base} stroke="var(--grid)" strokeWidth="1" />
        {items.map((item, i) => {
          const h = Math.max(4, (num(item.value) / max) * (base - top))
          const x = 12 + slot * i + (slot - w - dx) / 2
          const yTop = base - h
          const active = hover === i
          return (
            <g key={item.label} onPointerEnter={() => setHover(i)} opacity={hover == null || active ? 1 : 0.55}>
              <g className="iso-prism" style={{ animationDelay: `${i * 70}ms` }}>
              {/* zemin gölgesi */}
              <path d={`M${x},${base} L${x + w},${base} L${x + w + dx},${base - dy} L${x + dx},${base - dy} Z`} fill="rgb(15 118 110 / 12%)" />
              {/* yan yüz */}
              <path d={`M${x + w},${yTop} L${x + w + dx},${yTop - dy} L${x + w + dx},${base - dy} L${x + w},${base} Z`} fill="#0b7d72" />
              {/* ön yüz */}
              <rect x={x} y={yTop} width={w} height={h} fill="url(#iso-front)" />
              {/* üst yüz */}
              <path d={`M${x},${yTop} L${x + dx},${yTop - dy} L${x + w + dx},${yTop - dy} L${x + w},${yTop} Z`} fill="#5eead4" />
              </g>
              <text x={x + (w + dx) / 2} y={yTop - dy - 6} textAnchor="middle" className="chart-direct">
                {formatDecimal(item.value, 2, 2)}
              </text>
              <text x={x + (w + dx) / 2} y={base + 18} textAnchor="middle" className="chart-axis">
                {item.label.length > 14 ? `${item.label.slice(0, 13)}…` : item.label}
              </text>
              <rect x={x - 6} y={top - 20} width={w + dx + 12} height={base - top + 44} fill="transparent" />
            </g>
          )
        })}
      </svg>
      {hover != null && (
        <Tooltip x={12 + slot * hover + slot / 2} y={top} width={width}>
          <strong>{items[hover].label}</strong>
          <br />
          {formatDecimal(items[hover].value, 2, 2)} {unit}
          {items[hover].hint && (
            <>
              <br />
              {items[hover].hint}
            </>
          )}
        </Tooltip>
      )}
    </div>
  )
}

// --- Yatay çubuklar ----------------------------------------------------------------------------

export function HBars({ items }: { items: { label: string; value: number; text: string; hint?: string }[] }) {
  if (items.length === 0) return <p className="muted">{t('Gösterilecek kayıt yok.')}</p>
  const max = Math.max(...items.map((i) => i.value)) || 1
  return (
    <ul className="hbars">
      {items.map((item, i) => (
        <li key={item.label} title={item.hint ? `${item.label}: ${item.text} · ${item.hint}` : `${item.label}: ${item.text}`}>
          <span className="hbars-label">{item.label}</span>
          <span className="hbars-track">
            <span className="hbars-fill" style={{ width: `${(item.value / max) * 100}%`, animationDelay: `${i * 60}ms` }} />
          </span>
          <span className="hbars-value num">{item.text}</span>
        </li>
      ))}
    </ul>
  )
}
