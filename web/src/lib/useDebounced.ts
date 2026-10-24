import { useEffect, useState } from 'react'

/** Değer `delay` ms boyunca değişmeyince güncellenir (ör. her tuşta sunucuya gitmemek için). */
export function useDebounced<T>(value: T, delay = 300): T {
  const [debounced, setDebounced] = useState(value)
  useEffect(() => {
    const timer = window.setTimeout(() => setDebounced(value), delay)
    return () => window.clearTimeout(timer)
  }, [value, delay])
  return debounced
}
