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

export function DifferenceTag({ difference }: { difference: string }) {
  const sign = compare(difference, '0')
  if (sign === 0) return <Tag color="green">Tutuyor</Tag>
  if (sign < 0) return <Tag color="red">{formatQty(difference.replace('-', ''))} eksik</Tag>
  return <Tag color="orange">{formatQty(difference)} fazla</Tag>
}

function CountResult({ count, onNew }: { count: StockCount; onNew: () => void }) {
  const short = count.lines.filter((line) => compare(line.difference, '0') < 0).length
  return (
    <>
      <Result
        status={short || count.surplus_lines ? 'warning' : 'success'}
        title={`Sayım kaydedildi: ${count.count_no}`}
        subTitle={
          short || count.surplus_lines
            ? `${short} lotta eksik (fire yazıldı, maliyeti ${formatMoney(count.shortage_value)}), ${count.surplus_lines} lotta fazla.`
            : 'Sayılan bütün lotlar defterle tutuyor.'
        }
        extra={[
          <Button key="print" type="primary" icon={<PrinterOutlined />} onClick={() => navigate(`/yazdir/sayim/${count.id}`)}>
            Sayım tutanağını yazdır
          </Button>,
          <Button key="new" onClick={onNew}>
            Yeni sayım
          </Button>,
        ]}
      />
      {count.surplus_lines > 0 && (
        <Alert
          type="warning"
          showIcon
          title="Fazla çıkan mal stoka eklenmedi"
          description="Kaynağı belli olmayan mal deftere girmez. Yanlış lota yazılmış satış ya da eksik girilmiş aktarma olabilir; araştırıp ilgili belgeyi düzeltin."
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
      <Page title="Sayım" back={{ to: '/sayim', label: 'Sayım' }}>
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
            { title: 'Ürün', dataIndex: 'product_name' },
            { title: 'Lot', dataIndex: 'lot_no' },
            { title: 'Defterde', align: 'right', render: (_, l) => formatQty(l.system_qty, l.base_unit) },
            { title: 'Sayılan', align: 'right', render: (_, l) => formatQty(l.counted_qty, l.base_unit) },
            { title: 'Fark', render: (_, l) => <DifferenceTag difference={l.difference} /> },
          ]}
        />
      </Page>
    )
  }

  return (
    <Page
      title="Sayım"
      description="Rafta saydığınız miktarı yazın. Saymadığınız lotları boş bırakın; onlar değişmez. Eksik çıkan mal fire olarak düşülür."
    >
      {(warehouses.isError || stock.isError) && <QueryError error={warehouses.error ?? stock.error} />}
      <Card style={{ marginBottom: 16 }}>
        <Space wrap size="large">
          <span>
            <label className="muted" htmlFor="sayim-yeri" style={{ display: 'block' }}>
              Sayılan yer
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
            Defterdeki miktarı gizle (kör sayım)
          </Checkbox>
        </Space>
      </Card>

      <Table<StockRow>
        rowKey="lot_no"
        loading={stock.isPending}
        dataSource={rows}
        pagination={false}
        scroll={{ x: 'max-content' }}
        locale={{ emptyText: 'Bu yerde stok yok.' }}
        columns={[
          { title: 'Ürün', dataIndex: 'product_name' },
          { title: 'Lot', dataIndex: 'lot_no' },
          { title: 'Son kullanma', dataIndex: 'expiry_date', render: formatDate, responsive: ['md'] },
          ...(blind
            ? []
            : [{ title: 'Defterde', align: 'right' as const, render: (_: unknown, row: StockRow) => formatQty(row.qty, row.base_unit) }]),
          {
            title: 'Sayılan',
            width: 170,
            render: (_, row) => (
              <Input
                inputMode="decimal"
                value={counted[row.lot_no] ?? ''}
                status={invalid.includes(row) ? 'error' : undefined}
                suffix={row.base_unit === 'ADET' ? 'adet' : 'kg'}
                placeholder="sayılmadı"
                aria-label={`${row.lot_no} sayılan miktar`}
                onChange={(e) => setCounted((current) => ({ ...current, [row.lot_no]: e.target.value }))}
              />
            ),
          },
          ...(blind
            ? []
            : [
                {
                  title: 'Fark',
                  render: (_: unknown, row: StockRow) => {
                    const value = parseUserDecimal(counted[row.lot_no] ?? '', 3)
                    if (value === null) return null
                    const sign = compare(value, row.qty)
                    return sign === 0 ? <Tag color="green">Tutuyor</Tag> : sign < 0 ? <Tag color="red">Eksik</Tag> : <Tag color="orange">Fazla</Tag>
                  },
                },
              ]),
        ]}
      />

      <Card style={{ marginTop: 16 }}>
        <Space orientation="vertical" style={{ width: '100%' }}>
          <Input placeholder="Not (isteğe bağlı), ör. Ay sonu sayımı" value={note} maxLength={255} onChange={(e) => setNote(e.target.value)} />
          {invalid.length > 0 && (
            <Typography.Text type="danger">
              {invalid.map((row) => row.lot_no).join(', ')}: miktar geçersiz{invalid.some((r) => r.base_unit === 'ADET') ? ' (adet tam sayı olmalı)' : ''}.
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
            Sayımı kaydet ({entered.length} lot)
          </Button>
        </Space>
      </Card>

      <div className="section-title">Önceki sayımlar</div>
      <Table<StockCount>
        rowKey="id"
        loading={history.isPending}
        dataSource={history.data}
        pagination={{ pageSize: 10, hideOnSinglePage: true }}
        scroll={{ x: 'max-content' }}
        locale={{ emptyText: 'Henüz sayım yapılmadı.' }}
        columns={[
          { title: 'Sayım', dataIndex: 'count_no' },
          { title: 'Tarih', dataIndex: 'created_at', render: formatDateTime },
          { title: 'Yer', dataIndex: 'warehouse_code' },
          { title: 'Sayan', dataIndex: 'counted_by' },
          { title: 'Lot', render: (_, c) => c.lines.length, align: 'right' },
          { title: 'Eksik maliyeti', dataIndex: 'shortage_value', render: formatMoney, align: 'right' },
          {
            title: '',
            render: (_, c) => (
              <Button size="small" icon={<PrinterOutlined />} onClick={() => navigate(`/yazdir/sayim/${c.id}`)}>
                Tutanak
              </Button>
            ),
          },
        ]}
      />
    </Page>
  )
}
