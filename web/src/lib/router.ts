// Küçük istemci tarafı yönlendirici: History API + popstate. Sayfa sayısı az olduğu için ayrı bir
// yönlendirme kütüphanesine gerek yok. Derin bağlantılar sunucuda index.html'e düşer (nginx.conf).

import { useSyncExternalStore } from 'react'

const listeners = new Set<() => void>()

function subscribe(listener: () => void): () => void {
  listeners.add(listener)
  window.addEventListener('popstate', listener)
  return () => {
    listeners.delete(listener)
    window.removeEventListener('popstate', listener)
  }
}

export function usePath(): string {
  return useSyncExternalStore(subscribe, () => window.location.pathname)
}

export function navigate(to: string, { replace = false } = {}): void {
  if (to === window.location.pathname) return
  if (replace) window.history.replaceState(null, '', to)
  else window.history.pushState(null, '', to)
  listeners.forEach((listener) => listener())
  window.scrollTo(0, 0)
}

/** "/uretim/:id" kalıbı "/uretim/7" yoluyla eşleşirse { id: "7" }; eşleşmezse null. */
export function matchPath(pattern: string, path: string): Record<string, string> | null {
  const normalize = (value: string) => value.replace(/\/+$/, '') || '/'
  const patternParts = normalize(pattern).split('/')
  const pathParts = normalize(path).split('/')
  if (patternParts.length !== pathParts.length) return null
  const params: Record<string, string> = {}
  for (const [index, part] of patternParts.entries()) {
    if (part.startsWith(':')) params[part.slice(1)] = decodeURIComponent(pathParts[index])
    else if (part !== pathParts[index]) return null
  }
  return params
}
