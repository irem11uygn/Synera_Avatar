import { Alert, Button } from 'antd'
import { errorMessage } from '../api/client'
import { t } from '../lib/i18n'

/** Veri yüklenemediğinde gösterilen hata kutusu; "Yeniden dene" sorguyu tekrarlar. */
export function QueryError({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  return (
    <Alert
      type="error"
      showIcon
      role="alert"
      title={t('Veri alınamadı')}
      description={errorMessage(error)}
      action={onRetry && <Button onClick={onRetry}>{t('Yeniden dene')}</Button>}
      style={{ marginBottom: 16 }}
    />
  )
}
