// Yeni parçalama (FR-203): reçete, ana depodaki giriş lotu ve parçalanacak ağırlık. Taslak açılır;
// deftere ancak tartım girilip onaylanınca yazılır.

import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Alert, App, Button, Card, Col, Descriptions, Flex, Form, Input, Row, Segmented, Select } from 'antd'
import { useState } from 'react'
import { api, errorMessage } from '../api/client'
import { refreshBusinessData, useStock, useWarehouses } from '../api/queries'
import type { AllocationMethod, Cutting, CuttingInput, Recipe, StockRow } from '../api/types'
import { Page } from '../components/Page'
import { compare, parseUserDecimal } from '../lib/decimal'
import { formatDate, formatQty, formatUnitCost } from '../lib/format'
import { ALLOCATION_METHOD, options, SPECIES } from '../lib/labels'
import { navigate } from '../lib/router'
import { decimalRule, fromApiDecimal, toApiDecimal } from '../lib/rules'

type FormValues = { recipe_id: number; input_lot_no: string; input_qty: string; method: AllocationMethod }

export default function CuttingNewPage() {
  const { message } = App.useApp()
  const queryClient = useQueryClient()
  const [form] = Form.useForm<FormValues>()
  const recipes = useQuery({ queryKey: ['recipes'], queryFn: () => api<Recipe[]>('/cutting-recipes') })
  const warehouses = useWarehouses()
  const mainId = warehouses.data?.find((w) => w.kind === 'ANA')?.id
  const recipeId = Form.useWatch('recipe_id', form)
  const lotNo = Form.useWatch('input_lot_no', form)
  const recipe = recipes.data?.find((r) => r.id === recipeId)
  const stock = useStock(
    { warehouse_id: mainId, product_id: recipe?.input_product_id },
    mainId !== undefined && recipe !== undefined,
  )
  const lots = (stock.data ?? []).filter((row) => row.lot_status === 'AKTIF')
  const chosenLot = lots.find((row) => row.lot_no === lotNo)
  const [error, setError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)

  function chooseRecipe(id: number) {
    const chosen = recipes.data?.find((r) => r.id === id)
    form.setFieldsValue({ input_lot_no: undefined, input_qty: undefined, method: chosen?.default_method })
  }

  function chooseLot(lot: string) {
    const row: StockRow | undefined = lots.find((item) => item.lot_no === lot)
    if (row) form.setFieldValue('input_qty', fromApiDecimal(row.qty))
  }

  async function finish(values: FormValues) {
    setSaving(true)
    setError(null)
    const body: CuttingInput = {
      recipe_id: values.recipe_id,
      input_lot_no: values.input_lot_no,
      input_qty: toApiDecimal(values.input_qty, 3)!,
      method: values.method,
    }
    try {
      const cutting = await api<Cutting>('/cuttings', { method: 'POST', body })
      await refreshBusinessData(queryClient)
      message.success(`${cutting.cutting_no} taslağı açıldı; şimdi parçaları tartın.`)
      navigate(`/parcalama/${cutting.id}`)
    } catch (caught) {
      setError(errorMessage(caught))
      setSaving(false)
    }
  }

  return (
    <Page title="Yeni parçalama" back={{ to: '/parcalama', label: 'Parçalama' }}>
      {error && <Alert type="error" showIcon role="alert" title={error} style={{ marginBottom: 16 }} />}
      <Form<FormValues> form={form} layout="vertical" onFinish={finish} validateTrigger="onBlur">
        <Card size="small" style={{ marginBottom: 16 }}>
          <Row gutter={16}>
            <Col xs={24} md={12}>
              <Form.Item label="Reçete" name="recipe_id" rules={[{ required: true, message: 'Reçete seçin.' }]}>
                <Select
                  loading={recipes.isPending}
                  onChange={chooseRecipe}
                  options={recipes.data?.map((r) => ({ value: r.id, label: `${r.code} · ${r.name}` }))}
                />
              </Form.Item>
            </Col>
            <Col xs={24} md={12}>
              <Form.Item label="Dağıtım yöntemi" name="method" rules={[{ required: true, message: 'Yöntem seçin.' }]}>
                <Segmented<AllocationMethod> options={options(ALLOCATION_METHOD)} />
              </Form.Item>
            </Col>
            <Col xs={24} md={12}>
              <Form.Item
                label="Giriş lotu (ana depo)"
                name="input_lot_no"
                rules={[{ required: true, message: 'Giriş lotu seçin.' }]}
                extra={recipe ? `${recipe.input_product_name} lotları` : 'Önce reçete seçin.'}
              >
                <Select
                  disabled={!recipe}
                  loading={stock.isFetching}
                  onChange={chooseLot}
                  notFoundContent="Ana depoda bu ürünün aktif lotu yok."
                  options={lots.map((row) => ({
                    value: row.lot_no,
                    label: `${row.lot_no} · ${formatQty(row.qty, row.base_unit)} · ${formatUnitCost(row.unit_cost)}/kg · SKT ${formatDate(row.expiry_date)}`,
                  }))}
                />
              </Form.Item>
            </Col>
            <Col xs={24} md={12}>
              <Form.Item
                label="Parçalanacak ağırlık"
                name="input_qty"
                dependencies={['input_lot_no']}
                rules={[
                  decimalRule('Ağırlık', { maxFraction: 3 }),
                  {
                    validator: async (_rule, value: string | undefined) => {
                      const qty = parseUserDecimal(value ?? '', 3)
                      if (chosenLot && qty && compare(qty, chosenLot.qty) > 0) {
                        throw new Error(`Ana depoda ${formatQty(chosenLot.qty, 'KG')} var.`)
                      }
                    },
                  },
                ]}
              >
                <Input inputMode="decimal" autoComplete="off" suffix="kg" />
              </Form.Item>
            </Col>
          </Row>
          {recipe && (
            <Descriptions
              size="small"
              column={{ xs: 1, sm: 3 }}
              items={[
                { key: 'species', label: 'Tür', children: SPECIES[recipe.species] },
                { key: 'tolerance', label: 'Tartım toleransı', children: formatQty(recipe.tolerance_kg, 'KG') },
                { key: 'lines', label: 'Çıkış kalemleri', children: recipe.lines.length },
              ]}
            />
          )}
        </Card>
        <Flex gap="small">
          <Button type="primary" htmlType="submit" loading={saving}>
            Taslağı aç
          </Button>
          <Button onClick={() => navigate('/parcalama')}>Vazgeç</Button>
        </Flex>
      </Form>
    </Page>
  )
}
