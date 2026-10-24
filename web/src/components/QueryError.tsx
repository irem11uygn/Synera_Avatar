import { Alert, Button } from 'antd'
import { errorMessage } from '../api/client'

/** Veri yüklenemediğinde gösterilen hata kutusu; "Yeniden dene" sorguyu tekrarlar. */
export function QueryError({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  return (
    <Alert
      type="error"
      showIcon
      role="alert"
      title="Veri alınamadı"
      description={errorMessage(error)}
      action={onRetry && <Button onClick={onRetry}>Yeniden dene</Button>}
      style={{ marginBottom: 16 }}
    />
  )
}
