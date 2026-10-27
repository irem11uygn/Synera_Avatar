// Raporlar (FR-601…FR-607): tek ekran bütün raporları gösterir. Sütunlar ve biçimleri sunucudan
// gelir (rapor tanımı); süzgeçler raporun desteklediklerine göre açılır; CSV aynı süzgeçle iner.

import { useQuery } from '@tanstack/react-query'
import {
  Alert,
  App as AntApp,
  Button,
  Card,
  Col,
  DatePicker,
  Input,
  Row,
  Select,
  Space,
  Table,
  Tag,
  Typography,
  type TableColumnsType,
} from 'antd'
import { useState } from 'react'
import { api, errorMessage } from '../api/client'
import { useProducts } from '../api/queries'
import type { ColumnKind, Report, ReportCode, ReportInfo } from '../api/types'
import { Page } from '../components/Page'
import { QueryError } from '../components/QueryError'
import { downloadFile } from '../lib/download'
import { formatDate, formatDateTime, formatMoney, formatPercent, formatQty, formatUnitCost } from '../lib/format'
import {
  ALLOCATION_METHOD,
  CUTTING_STATUS,
  MOVEMENT_TYPE,
  ORDER_STATUS,
  RECALL_STATUS,
  SALE_CHANNEL,
} from '../lib/labels'
import { navigate } from '../lib/router'
import { t } from '../lib/i18n'

// Durum sütunlarında gelen kodların Türkçesi (hepsi tek sözlükte; kodlar çakışmıyor).
const STATUS_TEXT: Record<string, string> = {
  ...ORDER_STATUS,
  ...CUTTING_STATUS,
  ...MOVEMENT_TYPE,
  ...ALLOCATION_METHOD,
  ...SALE_CHANNEL,
  ...RECALL_STATUS,
  IMHA: t('İmha'),
  SERBEST: t('Serbest'),
  KAYITLI: t('Kesin (kayıtlı)'),
  KISMEN: t('Kısmen kayıtlı'),
  BILINMIYOR: t('Sonrası bilinmiyor'),
}

const REPORT_ICON: Record<ReportCode, string> = {
  purchases: t('Alış'),
  production: t('Üretim'),
  cuttings: t('Parçalama'),
  'lot-movements': t('Stok hareketi'),
  sales: t('Satış'),
  recalls: t('Kalite'),
  integrity: t('Denetim'),
}

type Value = string | number | boolean | null | undefined

function renderCell(kind: ColumnKind, value: Value) {
  if (value === null || value === undefined || value === '') return '—'
  const text = String(value)
  switch (kind) {
    case 'qty':
      return formatQty(text)
    case 'money':
      return formatMoney(text)
    case 'unit_cost':
      return formatUnitCost(text)
    case 'percent':
      return formatPercent(text)
    case 'date':
      return formatDate(text)
    case 'datetime':
      return formatDateTime(text)
    case 'bool':
      return value ? t('Evet') : t('Hayır')
    case 'status':
      return STATUS_TEXT[text] ?? text
    default:
      return text
  }
}

const NUMERIC: ColumnKind[] = ['qty', 'money', 'unit_cost', 'percent']

type Filters = { date_from?: string; date_to?: string; product_id?: number; lot_no?: string }

