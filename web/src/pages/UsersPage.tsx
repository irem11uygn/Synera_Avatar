// Kullanıcı yönetimi (yalnız yönetici): hesap aç, rol ver, pasifleştir, şifre sıfırla.
// Yeni hesap ve sıfırlanan şifre geçicidir: kullanıcı ilk girişte kendi şifresini belirler.

import { PlusOutlined } from '@ant-design/icons'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { App, Button, Form, Input, Select, Space, Switch, Table, Tag, Typography } from 'antd'
import { useState } from 'react'
import { api } from '../api/client'
import { useWarehouses } from '../api/queries'
import type { UserAdmin, UserCreateInput, UserRole, UserUpdateInput } from '../api/types'
import { useSession } from '../auth/context'
import { FormModal } from '../components/FormModal'
import { Page } from '../components/Page'
import { QueryError } from '../components/QueryError'
import { ROLE, ROLE_HELP } from '../lib/roles'

const ROLE_OPTIONS = (Object.keys(ROLE) as UserRole[]).map((role) => ({
  value: role,
  label: (
    <div>
      <div>{ROLE[role]}</div>
      <div className="muted" style={{ fontSize: 12, whiteSpace: 'normal' }}>
        {ROLE_HELP[role]}
      </div>
    </div>
  ),
  title: ROLE[role],
}))

type EditValues = UserUpdateInput & { username?: string; password?: string }

function VanField() {
  const warehouses = useWarehouses()
  const role = Form.useWatch('role')
  if (role !== 'SATIS') return null
  return (
    <Form.Item name="warehouse_id" label="Aracı" rules={[{ required: true, message: 'Satış elemanının aracını seçin.' }]}>
      <Select
        options={(warehouses.data ?? []).filter((w) => w.kind === 'ARAC').map((w) => ({ value: w.id, label: w.name }))}
      />
    </Form.Item>
  )
}

