// Son kullanma takibi: elimizdeki (ana depo ve araçlar) malın son kullanma tarihine göre listesi.
// Süresi geçen mal satılamaz; buradan doğrudan fire/imha kaydı girilir. Yaklaşanlar önce satılır.

import { DeleteOutlined, PrinterOutlined } from '@ant-design/icons'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Button, Form, Input, Radio, Space, Table, Tag, Typography } from 'antd'
import { useMemo, useState } from 'react'
import { api } from '../api/client'
import { refreshBusinessData, useStock, useWarehouses } from '../api/queries'
import type { StockRow } from '../api/types'
import { useSession } from '../auth/context'
import { FormModal } from '../components/FormModal'
import { Page } from '../components/Page'
import { QueryError } from '../components/QueryError'
import { daysLeft, formatDate, formatQty, todayIso } from '../lib/format'
import { LOT_STATUS } from '../lib/labels'
import { can } from '../lib/roles'
import { navigate } from '../lib/router'
import { decimalRule, fromApiDecimal, toApiDecimal } from '../lib/rules'
import { t } from '../lib/i18n'

export function ExpiryTag({ days }: { days: number }) {
  if (days < 0) return <Tag color="red">{t('{n} gün önce geçti', { n: -days })}</Tag>
  if (days === 0) return <Tag color="red">{t('Bugün son gün')}</Tag>
  if (days <= 3) return <Tag color="orange">{t('{n} gün kaldı', { n: days })}</Tag>
  return <Tag>{t('{n} gün kaldı', { n: days })}</Tag>
}

type Row = StockRow & { days: number }
type WasteValues = { qty: string; reason: string }

function WasteModal({ row, onClose }: { row: Row | null; onClose: () => void }) {
  const queryClient = useQueryClient()
  const mutation = useMutation({
    mutationFn: (values: WasteValues) =>
      api('/adjustments', {
        method: 'POST',
        body: {
          lot_no: row!.lot_no,
          warehouse_id: row!.warehouse_id,
          qty: toApiDecimal(values.qty, 3),
          reason: values.reason,
        },
      }),
    onSuccess: () => refreshBusinessData(queryClient),
  })
  if (!row) return null
  return (
    <FormModal<WasteValues>
      title={`Fire / imha: ${row.product_name}`}
      open
      onClose={onClose}
      initialValues={{
        qty: fromApiDecimal(row.qty),
        reason: row.days < 0 ? t('Son kullanma tarihi geçti — imha') : t('Bozuldu — imha'),
      }}
      onSubmit={(values) => mutation.mutateAsync(values)}
      okText={t('İmha kaydını gir')}
    >
      <Typography.Paragraph>
        Lot <b>{row.lot_no}</b>, {row.warehouse_name}. Stokta {formatQty(row.qty, row.base_unit)} var.
      </Typography.Paragraph>
      <Form.Item name="qty" label={t('İmha edilen miktar')} rules={[decimalRule(t('Miktar'), { maxFraction: 3, integer: row.base_unit === 'ADET' })]}>
        <Input inputMode="decimal" suffix={row.base_unit === 'ADET' ? 'adet' : 'kg'} />
      </Form.Item>
      <Form.Item name="reason" label={t('Neden')} rules={[{ required: true, message: t('Nedeni yazın.') }]}>
        <Input maxLength={255} />
      </Form.Item>
    </FormModal>
  )
}

export default function ExpiryPage() {
  const { user } = useSession()
  const today = todayIso()
  const [horizon, setHorizon] = useState(7)
  const [wasting, setWasting] = useState<Row | null>(null)
  const warehouses = useWarehouses()
  const stock = useStock()
  const rows = useMemo<Row[]>(() => {
    // Fasoncunun deposundaki hammadde üretimde tüketilir; burada elimizdeki mal listelenir.
    const own = new Set((warehouses.data ?? []).filter((w) => w.kind !== 'DIS_URETICI').map((w) => w.id))
    return (stock.data ?? [])
      .filter((row) => own.has(row.warehouse_id) && row.expiry_date)
      .map((row) => ({ ...row, days: daysLeft(row.expiry_date!, today) }))
      .filter((row) => row.days <= horizon)
      .sort((a, b) => a.days - b.days || a.lot_no.localeCompare(b.lot_no))
  }, [stock.data, warehouses.data, horizon, today])
  const expired = rows.filter((row) => row.days < 0).length

  return (
    <Page
      title={t('Son kullanma takibi')}
      description={t('Elimizdeki malın son kullanma tarihleri. Süresi geçen mal satılamaz: rafından ayırıp imha kaydı girin. Yaklaşanları önce satın.')}
    >
      {(stock.isError || warehouses.isError) && <QueryError error={stock.error ?? warehouses.error} onRetry={() => stock.refetch()} />}
      <Space wrap style={{ marginBottom: 16 }}>
        <Typography.Text>{t('Göster:')}</Typography.Text>
        <Radio.Group
          optionType="button"
          value={horizon}
          onChange={(e) => setHorizon(e.target.value)}
          options={[
            { value: 0, label: t('Süresi geçenler') },
            { value: 3, label: t('3 gün içinde') },
            { value: 7, label: t('7 gün içinde') },
            { value: 30, label: t('30 gün içinde') },
          ]}
        />
        {expired > 0 && <Tag color="red">{t('{n} lotun süresi geçmiş', { n: expired })}</Tag>}
      </Space>
      <Table<Row>
        rowKey={(row) => `${row.lot_no}-${row.warehouse_id}`}
        loading={stock.isPending}
        dataSource={rows}
        pagination={{ pageSize: 25, hideOnSinglePage: true }}
        scroll={{ x: 'max-content' }}
        locale={{ emptyText: horizon === 0 ? t('Süresi geçmiş mal yok.') : t('{n} gün içinde dolan mal yok.', { n: horizon }) }}
        columns={[
          { title: t('Durum'), render: (_, row) => <ExpiryTag days={row.days} /> },
          { title: t('Son kullanma'), dataIndex: 'expiry_date', render: formatDate },
          { title: t('Ürün'), dataIndex: 'product_name' },
          {
            title: t('Lot'),
            dataIndex: 'lot_no',
            render: (lotNo: string, row) => (
              <>
                <a href={`/lotlar/${lotNo}`} onClick={(e) => (e.preventDefault(), navigate(`/lotlar/${lotNo}`))}>
                  {lotNo}
                </a>
                {row.lot_status === 'BLOKE' && (
                  <Tag color="red" style={{ marginLeft: 6 }}>
                    {LOT_STATUS.BLOKE}
                  </Tag>
                )}
              </>
            ),
          },
          { title: t('Yer'), dataIndex: 'warehouse_name' },
          { title: t('Miktar'), align: 'right', render: (_, row) => formatQty(row.qty, row.base_unit) },
          {
            title: '',
            render: (_, row) => (
              <Space>
                {can(user.role, 'stock') && (
                  <Button size="small" danger={row.days < 0} icon={<DeleteOutlined />} onClick={() => setWasting(row)}>
                    {t('İmha')}
                  </Button>
                )}
                <Button size="small" icon={<PrinterOutlined />} onClick={() => navigate(`/yazdir/etiket/${row.lot_no}`)}>
                  {t('Etiket')}
                </Button>
              </Space>
            ),
          },
        ]}
      />
      <WasteModal row={wasting} onClose={() => setWasting(null)} />
    </Page>
  )
}
