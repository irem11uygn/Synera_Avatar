// Geçici elle yazılmış tip; API büyüyünce tipler OpenAPI tanımından üretilecek (ADR-002).
import { t } from '../lib/i18n'

export type Health = {
  status: 'ok' | 'degraded'
  database: 'ok' | 'error'
  version: string
}

export async function fetchHealth(): Promise<Health> {
  const response = await fetch('/api/v1/health')
  // 503 de geçerli bir sağlık yanıtıdır: gövdesi "degraded" durumunu taşır.
  if (!response.ok && response.status !== 503) {
    throw new Error(t('API yanıt vermedi (HTTP {status})', { status: response.status }))
  }
  return response.json()
}
