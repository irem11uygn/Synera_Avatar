// Cari kartları: tedarikçi, müşteri, dış üretici (FR-101, FR-301). Müşteri iletişim bilgileri
// geri çağırma listesinde kullanılır; şube → ana firma bağı ikinci kademe izleme içindir.

import { useQueryClient } from '@tanstack/react-query'
import { App, Button, Checkbox, Col, Form, Input, Row, Segmented, Select, Space, Table, Tag } from 'antd'
import type { TableColumnsType } from 'antd'
import { useState } from 'react'
import { api } from '../api/client'
import { refreshBusinessData, usePartners } from '../api/queries'
import type { Partner, PartnerInput } from '../api/types'
import { FormModal } from '../components/FormModal'
import { Page } from '../components/Page'
import { QueryError } from '../components/QueryError'
import { textOrNull } from '../lib/rules'
import { t } from '../lib/i18n'
import { sortable } from '../lib/sort'

type Role = 'supplier' | 'customer' | 'subcontractor'

const ROLE_LABEL: Record<Role, string> = { supplier: t('Tedarikçi'), customer: t('Müşteri'), subcontractor: t('Fasoncu') }

type FormValues = {
  code: string
  name: string
  roles: Role[]
  parent_id?: number
  contact_person?: string
  phone?: string
  email?: string
  address?: string
}

function rolesOf(partner: Partner): Role[] {
  const roles: Role[] = []
  if (partner.is_supplier) roles.push('supplier')
  if (partner.is_customer) roles.push('customer')
  if (partner.is_subcontractor) roles.push('subcontractor')
  return roles
}

function toInput(values: FormValues): PartnerInput {
  return {
    code: values.code.trim(),
    name: values.name.trim(),
    is_supplier: values.roles.includes('supplier'),
    is_customer: values.roles.includes('customer'),
    is_subcontractor: values.roles.includes('subcontractor'),
    parent_id: values.parent_id ?? null,
    contact_person: textOrNull(values.contact_person),
    phone: textOrNull(values.phone),
    email: textOrNull(values.email),
    address: textOrNull(values.address),
  }
}

function toFormValues(partner: Partner): FormValues {
  return {
    code: partner.code,
    name: partner.name,
    roles: rolesOf(partner),
    parent_id: partner.parent_id ?? undefined,
    contact_person: partner.contact_person ?? undefined,
    phone: partner.phone ?? undefined,
    email: partner.email ?? undefined,
    address: partner.address ?? undefined,
  }
}

