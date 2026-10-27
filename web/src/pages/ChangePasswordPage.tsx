import { Alert, App, Button, Card, Flex, Form, Input, Typography } from 'antd'
import { useState } from 'react'
import { api, errorMessage } from '../api/client'
import type { User } from '../api/types'
import { useSession } from '../auth/context'
import { Page } from '../components/Page'
import { navigate } from '../lib/router'
import { t } from '../lib/i18n'

type Values = { current_password: string; new_password: string; repeat: string }

const RULE = t('En az 8 karakter; harf ve rakam birlikte.')

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
      <Form.Item label={t('Şu anki şifre')} name="current_password" rules={[{ required: true, message: t('Şu anki şifreyi yazın.') }]}>
        <Input.Password autoComplete="current-password" />
      </Form.Item>
      <Form.Item
        label={t('Yeni şifre')}
        name="new_password"
        extra={RULE}
        rules={[
          { required: true, message: t('Yeni şifreyi yazın.') },
          { min: 8, message: RULE },
          { pattern: /^(?=.*[A-Za-zÇĞİÖŞÜçğıöşü])(?=.*\d).+$/, message: RULE },
        ]}
      >
        <Input.Password autoComplete="new-password" />
      </Form.Item>
      <Form.Item
        label={t('Yeni şifre (tekrar)')}
        name="repeat"
        dependencies={['new_password']}
        rules={[
          { required: true, message: t('Yeni şifreyi tekrar yazın.') },
          ({ getFieldValue }) => ({
            validator: (_, value) =>
              !value || value === getFieldValue('new_password')
                ? Promise.resolve()
                : Promise.reject(new Error(t('İki şifre aynı değil.'))),
          }),
        ]}
      >
        <Input.Password autoComplete="new-password" />
      </Form.Item>
      <Button type="primary" htmlType="submit" loading={busy} size="large">
        {t('Şifreyi değiştir')}
      </Button>
    </Form>
  )
}

/** Menüden açılan şifre değiştirme sayfası. */
export default function ChangePasswordPage() {
  const { message } = App.useApp()
  return (
    <Page title={t('Şifremi değiştir')} description={t('Diğer cihazlardaki oturumlarınız kapanır; bu oturum açık kalır.')}>
      <Card>
        <PasswordForm
          onDone={() => {
            message.success(t('Şifreniz değiştirildi.'))
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
          {t('Yeni şifrenizi belirleyin')}
        </Typography.Title>
        <Typography.Paragraph type="secondary">
          {t('Merhaba {name}. Hesabınız yeni açıldı ya da şifreniz sıfırlandı. Devam etmeden önce yalnız sizin bildiğiniz bir şifre belirleyin.', { name: user.full_name })}
        </Typography.Paragraph>
        <PasswordForm onDone={() => navigate('/')} />
        <Button type="link" onClick={() => void logout()} style={{ paddingInline: 0, marginTop: 12 }}>
          {t('Çıkış yap')}
        </Button>
      </Card>
    </Flex>
  )
}
