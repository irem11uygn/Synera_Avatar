// Oturum belirteci gerektiren dosya indirme (CSV raporları, geri çağırma iletişim listesi).
// Düz bağlantı Authorization başlığı gönderemez; dosya fetch ile alınıp tarayıcıya kaydettirilir.

import { ApiError, getToken } from '../api/client'

type Query = Record<string, string | number | null | undefined>

export async function downloadFile(path: string, query: Query = {}, fallbackName = 'dosya.csv'): Promise<void> {
  const url = new URL(`/api/v1${path}`, window.location.origin)
  for (const [key, value] of Object.entries(query)) {
    if (value !== undefined && value !== null && value !== '') url.searchParams.set(key, String(value))
  }
  const token = getToken()
  let response: Response
  try {
    response = await fetch(url, { headers: token ? { Authorization: `Bearer ${token}` } : {} })
  } catch {
    throw new ApiError(0, 'NETWORK', 'Sunucuya ulaşılamadı; dosya indirilemedi.')
  }
  if (!response.ok) throw new ApiError(response.status, 'HTTP_ERROR', `Dosya indirilemedi (HTTP ${response.status}).`)
  const name = /filename="([^"]+)"/.exec(response.headers.get('content-disposition') ?? '')?.[1] ?? fallbackName
  const blob = await response.blob()
  const link = document.createElement('a')
  link.href = URL.createObjectURL(blob)
  link.download = name
  document.body.append(link)
  link.click()
  link.remove()
  setTimeout(() => URL.revokeObjectURL(link.href), 1000)
}
