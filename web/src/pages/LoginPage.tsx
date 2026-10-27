import { Alert, Button, Form, Input, Typography } from 'antd'
import { useEffect, useState } from 'react'
import { errorMessage } from '../api/client'

type Values = { username: string; password: string }

type Props = { onLogin: (username: string, password: string) => Promise<void>; notice: string | null }

export default function LoginPage({ onLogin, notice }: Props) {
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    document.title = 'Giriş — Synera'
  }, [])

  async function finish({ username, password }: Values) {
    setBusy(true)
    setError(null)
    try {
      await onLogin(username.trim().toLowerCase(), password)
    } catch (caught) {
      setError(errorMessage(caught))
      setBusy(false)
    }
  }

  const shown = error ?? notice
  return (
    <div className="login">
      <div className="login-panel">
        <div className="login-brand">
          <span className="shell-brand-mark" aria-hidden="true">
            S
          </span>
          <span className="shell-brand-name">Synera</span>
        </div>
        <Typography.Title level={1} style={{ fontSize: 26, margin: '24px 0 4px' }}>
          Giriş yap
        </Typography.Title>
        <Typography.Paragraph type="secondary" style={{ marginBottom: 24 }}>
          Üretim, stok, satış ve lot izleme sistemi
        </Typography.Paragraph>
        {shown && (
          <Alert type={error ? 'error' : 'info'} showIcon role="alert" title={shown} style={{ marginBottom: 16 }} />
        )}
        <Form<Values> layout="vertical" onFinish={finish} requiredMark={false} size="large">
          <Form.Item
            label="Kullanıcı adı"
            name="username"
            rules={[{ required: true, whitespace: true, message: 'Kullanıcı adınızı yazın.' }]}
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
            label="Şifre"
            name="password"
            htmlFor="current-password"
            rules={[{ required: true, message: 'Şifrenizi yazın.' }]}
          >
            <Input.Password id="current-password" required autoComplete="current-password" enterKeyHint="done" />
          </Form.Item>
          <Button type="primary" htmlType="submit" block loading={busy}>
            Giriş yap
          </Button>
        </Form>
        <Typography.Paragraph type="secondary" style={{ marginTop: 20, marginBottom: 0, fontSize: 13 }}>
          Şifrenizi unuttuysanız yöneticinize başvurun; geçici şifre verir. Araçtaki satış elemanları telefon
          uygulamasını kullanır.
        </Typography.Paragraph>
      </div>
    </div>
  )
}
