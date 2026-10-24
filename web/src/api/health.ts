// Geçici elle yazılmış tip; API büyüyünce tipler OpenAPI tanımından üretilecek (ADR-002).
export type Health = {
  status: 'ok' | 'degraded'
  database: 'ok' | 'error'
  version: string
}

export async function fetchHealth(): Promise<Health> {
  const response = await fetch('/api/v1/health')
  // 503 de geçerli bir sağlık yanıtıdır: gövdesi "degraded" durumunu taşır.
  if (!response.ok && response.status !== 503) {
    throw new Error(`API yanıt vermedi (HTTP ${response.status})`)
  }
  return response.json()
}
