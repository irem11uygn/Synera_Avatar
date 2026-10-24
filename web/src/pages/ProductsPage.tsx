// Ürün kartları (FR-101, FR-103): hammadde, mamul, parça. Adetle izlenen ürünün 1 adet ağırlığı
// (ör. Narin Sucuk 1 paket = 1 kg) burada tanımlanır.

import { useQueryClient } from '@tanstack/react-query'
import { App, Button, Col, Form, Input, Row, Segmented, Select, Switch, Table, Tag, type TableColumnsType } from 'antd'
import { useState } from 'react'
import { api } from '../api/client'
import { refreshBusinessData, useProducts } from '../api/queries'
import type { BaseUnit, Product, ProductInput, ProductKind } from '../api/types'
import { FormModal } from '../components/FormModal'
import { Page } from '../components/Page'
import { QueryError } from '../components/QueryError'
import { formatMoney, formatQty, formatUnitCost, unitLabel } from '../lib/format'
import { options, PRODUCT_KIND } from '../lib/labels'
import { decimalRule, fromApiDecimal, textOrNull, toApiDecimal } from '../lib/rules'

type FormValues = {
  code: string
  name: string
  kind: ProductKind
  base_unit: BaseUnit
  unit_weight_kg?: string
  lot_prefix?: string
  default_purchase_price?: string
  sale_price?: string
  shelf_life_days?: string
  active: boolean
}

const UNIT_OPTIONS: { value: BaseUnit; label: string }[] = [
  { value: 'KG', label: 'kg' },
  { value: 'ADET', label: 'adet / paket' },
]

function toInput(values: FormValues): ProductInput {
  return {
    code: values.code.trim(),
    name: values.name.trim(),
    kind: values.kind,
    base_unit: values.base_unit,
    unit_weight_kg: toApiDecimal(values.unit_weight_kg, 3),
    lot_prefix: textOrNull(values.lot_prefix),
    default_purchase_price: toApiDecimal(values.default_purchase_price, 4),
    sale_price: toApiDecimal(values.sale_price, 2),
    shelf_life_days: values.shelf_life_days?.trim() ? Number(values.shelf_life_days) : null,
    active: values.active,
  }
}

function toFormValues(product: Product): FormValues {
  return {
    code: product.code,
    name: product.name,
    kind: product.kind,
    base_unit: product.base_unit,
    unit_weight_kg: fromApiDecimal(product.unit_weight_kg),
    lot_prefix: product.lot_prefix ?? undefined,
    default_purchase_price: fromApiDecimal(product.default_purchase_price),
    sale_price: fromApiDecimal(product.sale_price),
    shelf_life_days: product.shelf_life_days == null ? undefined : String(product.shelf_life_days),
    active: product.active ?? true,
  }
}

const NEW_PRODUCT: Partial<FormValues> = { kind: 'HAMMADDE', base_unit: 'KG', active: true }

export default function ProductsPage() {
  const { message } = App.useApp()
  const queryClient = useQueryClient()
  const products = useProducts()
  const [kind, setKind] = useState<ProductKind | 'ALL'>('ALL')
  const [editing, setEditing] = useState<Product | 'new' | null>(null)

  async function save(values: FormValues) {
    const body = toInput(values)
    if (editing === 'new') await api<Product>('/products', { method: 'POST', body })
    else if (editing) await api<Product>(`/products/${editing.id}`, { method: 'PUT', body })
    await refreshBusinessData(queryClient)
    message.success(`${body.name} kaydedildi.`)
  }

  const columns: TableColumnsType<Product> = [
    { title: 'Kod', dataIndex: 'code' },
    { title: 'Ad', dataIndex: 'name' },
    { title: 'Tür', dataIndex: 'kind', render: (value: ProductKind) => PRODUCT_KIND[value] },
    {
      title: 'Birim',
      dataIndex: 'base_unit',
      render: (unit: BaseUnit, row) =>
        unit === 'ADET' && row.unit_weight_kg ? `adet (1 adet = ${formatQty(row.unit_weight_kg, 'KG')})` : unitLabel(unit),
    },
    { title: 'Lot öneki', dataIndex: 'lot_prefix', render: (value: string | null) => value ?? '—' },
    {
      title: 'Varsayılan alış fiyatı',
      dataIndex: 'default_purchase_price',
      align: 'right',
      render: (value: string | null) => formatUnitCost(value),
    },
    { title: 'Satış fiyatı (VKP)', dataIndex: 'sale_price', align: 'right', render: formatMoney },
    {
      title: 'Raf ömrü',
      dataIndex: 'shelf_life_days',
      align: 'right',
      render: (value: number | null) => (value == null ? '—' : `${value} gün`),
    },
    {
      title: 'Durum',
      dataIndex: 'active',
      render: (active: boolean) => (active ? <Tag color="green">Aktif</Tag> : <Tag>Pasif</Tag>),
    },
    {
      title: '',
      key: 'actions',
      fixed: 'right',
      render: (_, row) => (
        <Button size="small" onClick={() => setEditing(row)}>
          Düzenle
        </Button>
      ),
    },
  ]

  const rows = kind === 'ALL' ? products.data : products.data?.filter((p) => p.kind === kind)

  return (
    <Page
      title="Ürünler"
      extra={
        <Button type="primary" onClick={() => setEditing('new')}>
          Yeni ürün
        </Button>
      }
    >
      {products.isError && <QueryError error={products.error} onRetry={() => products.refetch()} />}
      <Segmented<ProductKind | 'ALL'>
        value={kind}
        onChange={setKind}
        options={[{ value: 'ALL', label: 'Tümü' }, ...options(PRODUCT_KIND)]}
        style={{ marginBottom: 16 }}
      />
      <Table<Product>
        rowKey="id"
        size="middle"
        loading={products.isPending}
        columns={columns}
        dataSource={rows}
        pagination={false}
        scroll={{ x: 'max-content' }}
      />
      <FormModal<FormValues>
        title={editing === 'new' ? 'Yeni ürün' : `Ürünü düzenle: ${editing?.code ?? ''}`}
        open={editing !== null}
        onClose={() => setEditing(null)}
        initialValues={editing && editing !== 'new' ? toFormValues(editing) : NEW_PRODUCT}
        onSubmit={save}
        width={640}
      >
        <ProductFields />
      </FormModal>
    </Page>
  )
}

