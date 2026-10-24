import type { MouseEvent, ReactNode } from 'react'
import { navigate } from '../lib/router'

/** Gerçek bağlantı (yeni sekmede açılabilir); normal tıklamada sayfa yenilenmeden gider. */
export function Link({ to, children }: { to: string; children: ReactNode }) {
  const onClick = (event: MouseEvent<HTMLAnchorElement>) => {
    if (event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return
    event.preventDefault()
    navigate(to)
  }
  return (
    <a href={to} onClick={onClick}>
      {children}
    </a>
  )
}
