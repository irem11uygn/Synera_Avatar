import { Alert, Form, Modal } from 'antd'
import { useState, type ReactNode } from 'react'
import { errorMessage } from '../api/client'

type Props<T> = {
  title: string
  open: boolean
  onClose: () => void
  initialValues?: Partial<T>
  onSubmit: (values: T) => Promise<unknown>
  okText?: string
  width?: number
  children: ReactNode
}

/**
 * Pencere içinde form. "Kaydet" gerçek bir gönder düğmesidir (Enter ile de gönderilir);
 * sunucunun Türkçe hata mesajı pencerenin üstünde gösterilir, pencere kapanmaz.
 * Form her açılışta yeniden kurulur ve kendi deposunu kullanır: önceki düzenlemenin değerleri
 * kalmaz, başlangıç değerleri her seferinde uygulanır. İçerideki alanlar forma
 * Form.useFormInstance ile ulaşır.
 */
export function FormModal<T extends object>({
  title,
  open,
  onClose,
  initialValues,
  onSubmit,
  okText = 'Kaydet',
  width,
  children,
}: Props<T>) {
  const [error, setError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)

  async function finish(values: T) {
    setSaving(true)
    setError(null)
    try {
      await onSubmit(values)
      onClose()
    } catch (caught) {
      setError(errorMessage(caught))
    } finally {
      setSaving(false)
    }
  }

  return (
    <Modal
      open={open}
      title={title}
      width={width}
      okText={okText}
      cancelText="Vazgeç"
      onCancel={onClose}
      afterClose={() => setError(null)}
      destroyOnHidden
      okButtonProps={{ htmlType: 'submit', loading: saving }}
      modalRender={(dom) => (
        <Form<T> layout="vertical" initialValues={initialValues} onFinish={finish} validateTrigger="onBlur">
          {dom}
        </Form>
      )}
    >
      {error && <Alert type="error" showIcon role="alert" title={error} style={{ marginBottom: 16 }} />}
      {children}
    </Modal>
  )
}