function ReportView({ code }: { code: ReportCode }) {
  const { message } = AntApp.useApp()
  const products = useProducts()
  const [draft, setDraft] = useState<Filters>({})
  const [filters, setFilters] = useState<Filters>({})
  const [downloading, setDownloading] = useState(false)
  const report = useQuery({
    queryKey: ['report', code, filters],
    queryFn: () => api<Report>(`/reports/${code}`, { query: filters }),
  })

  async function download() {
    setDownloading(true)
    try {
      await downloadFile(`/reports/${code}`, { ...filters, format: 'csv' }, `rapor_${code}.csv`)
    } catch (error) {
      message.error(errorMessage(error))
    } finally {
      setDownloading(false)
    }
  }

  const data = report.data
  const allowed = new Set(data?.filters ?? [])
  const columns: TableColumnsType<Record<string, Value>> = (data?.columns ?? []).map((column) => ({
    title: column.label,
    dataIndex: column.key,
    align: NUMERIC.includes(column.kind) ? 'right' : undefined,
    render: (value: Value) => renderCell(column.kind, value),
  }))
  const totals = data ? Object.entries(data.totals) : []

  return (
    <Page
      title={data?.title ?? t('Rapor')}
      back={{ to: '/raporlar', label: t('Raporlar') }}
      extra={
        <>
          <Button onClick={() => navigate('/raporlar')}>{t('Bütün raporlar')}</Button>
          <Button type="primary" onClick={download} loading={downloading} disabled={!data}>
            {t('CSV indir')}
          </Button>
        </>
      }
    >
      {data && <Typography.Paragraph type="secondary">{data.description}</Typography.Paragraph>}
      {allowed.size > 0 && (
        <Card size="small" style={{ marginBottom: 16 }}>
          <Space wrap>
            {allowed.has('date') && (
              <DatePicker.RangePicker
                format="DD.MM.YYYY"
                aria-label={t('Tarih aralığı')}
                onChange={(_, [from, to]) =>
                  setDraft((d) => ({
                    ...d,
                    date_from: from ? from.split('.').reverse().join('-') : undefined,
                    date_to: to ? to.split('.').reverse().join('-') : undefined,
                  }))
                }
              />
            )}
            {allowed.has('product') && (
              <Select
                allowClear
                showSearch
                optionFilterProp="label"
                placeholder={t('Ürün')}
                aria-label={t('Ürün')}
                style={{ minWidth: 200 }}
                options={(products.data ?? []).map((p) => ({ value: p.id, label: p.name }))}
                onChange={(product_id?: number) => setDraft((d) => ({ ...d, product_id }))}
              />
            )}
            {allowed.has('lot') && (
              <Input
                allowClear
                placeholder={t('Lot (ör. SUC-2026-045)')}
                aria-label={t('Lot')}
                style={{ width: 200 }}
                onChange={(e) => setDraft((d) => ({ ...d, lot_no: e.target.value || undefined }))}
              />
            )}
            <Button onClick={() => setFilters(draft)}>{t('Süz')}</Button>
          </Space>
        </Card>
      )}
      {report.isError && <QueryError error={report.error} onRetry={() => report.refetch()} />}
      {data?.notes.map((note) => (
        <Alert key={note} type="info" showIcon title={note} style={{ marginBottom: 12 }} />
      ))}
      <Card size="small">
        <Table<Record<string, Value>>
          rowKey="__row"
          size="small"
          loading={report.isPending}
          columns={columns}
          dataSource={data?.rows.map((row, index) => ({ ...row, __row: index }))}
          pagination={{ pageSize: 50, hideOnSinglePage: true }}
          scroll={{ x: 'max-content' }}
          locale={{ emptyText: t('Bu süzgeçlerle kayıt yok.') }}
          summary={() =>
            totals.length === 0 || !data ? null : (
              <Table.Summary.Row>
                {data.columns.map((column, index) => {
                  const total = data.totals[column.key]
                  return (
                    <Table.Summary.Cell key={column.key} index={index} align={NUMERIC.includes(column.kind) ? 'right' : undefined}>
                      {index === 0 ? <strong>{t('Toplam')}</strong> : total != null ? <strong>{renderCell(column.kind, total)}</strong> : null}
                    </Table.Summary.Cell>
                  )
                })}
              </Table.Summary.Row>
            )
          }
        />
      </Card>
    </Page>
  )
}

function ReportList() {
  const reports = useQuery({ queryKey: ['reports'], queryFn: () => api<ReportInfo[]>('/reports') })
  return (
    <Page
      title={t('Raporlar')}
      description={t("Bir rapor seçin; ekranda görün, Excel'de açmak için CSV olarak indirin.")}
    >
      {reports.isError && <QueryError error={reports.error} onRetry={() => reports.refetch()} />}
      <Row gutter={[16, 16]}>
        {(reports.data ?? []).map((report) => (
          <Col key={report.code} xs={24} md={12} xl={8}>
            <button
              type="button"
              className="stat"
              style={{ minHeight: 132 }}
              onClick={() => navigate(`/raporlar/${report.code}`)}
            >
              <Tag color="blue">{REPORT_ICON[report.code]}</Tag>
              <div className="stat-value" style={{ fontSize: 19 }}>
                {report.title}
              </div>
              <div className="stat-hint">{report.description}</div>
            </button>
          </Col>
        ))}
      </Row>
    </Page>
  )
}

export default function ReportsPage({ code }: { code?: ReportCode }) {
  return code ? <ReportView key={code} code={code} /> : <ReportList />
}
