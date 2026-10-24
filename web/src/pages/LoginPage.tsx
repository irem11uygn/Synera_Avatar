import { Alert, Button, Card, Flex, Form, Input, Typography } from 'antd'
import { useEffect, useState } from 'react'
import { errorMessage } from '../api/client'

type Values = { username: string; password: string }

type Props = { onLogin: (username: string, password: string) => Promise<void>; notice: string | null }

export default function LoginPage({ onLogin, notice }: Props) {
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    document.title = 'Giriş — AVATAR'
  }, [])

  async function finish({ username, password }: Values) {
    setBusy(true)
    setError(null)
    try {
      await onLogin(username.trim(), password)
    } catch (caught) {
      setError(errorMessage(caught))
      setBusy(false)
    }
  }

  const shown = error ?? notice
  return (
    <Flex justify="center" align="flex-start" style={{ minHeight: '100vh', padding: '10vh 16px 16px' }}>
      <Card style={{ width: '100%', maxWidth: 380 }}>
        <Typography.Title level={1} style={{ marginTop: 0, fontSize: 28 }}>
          AVATAR
        </Typography.Title>
        <Typography.Paragraph type="secondary">Üretim, maliyet ve lot izlenebilirliği · Yönetici girişi</Typography.Paragraph>
        {shown && (
          <Alert type={error ? 'error' : 'info'} showIcon role="alert" title={shown} style={{ marginBottom: 16 }} />
        )}
        <Form<Values> layout="vertical" onFinish={finish} requiredMark={false}>
          <Form.Item
            label="Kullanıcı adı"
            name="username"
            rules={[{ required: true, whitespace: true, message: 'Kullanıcı adı gerekli.' }]}
          >
            <Input
              id="username"
              required
              autoComplete="username"
              autoCapitalize="off"
              autoCorrect="off"
              spellCheck={false}
              enterKeyHint="next"
            />
          </Form.Item>
          <Form.Item
            label="Parola"
            name="password"
            htmlFor="current-password"
            rules={[{ required: true, message: 'Parola gerekli.' }]}
          >
            <Input.Password id="current-password" required autoComplete="current-password" enterKeyHint="done" />
          </Form.Item>
          <Button type="primary" htmlType="submit" block loading={busy}>
            Giriş yap
          </Button>
        </Form>
        <Typography.Paragraph type="secondary" style={{ marginTop: 16, marginBottom: 0, fontSize: 12 }}>
          Örnek kullanıcılar README'de listelenir.
        </Typography.Paragraph>
      </Card>
    </Flex>
  )
}
