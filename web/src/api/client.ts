// API istemcisi: oturum belirteci, hata biçimi (api.md §3) ve ağ hatası tek yerde ele alınır.

const TOKEN_KEY = 'avatar.token'

export class ApiError extends Error {
  readonly status: number
  readonly code: string
  readonly details: Record<string, unknown>

  constructor(status: number, code: string, message: string, details: Record<string, unknown> = {}) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
    this.details = details
  }
}

// Sekme kapanınca oturum biter; aynı sekmede sayfa yenilenince sürer.
export function getToken(): string | null {
  try {
    return sessionStorage.getItem(TOKEN_KEY)
  } catch {
    return null
  }
}

export function setToken(token: string | null): void {
  try {
    if (token) sessionStorage.setItem(TOKEN_KEY, token)
    else sessionStorage.removeItem(TOKEN_KEY)
  } catch {
    // Depolama kapalıysa oturum yalnız bu sayfa açıkken sürer.
  }
}

let unauthorizedHandler: () => void = () => {}

/** Oturum düşerse (401) ne yapılacağı; oturum katmanı bunu girişe dönüş olarak ayarlar. */
export function onUnauthorized(handler: () => void): void {
  unauthorizedHandler = handler
}

type Query = Record<string, string | number | boolean | null | undefined>

export type RequestOptions = { method?: 'GET' | 'POST' | 'PUT'; body?: unknown; query?: Query }

function toApiError(status: number, body: unknown): ApiError {
  const error = (body as { error?: { code?: string; message?: string; details?: Record<string, unknown> } })
    ?.error
  if (error?.code && error.message) return new ApiError(status, error.code, error.message, error.details ?? {})
  return new ApiError(status, 'HTTP_ERROR', `Sunucu beklenmeyen bir yanıt verdi (HTTP ${status}).`)
}

export async function api<T>(path: string, { method = 'GET', body, query }: RequestOptions = {}): Promise<T> {
  const url = new URL(`/api/v1${path}`, window.location.origin)
  for (const [key, value] of Object.entries(query ?? {})) {
    if (value !== undefined && value !== null && value !== '') url.searchParams.set(key, String(value))
  }
  const token = getToken()
  const headers: Record<string, string> = { Accept: 'application/json' }
  if (token) headers.Authorization = `Bearer ${token}`
  if (body !== undefined) headers['Content-Type'] = 'application/json'

  let response: Response
  try {
    response = await fetch(url, { method, headers, body: body === undefined ? undefined : JSON.stringify(body) })
  } catch {
    throw new ApiError(0, 'NETWORK', 'Sunucuya ulaşılamadı. Bağlantıyı ve sunucunun çalıştığını kontrol edin.')
  }

  const text = await response.text()
  let data: unknown = null
  try {
    data = text ? JSON.parse(text) : null
  } catch {
    data = null
  }
  if (!response.ok) {
    if (response.status === 401 && token) unauthorizedHandler()
    throw toApiError(response.status, data)
  }
  return data as T
}

/** Hata nesnesinden kullanıcıya gösterilecek Türkçe metin. */
export function errorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    const fields = error.details.fields as { field: string; problem: string }[] | undefined
    if (fields?.length) return `${error.message} (${fields.map((f) => f.field.replace(/^body\./, '')).join(', ')})`
    return error.message
  }
  return error instanceof Error ? error.message : 'Bilinmeyen hata.'
}