export default function PartnersPage() {
  const { message } = App.useApp()
  const queryClient = useQueryClient()
  const partners = usePartners()
  const [role, setRole] = useState<Role | 'all'>('all')
  const [editing, setEditing] = useState<Partner | 'new' | null>(null)

  const byId = new Map(partners.data?.map((p) => [p.id, p]))
  const rows = role === 'all' ? partners.data : partners.data?.filter((p) => rolesOf(p).includes(role))

  async function save(values: FormValues) {
    const body = toInput(values)
    if (editing === 'new') await api<Partner>('/partners', { method: 'POST', body })
    else if (editing) await api<Partner>(`/partners/${editing.id}`, { method: 'PUT', body })
    await refreshBusinessData(queryClient)
    message.success(`${body.name} kaydedildi.`)
  }

  const columns: TableColumnsType<Partner> = [
    { title: t('Kod'), dataIndex: 'code' },
    {
      title: t('Ad'),
      dataIndex: 'name',
      render: (name: string, row) => {
        const parent = row.parent_id ? byId.get(row.parent_id) : undefined
        return parent ? t('{name} ({parent} şubesi)', { name, parent: parent.name }) : name
      },
    },
    {
      title: t('Rol'),
      key: 'roles',
      render: (_, row) => (
        <Space size={4} wrap>
          {rolesOf(row).map((r) => (
            <Tag key={r}>{ROLE_LABEL[r]}</Tag>
          ))}
        </Space>
      ),
    },
    { title: t('Yetkili'), dataIndex: 'contact_person', render: (v: string | null) => v ?? '—' },
    { title: t('Telefon'), dataIndex: 'phone', render: (v: string | null) => v ?? '—' },
    { title: 'E-posta', dataIndex: 'email', render: (v: string | null) => v ?? '—' },
    { title: t('Adres'), dataIndex: 'address', render: (v: string | null) => v ?? '—' },
    {
      title: '',
      key: 'actions',
      fixed: 'right',
      render: (_, row) => (
        <Button size="small" onClick={() => setEditing(row)}>
          {t('Düzenle')}
        </Button>
      ),
    },
  ]

  return (
    <Page
      title={t('Müşteri ve tedarikçiler')}
      description={t('Müşteri, tedarikçi ve fasoncu firmaların iletişim bilgileri. Geri çağırmada müşteriye bu bilgilerle ulaşılır.')}
      extra={
        <Button type="primary" onClick={() => setEditing('new')}>
          {t('Yeni firma')}
        </Button>
      }
    >
      {partners.isError && <QueryError error={partners.error} onRetry={() => partners.refetch()} />}
      <Segmented<Role | 'all'>
        value={role}
        onChange={setRole}
        options={[
          { value: 'all', label: t('Tümü') },
          { value: 'supplier', label: t('Tedarikçiler') },
          { value: 'customer', label: t('Müşteriler') },
          { value: 'subcontractor', label: t('Fasoncular') },
        ]}
        style={{ marginBottom: 16 }}
      />
      <Table<Partner>
        rowKey="id"
        size="middle"
        loading={partners.isPending}
        columns={sortable(columns)}
        dataSource={rows}
        pagination={false}
        scroll={{ x: 'max-content' }}
      />
      <FormModal<FormValues>
        title={editing === 'new' ? t('Yeni firma') : t('Firmayı düzenle: {code}', { code: editing?.code ?? '' })}
        open={editing !== null}
        onClose={() => setEditing(null)}
        initialValues={editing && editing !== 'new' ? toFormValues(editing) : { roles: [] }}
        onSubmit={save}
        width={640}
      >
        <Row gutter={16}>
          <Col xs={24} sm={8}>
            <Form.Item label={t('Kod')} name="code" rules={[{ required: true, whitespace: true, message: t('Kod gerekli.') }]}>
              <Input maxLength={30} autoComplete="off" spellCheck={false} />
            </Form.Item>
          </Col>
          <Col xs={24} sm={16}>
            <Form.Item label={t('Ad')} name="name" rules={[{ required: true, whitespace: true, message: t('Ad gerekli.') }]}>
              <Input maxLength={150} autoComplete="off" />
            </Form.Item>
          </Col>
          <Col span={24}>
            <Form.Item
              label={t('Rol')}
              name="roles"
              extra={t('Fasoncu seçilince ona ait bir fasoncu deposu otomatik açılır; gönderilen hammadde orada izlenir.')}
              rules={[{ required: true, type: 'array', min: 1, message: t('En az bir rol seçin.') }]}
            >
              <Checkbox.Group
                options={(Object.keys(ROLE_LABEL) as Role[]).map((r) => ({ value: r, label: ROLE_LABEL[r] }))}
              />
            </Form.Item>
          </Col>
          <Col span={24}>
            <Form.Item label={t('Ana firma (bu firma bir şubeyse)')} name="parent_id">
              <Select
                allowClear
                showSearch={{ optionFilterProp: 'label' }}
                options={partners.data
                  ?.filter((p) => editing === 'new' || p.id !== editing?.id)
                  .map((p) => ({ value: p.id, label: `${p.code} · ${p.name}` }))}
              />
            </Form.Item>
          </Col>
          <Col xs={24} sm={12}>
            <Form.Item label={t('Yetkili kişi')} name="contact_person">
              <Input maxLength={100} autoComplete="off" />
            </Form.Item>
          </Col>
          <Col xs={24} sm={12}>
            <Form.Item label={t('Telefon')} name="phone">
              <Input type="tel" maxLength={30} autoComplete="off" />
            </Form.Item>
          </Col>
          <Col span={24}>
            <Form.Item label="E-posta" name="email" rules={[{ type: 'email', message: t('Geçerli bir e-posta yazın.') }]}>
              <Input type="email" maxLength={120} autoComplete="off" spellCheck={false} />
            </Form.Item>
          </Col>
          <Col span={24}>
            <Form.Item label={t('Adres')} name="address">
              <Input.TextArea maxLength={255} rows={2} autoComplete="off" />
            </Form.Item>
          </Col>
        </Row>
      </FormModal>
    </Page>
  )
}
