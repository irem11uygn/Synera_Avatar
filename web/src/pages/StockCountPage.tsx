// Sayım: depoda ya da araçta sayılan miktarlar girilir. Eksik çıkan mal "Sayım farkı" firesiyle
// düşülür; fazla çıkan mal stoka eklenmez, raporlanır (kaynağı araştırılmalı).

import { PrinterOutlined } from '@ant-design/icons'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Alert, Button, Card, Checkbox, Input, Result, Select, Space, Table, Tag, Typography } from 'antd'
import { useState } from 'react'
import { api, errorMessage } from '../api/client'
import { refreshBusinessData, useStock, useWarehouses } from '../api/queries'
import type { StockCount, StockRow } from '../api/types'
import { Page } from '../components/Page'
import { QueryError } from '../components/QueryError'
import { compare, parseUserDecimal } from '../lib/decimal'
import { formatDate, formatDateTime, formatMoney, formatQty } from '../lib/format'
import { navigate } from '../lib/router'
import { t } from '../lib/i18n'

export function DifferenceTag({ difference }: { difference: string }) {
  const sign = compare(difference, '0')
  if (sign === 0) return <Tag color="green">{t('Tutuyor')}</Tag>
  if (sign < 0) return <Tag color="red">{formatQty(difference.replace('-', ''))} eksik</Tag>
  return <Tag color="orange">{formatQty(difference)} fazla</Tag>
}

function CountResult({ count, onNew }: { count: StockCount; onNew: () => void }) {
  const short = count.lines.filter((line) => compare(line.difference, '0') < 0).length
  return (
    <>
      <Result
        status={short || count.surplus_lines ? 'warning' : 'success'}
        title={t('Sayım kaydedildi: {no}', { no: count.count_no })}
        subTitle={
          short || count.surplus_lines
            ? t('{short} lotta eksik (fire yazıldı, maliyeti {cost}), {surplus} lotta fazla.', { short, cost: formatMoney(count.shortage_value), surplus: count.surplus_lines })
            : t('Sayılan bütün lotlar sistemle tutuyor.')
        }
        extra={[
          <Button key="print" type="primary" icon={<PrinterOutlined />} onClick={() => navigate(`/yazdir/sayim/${count.id}`)}>
            {t('Sayım tutanağını yazdır')}
          </Button>,
          <Button key="new" onClick={onNew}>
            {t('Yeni sayım')}
          </Button>,
        ]}
      />
      {count.surplus_lines > 0 && (
        <Alert
          type="warning"
          showIcon
          title={t('Fazla çıkan mal stoka eklenmedi')}
          description={t('Kaynağı belli olmayan mal stoka girmez. Yanlış lota yazılmış satış ya da eksik girilmiş aktarma olabilir; araştırıp ilgili belgeyi düzeltin.')}
          style={{ marginBottom: 16 }}
        />
      )}
    </>
  )
}

