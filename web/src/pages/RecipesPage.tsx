// Parçalama reçeteleri (FR-201, FR-202): giriş ürünü, çıkış kalemleri, standart oranlar (referans
// yöntem), değer katsayıları (değer ağırlıklı dağıtım için) ve tartım toleransı.

import { useQuery, useQueryClient } from '@tanstack/react-query'
import { App, Button, Col, Form, Input, Row, Select, Switch, Table, Tag, Typography, type TableColumnsType } from 'antd'
import { useState } from 'react'
import { api } from '../api/client'
import { refreshBusinessData, useProducts } from '../api/queries'
import type { AllocationMethod, Recipe, RecipeInput, RecipeLineType, Species } from '../api/types'
import { FormModal } from '../components/FormModal'
import { Page } from '../components/Page'
import { QueryError } from '../components/QueryError'
import { compare, divide, multiply, parseUserDecimal, sum } from '../lib/decimal'
import { formatDecimal, formatQty, formatUnitCost } from '../lib/format'
import { ALLOCATION_METHOD, options, RECIPE_LINE_TYPE, SPECIES } from '../lib/labels'
import { decimalRule, toApiDecimal } from '../lib/rules'

type RecipeLine = Recipe['lines'][number]

type LineValues = {
  line_type: RecipeLineType
  product_id?: number
  percent?: string
  value_per_kg?: string
  bears_cost: boolean
}
type FormValues = {
  code: string
  name: string
  input_product_id: number
  species: Species
  default_method: AllocationMethod
  tolerance_kg: string
  lines: LineValues[]
}

const percentOf = (ratio: string) => `%${formatDecimal(multiply(ratio, '100', 2), 0, 2)}`

const LINE_COLUMNS: TableColumnsType<RecipeLine> = [
  { title: 'Sıra', dataIndex: 'sort_order', width: 60 },
  { title: 'Tür', dataIndex: 'line_type', render: (t: RecipeLineType) => RECIPE_LINE_TYPE[t] },
  { title: 'Ürün', key: 'product', render: (_, line) => (line.product_name ? `${line.product_code} · ${line.product_name}` : '—') },
  { title: 'Standart oran', dataIndex: 'standard_ratio', align: 'right', render: percentOf },
  {
    title: 'Değer katsayısı',
    dataIndex: 'value_per_kg',
    align: 'right',
    render: (v: string | null) => (v ? `${formatUnitCost(v)}/kg` : '—'),
  },
  {
    title: 'Maliyet taşır',
    dataIndex: 'bears_cost',
    render: (bears: boolean) => (bears ? <Tag color="blue">Evet</Tag> : <Tag>Hayır</Tag>),
  },
]

const COLUMNS: TableColumnsType<Recipe> = [
  { title: 'Kod', dataIndex: 'code' },
  { title: 'Ad', dataIndex: 'name' },
  { title: 'Giriş ürünü', dataIndex: 'input_product_name' },
  { title: 'Tür', dataIndex: 'species', render: (s: Species) => SPECIES[s] },
  { title: 'Varsayılan yöntem', dataIndex: 'default_method', render: (m: AllocationMethod) => ALLOCATION_METHOD[m] },
  { title: 'Tolerans', dataIndex: 'tolerance_kg', align: 'right', render: (v: string) => formatQty(v, 'KG') },
  { title: 'Kalem', key: 'lines', align: 'right', render: (_, r) => r.lines.length },
]

function toInput(values: FormValues): RecipeInput {
  return {
    code: values.code.trim(),
    name: values.name.trim(),
    input_product_id: values.input_product_id,
    species: values.species,
    default_method: values.default_method,
    tolerance_kg: toApiDecimal(values.tolerance_kg, 3)!,
    lines: values.lines.map((line) => {
      const fire = line.line_type === 'FIRE'
      return {
        line_type: line.line_type,
        product_id: fire ? null : (line.product_id ?? null),
        standard_ratio: divide(toApiDecimal(line.percent, 2)!, '100', 4),
        value_per_kg: toApiDecimal(line.value_per_kg, 4),
        bears_cost: !fire && line.bears_cost,
      }
    }),
  }
}

const NEW_RECIPE: Partial<FormValues> = {
  species: 'KUZU',
  default_method: 'DEGER',
  tolerance_kg: '0.2',
  lines: [
    { line_type: 'PARCA', bears_cost: true },
    { line_type: 'FIRE', bears_cost: false },
  ],
}

export default function RecipesPage() {
  const { message } = App.useApp()
  const queryClient = useQueryClient()
  const recipes = useQuery({ queryKey: ['recipes'], queryFn: () => api<Recipe[]>('/cutting-recipes') })
  const [open, setOpen] = useState(false)

  async function save(values: FormValues) {
    const recipe = await api<Recipe>('/cutting-recipes', { method: 'POST', body: toInput(values) })
    await refreshBusinessData(queryClient)
    message.success(`${recipe.code} reçetesi kaydedildi.`)
  }

  return (
    <Page
      title="Parçalama reçeteleri"
      extra={
        <Button type="primary" onClick={() => setOpen(true)}>
          Yeni reçete
        </Button>
      }
    >
      {recipes.isError && <QueryError error={recipes.error} onRetry={() => recipes.refetch()} />}
      <Table<Recipe>
        rowKey="id"
        size="middle"
        loading={recipes.isPending}
        columns={COLUMNS}
        dataSource={recipes.data}
        pagination={false}
        scroll={{ x: 'max-content' }}
        expandable={{
          expandedRowRender: (recipe) => (
            <Table<RecipeLine>
              rowKey="id"
              size="small"
              columns={LINE_COLUMNS}
              dataSource={recipe.lines}
              pagination={false}
              scroll={{ x: 'max-content' }}
            />
          ),
        }}
      />
      <Typography.Paragraph type="secondary" style={{ marginTop: 12 }}>
        Standart oranlar, "beklenen kg" için referans yöntemdir (oran × giriş ağırlığı). Değer katsayıları değer
        ağırlıklı dağıtımda kullanılır: pay ∝ kg × €/kg. Fire stoka girmez ve maliyet almaz.
      </Typography.Paragraph>
      <FormModal<FormValues> title="Yeni reçete" open={open} onClose={() => setOpen(false)} initialValues={NEW_RECIPE} onSubmit={save} width={880}>
        <RecipeFields />
      </FormModal>
    </Page>
  )
}