function ProductFields() {
  const form = Form.useFormInstance<FormValues>()
  const unit = Form.useWatch('base_unit', form)
  return (
    <Row gutter={16}>
      <Col xs={24} sm={8}>
        <Form.Item label="Kod" name="code" rules={[{ required: true, whitespace: true, message: 'Kod gerekli.' }]}>
          <Input maxLength={30} autoComplete="off" spellCheck={false} />
        </Form.Item>
      </Col>
      <Col xs={24} sm={16}>
        <Form.Item label="Ad" name="name" rules={[{ required: true, whitespace: true, message: 'Ad gerekli.' }]}>
          <Input maxLength={100} autoComplete="off" />
        </Form.Item>
      </Col>
      <Col xs={24} sm={12}>
        <Form.Item label="Tür" name="kind" rules={[{ required: true }]}>
          <Select options={options(PRODUCT_KIND)} />
        </Form.Item>
      </Col>
      <Col xs={24} sm={12}>
        <Form.Item label="Ölçü birimi" name="base_unit" rules={[{ required: true }]}>
          <Select options={UNIT_OPTIONS} />
        </Form.Item>
      </Col>
      <Col xs={24} sm={12}>
        <Form.Item
          label="1 adedin ağırlığı"
          name="unit_weight_kg"
          extra="Adetle izlenen üründe zorunlu (ör. 1 paket = 1 kg)."
          dependencies={['base_unit']}
          rules={[decimalRule('Ağırlık', { maxFraction: 3, required: unit === 'ADET' })]}
        >
          <Input inputMode="decimal" autoComplete="off" suffix="kg" />
        </Form.Item>
      </Col>
      <Col xs={24} sm={12}>
        <Form.Item label="Lot öneki" name="lot_prefix" extra="Üretimde açılan lot numarasının başı (ör. SUC).">
          <Input maxLength={10} autoComplete="off" spellCheck={false} />
        </Form.Item>
      </Col>
      <Col xs={24} sm={12}>
        <Form.Item
          label="Varsayılan alış fiyatı"
          name="default_purchase_price"
          rules={[decimalRule('Alış fiyatı', { maxFraction: 4, required: false, allowZero: true })]}
        >
          <Input inputMode="decimal" autoComplete="off" suffix="€" />
        </Form.Item>
      </Col>
      <Col xs={24} sm={12}>
        <Form.Item
          label="Satış fiyatı (VKP)"
          name="sale_price"
          rules={[decimalRule('Satış fiyatı', { maxFraction: 2, required: false, allowZero: true })]}
        >
          <Input inputMode="decimal" autoComplete="off" suffix="€" />
        </Form.Item>
      </Col>
      <Col xs={24} sm={12}>
        <Form.Item
          label="Raf ömrü"
          name="shelf_life_days"
          extra="Lotun son kullanma tarihi bu süreyle hesaplanır."
          rules={[decimalRule('Raf ömrü', { maxFraction: 0, integer: true, required: false, allowZero: true })]}
        >
          <Input inputMode="numeric" autoComplete="off" suffix="gün" />
        </Form.Item>
      </Col>
      <Col xs={24} sm={12}>
        <Form.Item label="Aktif" name="active" valuePropName="checked">
          <Switch />
        </Form.Item>
      </Col>
    </Row>
  )
}