export default function StockCountPage() {
  const queryClient = useQueryClient()
  const warehouses = useWarehouses()
  const places = (warehouses.data ?? []).filter((w) => w.kind !== 'DIS_URETICI')
  const [warehouseId, setWarehouseId] = useState<number | undefined>()
  const chosen = warehouseId ?? places.find((w) => w.kind === 'ANA')?.id
  const stock = useStock({ warehouse_id: chosen }, chosen !== undefined)
  const history = useQuery({ queryKey: ['stock-counts'], queryFn: () => api<StockCount[]>('/stock-counts') })
  const [counted, setCounted] = useState<Record<string, string>>({})
  const [blind, setBlind] = useState(false)
  const [note, setNote] = useState('')
  const [result, setResult] = useState<StockCount | null>(null)

  const rows = stock.data ?? []
  const entered = rows.filter((row) => (counted[row.lot_no] ?? '').trim() !== '')
  const invalid = entered.filter(
    (row) => parseUserDecimal(counted[row.lot_no], row.base_unit === 'ADET' ? 0 : 3) === null,
  )

  const save = useMutation({
    mutationFn: () =>
      api<StockCount>('/stock-counts', {
        method: 'POST',
        body: {
          warehouse_id: chosen,
          note: note.trim() || null,
          lines: entered.map((row) => ({
            lot_no: row.lot_no,
            counted_qty: parseUserDecimal(counted[row.lot_no], 3),
          })),
        },
      }),
    onSuccess: async (count) => {
      setResult(count)
      setCounted({})
      setNote('')
      await refreshBusinessData(queryClient)
    },
  })

  if (result) {
    return (
      <Page title={t('Sayım')} back={{ to: '/sayim', label: t('Sayım') }}>
        <CountResult
          count={result}
          onNew={() => {
            setResult(null)
            save.reset()
          }}
        />
        <Table
          rowKey="lot_no"
          dataSource={result.lines}
          pagination={false}
          scroll={{ x: 'max-content' }}
          columns={[
            { title: t('Ürün'), dataIndex: 'product_name' },
            { title: t('Lot'), dataIndex: 'lot_no' },
            { title: t('Sistemde'), align: 'right', render: (_, l) => formatQty(l.system_qty, l.base_unit) },
            { title: t('Sayılan'), align: 'right', render: (_, l) => formatQty(l.counted_qty, l.base_unit) },
            { title: t('Fark'), render: (_, l) => <DifferenceTag difference={l.difference} /> },
          ]}
        />
      </Page>
    )
  }

  return (
    <Page
      title={t('Sayım')}
      description={t('Rafta saydığınız miktarı yazın. Saymadığınız lotları boş bırakın; onlar değişmez. Eksik çıkan mal fire olarak düşülür.')}
    >
      {(warehouses.isError || stock.isError) && <QueryError error={warehouses.error ?? stock.error} />}
      <Card style={{ marginBottom: 16 }}>
        <Space wrap size="large">
          <span>
            <label className="muted" htmlFor="sayim-yeri" style={{ display: 'block' }}>
              {t('Sayılan yer')}
            </label>
            <Select
              id="sayim-yeri"
              style={{ minWidth: 240 }}
              value={chosen}
              onChange={(value: number) => {
                setWarehouseId(value)
                setCounted({})
              }}
              options={places.map((w) => ({ value: w.id, label: w.name }))}
            />
          </span>
          <Checkbox checked={blind} onChange={(e) => setBlind(e.target.checked)}>
            {t('Sistemdeki miktarı gizle (kör sayım)')}
          </Checkbox>
        </Space>
      </Card>

      <Table<StockRow>
        rowKey="lot_no"
        loading={stock.isPending}
        dataSource={rows}
        pagination={false}
        scroll={{ x: 'max-content' }}
        locale={{ emptyText: t('Bu yerde stok yok.') }}
        columns={[
          { title: t('Ürün'), dataIndex: 'product_name' },
          { title: t('Lot'), dataIndex: 'lot_no' },
          { title: t('Son kullanma'), dataIndex: 'expiry_date', render: formatDate, responsive: ['md'] },
          ...(blind
            ? []
            : [{ title: t('Sistemde'), align: 'right' as const, render: (_: unknown, row: StockRow) => formatQty(row.qty, row.base_unit) }]),
          {
            title: t('Sayılan'),
            width: 170,
            render: (_, row) => (
              <Input
                inputMode="decimal"
                value={counted[row.lot_no] ?? ''}
                status={invalid.includes(row) ? 'error' : undefined}
                suffix={row.base_unit === 'ADET' ? 'adet' : 'kg'}
                placeholder={t('sayılmadı')}
                aria-label={t('{lot} sayılan miktar', { lot: row.lot_no })}
                onChange={(e) => setCounted((current) => ({ ...current, [row.lot_no]: e.target.value }))}
              />
            ),
          },
          ...(blind
            ? []
            : [
                {
                  title: t('Fark'),
                  render: (_: unknown, row: StockRow) => {
                    const value = parseUserDecimal(counted[row.lot_no] ?? '', 3)
                    if (value === null) return null
                    const sign = compare(value, row.qty)
                    return sign === 0 ? <Tag color="green">{t('Tutuyor')}</Tag> : sign < 0 ? <Tag color="red">{t('Eksik')}</Tag> : <Tag color="orange">{t('Fazla')}</Tag>
                  },
                },
              ]),
        ]}
      />

      <Card style={{ marginTop: 16 }}>
        <Space orientation="vertical" style={{ width: '100%' }}>
          <Input placeholder={t('Not (isteğe bağlı), ör. Ay sonu sayımı')} value={note} maxLength={255} onChange={(e) => setNote(e.target.value)} />
          {invalid.length > 0 && (
            <Typography.Text type="danger">
              {t('{lots}: miktar geçersiz.', { lots: invalid.map((row) => row.lot_no).join(', ') })}
              {invalid.some((r) => r.base_unit === 'ADET') ? ` ${t('Adet tam sayı olmalı.')}` : ''}
            </Typography.Text>
          )}
          {save.isError && <Alert type="error" showIcon title={errorMessage(save.error)} />}
          <Button
            type="primary"
            size="large"
            disabled={entered.length === 0 || invalid.length > 0}
            loading={save.isPending}
            onClick={() => save.mutate()}
          >
            {t('Sayımı kaydet ({n} lot)', { n: entered.length })}
          </Button>
        </Space>
      </Card>

      <div className="section-title">{t('Önceki sayımlar')}</div>
      <Table<StockCount>
        rowKey="id"
        loading={history.isPending}
        dataSource={history.data}
        pagination={{ pageSize: 10, hideOnSinglePage: true }}
        scroll={{ x: 'max-content' }}
        locale={{ emptyText: t('Henüz sayım yapılmadı.') }}
        columns={[
          { title: t('Sayım'), dataIndex: 'count_no' },
          { title: t('Tarih'), dataIndex: 'created_at', render: formatDateTime },
          { title: t('Yer'), dataIndex: 'warehouse_code' },
          { title: t('Sayan'), dataIndex: 'counted_by' },
          { title: t('Lot'), render: (_, c) => c.lines.length, align: 'right' },
          { title: t('Eksik maliyeti'), dataIndex: 'shortage_value', render: formatMoney, align: 'right' },
          {
            title: '',
            render: (_, c) => (
              <Button size="small" icon={<PrinterOutlined />} onClick={() => navigate(`/yazdir/sayim/${c.id}`)}>
                {t('Tutanak')}
              </Button>
            ),
          },
        ]}
      />
    </Page>
  )
}