function RecipeFields() {
  const form = Form.useFormInstance<FormValues>()
  const products = useProducts()
  const lines = Form.useWatch('lines', form) as LineValues[] | undefined
  const kgProducts = (products.data ?? []).filter((p) => p.base_unit === 'KG' && p.active)
  const percents = (lines ?? []).map((line) => parseUserDecimal(line?.percent ?? '', 2) ?? '0')
  const total = sum(percents, 2)

  return (
    <>
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
        <Col xs={24} sm={8}>
          <Form.Item label="Giriş ürünü" name="input_product_id" rules={[{ required: true, message: 'Giriş ürünü seçin.' }]}>
            <Select
              options={kgProducts.filter((p) => p.kind === 'HAMMADDE').map((p) => ({ value: p.id, label: `${p.code} · ${p.name}` }))}
            />
          </Form.Item>
        </Col>
        <Col xs={12} sm={5}>
          <Form.Item label="Hayvan" name="species" rules={[{ required: true }]}>
            <Select options={options(SPECIES)} />
          </Form.Item>
        </Col>
        <Col xs={12} sm={6}>
          <Form.Item label="Varsayılan yöntem" name="default_method" rules={[{ required: true }]}>
            <Select options={options(ALLOCATION_METHOD)} />
          </Form.Item>
        </Col>
        <Col xs={24} sm={5}>
          <Form.Item label="Tartım toleransı" name="tolerance_kg" rules={[decimalRule('Tolerans', { maxFraction: 3, allowZero: true })]}>
            <Input inputMode="decimal" autoComplete="off" suffix="kg" />
          </Form.Item>
        </Col>
      </Row>

      <Typography.Text strong>Çıkış kalemleri</Typography.Text>{' '}
      <Typography.Text type={compare(total, '100') === 0 ? 'success' : 'danger'} aria-live="polite">
        (oranlar toplamı %{formatDecimal(total, 0, 2)}; %100 olmalı)
      </Typography.Text>
      <Form.List
        name="lines"
        rules={[
          {
            validator: async (_rule, value: LineValues[] | undefined) => {
              const percentsNow = (value ?? []).map((line) => parseUserDecimal(line?.percent ?? '', 2) ?? '0')
              if (compare(sum(percentsNow, 2), '100') !== 0) throw new Error('Standart oranların toplamı %100 olmalı.')
            },
          },
        ]}
      >
        {(fields, { add, remove }, { errors }) => (
          <>
            {fields.map((field) => {
              const fire = lines?.[field.name]?.line_type === 'FIRE'
              return (
                <Row gutter={8} key={field.key} align="top" style={{ marginTop: 8 }}>
                  <Col xs={12} sm={4}>
                    <Form.Item label="Tür" name={[field.name, 'line_type']} rules={[{ required: true }]}>
                      <Select options={options(RECIPE_LINE_TYPE)} />
                    </Form.Item>
                  </Col>
                  <Col xs={12} sm={7}>
                    <Form.Item
                      label="Ürün"
                      name={[field.name, 'product_id']}
                      rules={[{ required: !fire, message: 'Ürün seçin.' }]}
                    >
                      <Select
                        disabled={fire}
                        allowClear
                        showSearch={{ optionFilterProp: 'label' }}
                        options={kgProducts
                          .filter((p) => p.kind === 'PARCA' || p.kind === 'YAN_URUN')
                          .map((p) => ({ value: p.id, label: `${p.code} · ${p.name}` }))}
                      />
                    </Form.Item>
                  </Col>
                  <Col xs={8} sm={4}>
                    <Form.Item label="Oran" name={[field.name, 'percent']} rules={[decimalRule('Oran', { maxFraction: 2, allowZero: true })]}>
                      <Input inputMode="decimal" autoComplete="off" suffix="%" />
                    </Form.Item>
                  </Col>
                  <Col xs={8} sm={4}>
                    <Form.Item
                      label="Değer"
                      name={[field.name, 'value_per_kg']}
                      rules={[decimalRule('Değer katsayısı', { maxFraction: 4, required: false, allowZero: true })]}
                    >
                      <Input inputMode="decimal" autoComplete="off" suffix="€/kg" disabled={fire} />
                    </Form.Item>
                  </Col>
                  <Col xs={5} sm={3}>
                    <Form.Item label="Maliyet" name={[field.name, 'bears_cost']} valuePropName="checked">
                      <Switch disabled={fire} aria-label="Maliyet taşır" />
                    </Form.Item>
                  </Col>
                  <Col xs={3} sm={2}>
                    <Form.Item label=" ">
                      <Button disabled={fields.length === 1} onClick={() => remove(field.name)}>
                        Sil
                      </Button>
                    </Form.Item>
                  </Col>
                </Row>
              )
            })}
            <Form.ErrorList errors={errors} />
            <Button size="small" onClick={() => add({ line_type: 'PARCA', bears_cost: true })}>
              Kalem ekle
            </Button>
          </>
        )}
      </Form.List>
    </>
  )
}