export default function UsersPage() {
  const { user: me } = useSession()
  const { modal } = App.useApp()
  const queryClient = useQueryClient()
  const users = useQuery({ queryKey: ['users'], queryFn: () => api<UserAdmin[]>('/users') })
  const [editing, setEditing] = useState<UserAdmin | 'new' | null>(null)

  const refresh = () => queryClient.invalidateQueries({ queryKey: ['users'] })

  const save = useMutation({
    mutationFn: (values: EditValues) =>
      editing === 'new'
        ? api('/users', { method: 'POST', body: values as UserCreateInput })
        : api(`/users/${(editing as UserAdmin).id}`, {
            method: 'PUT',
            body: {
              full_name: values.full_name,
              role: values.role,
              active: values.active,
              warehouse_id: values.role === 'SATIS' ? values.warehouse_id : null,
            },
          }),
    onSuccess: refresh,
  })

  function reset(user: UserAdmin) {
    modal.confirm({
      title: `${user.full_name} için yeni geçici şifre verilsin mi?`,
      content: 'Kullanıcının açık oturumları kapanır; ilk girişte kendi şifresini belirler.',
      okText: 'Geçici şifre ver',
      cancelText: 'Vazgeç',
      onOk: async () => {
        const result = await api<{ temporary_password: string }>(`/users/${user.id}/reset-password`, {
          method: 'POST',
          body: {},
        })
        await refresh()
        modal.success({
          title: 'Geçici şifre',
          content: (
            <>
              <Typography.Paragraph>
                {user.full_name} ({user.username}) için geçici şifre. Kullanıcıya iletin; bu pencere kapanınca bir daha
                gösterilmez.
              </Typography.Paragraph>
              <Typography.Text code copyable style={{ fontSize: 18 }}>
                {result.temporary_password}
              </Typography.Text>
            </>
          ),
        })
      },
    })
  }

  return (
    <Page
      title="Kullanıcılar"
      description="Her çalışan kendi hesabıyla girer ve yalnız kendi işinin ekranlarını görür. İşten ayrılanı silmeyin, pasifleştirin: geçmiş kayıtlarda adı kalır."
      extra={
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setEditing('new')}>
          Yeni kullanıcı
        </Button>
      }
    >
      {users.isError && <QueryError error={users.error} onRetry={() => users.refetch()} />}
      <Table<UserAdmin>
        rowKey="id"
        loading={users.isPending}
        dataSource={users.data}
        pagination={false}
        scroll={{ x: 'max-content' }}
        columns={[
          {
            title: 'Ad soyad',
            dataIndex: 'full_name',
            render: (name: string, user) => (
              <>
                {name}
                {user.id === me.id && <Tag style={{ marginLeft: 6 }}>Siz</Tag>}
                <div className="muted">{user.username}</div>
              </>
            ),
          },
          { title: 'Rol', dataIndex: 'role', render: (role: UserRole) => ROLE[role] },
          { title: 'Araç', dataIndex: 'warehouse_code', render: (code: string | null) => code ?? '—', responsive: ['md'] },
          {
            title: 'Durum',
            render: (_, user) =>
              !user.active ? (
                <Tag>Pasif</Tag>
              ) : user.must_change_password ? (
                <Tag color="orange">İlk girişte şifre belirleyecek</Tag>
              ) : (
                <Tag color="green">Aktif</Tag>
              ),
          },
          {
            title: '',
            render: (_, user) => (
              <Space>
                <Button size="small" onClick={() => setEditing(user)}>
                  Düzenle
                </Button>
                <Button size="small" onClick={() => reset(user)}>
                  Şifre sıfırla
                </Button>
              </Space>
            ),
          },
        ]}
      />

      <FormModal<EditValues>
        title={editing === 'new' ? 'Yeni kullanıcı' : `Düzenle: ${editing ? editing.full_name : ''}`}
        open={editing !== null}
        onClose={() => setEditing(null)}
        initialValues={
          editing && editing !== 'new'
            ? { full_name: editing.full_name, role: editing.role, active: editing.active, warehouse_id: editing.warehouse_id }
            : { role: 'DEPO', active: true }
        }
        onSubmit={(values) => save.mutateAsync(values)}
      >
        {editing === 'new' && (
          <Form.Item
            name="username"
            label="Kullanıcı adı"
            extra="Küçük harf, rakam, nokta; ör. ayse.demir"
            rules={[
              { required: true, message: 'Kullanıcı adını yazın.' },
              { pattern: /^[a-z0-9._]{3,50}$/, message: 'Yalnız küçük harf (Türkçe karakter yok), rakam, nokta ve alt çizgi; en az 3 karakter.' },
            ]}
          >
            <Input autoComplete="off" autoCapitalize="off" />
          </Form.Item>
        )}
        <Form.Item name="full_name" label="Ad soyad" rules={[{ required: true, message: 'Adı yazın.' }]}>
          <Input maxLength={100} />
        </Form.Item>
        <Form.Item name="role" label="Görevi" rules={[{ required: true }]}>
          <Select options={ROLE_OPTIONS} optionLabelProp="title" />
        </Form.Item>
        <VanField />
        {editing === 'new' ? (
          <Form.Item
            name="password"
            label="Geçici şifre"
            extra="En az 8 karakter, harf ve rakam. Kullanıcı ilk girişte değiştirir."
            rules={[
              { required: true, message: 'Geçici şifre yazın.' },
              { min: 8, message: 'En az 8 karakter.' },
              { pattern: /^(?=.*[A-Za-zÇĞİÖŞÜçğıöşü])(?=.*\d).+$/, message: 'Harf ve rakam birlikte olmalı.' },
            ]}
          >
            <Input.Password autoComplete="new-password" />
          </Form.Item>
        ) : (
          <Form.Item name="active" label="Hesap açık" valuePropName="checked">
            <Switch />
          </Form.Item>
        )}
      </FormModal>
    </Page>
  )
}
