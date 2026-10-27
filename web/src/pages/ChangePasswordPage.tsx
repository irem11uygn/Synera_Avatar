import { Alert, App, Button, Card, Flex, Form, Input, Typography } from 'antd'
import { useState } from 'react'
import { api, errorMessage } from '../api/client'
import type { User } from '../api/types'
import { useSession } from '../auth/context'
import { Page } from '../components/Page'
import { navigate } from '../lib/router'

type Values = { current_password: string; new_password: string; repeat: string }

const RULE = 'En az 8 karakter; harf ve rakam birlikte.'

function PasswordForm({ onDone }: { onDone: () => void }) {
  const { setUser } = useSession()
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  async function finish(values: Values) {
    setBusy(true)
    setError(null)
    try {
      const user = await api<User>('/auth/change-password', {
        method: 'POST',
        body: { current_password: values.current_password, new_password: values.new_password },
      })
      setUser(user)
      onDone()
    } catch (caught) {
      setError(errorMessage(caught))
    } finally {
      setBusy(false)
    }
  }

  return (
    <Form<Values> layout="vertical" onFinish={finish} requiredMark={false} style={{ maxWidth: 420 }}>
      {error && <Alert type="error" showIcon role="alert" title={error} style={{ marginBottom: 16 }} />}
      <Form.Item label="Şu anki şifre" name="current_password" rules={[{ required: true, message: 'Şu anki şifreyi yazın.' }]}>
        <Input.Password autoComplete="current-password" />
      </Form.Item>
      <Form.Item
        label="Yeni şifre"
        name="new_password"
        extra={RULE}
        rules={[
          { required: true, message: 'Yeni şifreyi yazın.' },
          { min: 8, message: RULE },
          { pattern: /^(?=.*[A-Za-zÇĞİÖŞÜçğıöşü])(?=.*\d).+$/, message: RULE },
        ]}
      >
        <Input.Password autoComplete="new-password" />
      </Form.Item>
      <Form.Item
        label="Yeni şifre (tekrar)"
        name="repeat"
        dependencies={['new_password']}
        rules={[
          { required: true, message: 'Yeni şifreyi tekrar yazın.' },
          ({ getFieldValue }) => ({
            validator: (_, value) =>
              !value || value === getFieldValue('new_password')
                ? Promise.resolve()
                : Promise.reject(new Error('İki şifre aynı değil.')),
          }),
        ]}
      >
        <Input.Password autoComplete="new-password" />
      </Form.Item>
      <Button type="primary" htmlType="submit" loading={busy} size="large">
        Şifreyi değiştir
      </Button>
    </Form>
  )
}

/** Menüden açılan şifre değiştirme sayfası. */
export default function ChangePasswordPage() {
  const { message } = App.useApp()
  return (
    <Page title="Şifremi değiştir" description="Diğer cihazlardaki oturumlarınız kapanır; bu oturum açık kalır.">
      <Card>
        <PasswordForm
          onDone={() => {
            message.success('Şifreniz değiştirildi.')
            navigate('/')
          }}
        />
      </Card>
    </Page>
  )
}

/** Yönetici şifreyi sıfırladıktan sonraki ilk giriş: yeni şifre belirlenmeden devam edilemez. */
export function ForcedPasswordChange() {
  const { user, logout } = useSession()
  return (
    <Flex justify="center" style={{ minHeight: '100vh', padding: '8vh 16px 16px' }}>
      <Card style={{ width: '100%', maxWidth: 480, alignSelf: 'flex-start' }}>
        <Typography.Title level={2} style={{ marginTop: 0 }}>
          Yeni şifrenizi belirleyin
        </Typography.Title>
        <Typography.Paragraph type="secondary">
          Merhaba {user.full_name}. Hesabınız yeni açıldı ya da şifreniz sıfırlandı. Devam etmeden önce yalnız sizin
          bildiğiniz bir şifre belirleyin.
        </Typography.Paragraph>
        <PasswordForm onDone={() => navigate('/')} />
        <Button type="link" onClick={() => void logout()} style={{ paddingInline: 0, marginTop: 12 }}>
          Çıkış yap
        </Button>
      </Card>
    </Flex>
  )
}
