// 3B eğilen kart: fare kartın üzerinde gezinirken kart o yöne birkaç derece eğilir.
// Dokunmatik ekranda ve "azaltılmış hareket" tercihinde eğilmez (CSS de dönüşümü kapatır).

import type { PointerEvent } from 'react'

function reducedMotion(): boolean {
  return window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false
}

/** `.tilt` sınıflı öğeye verilir: <div className="tilt" {...tiltHandlers()} /> */
export function tiltHandlers(maxDeg = 4) {
  return {
    onPointerMove(event: PointerEvent<HTMLElement>) {
      if (event.pointerType !== 'mouse' || reducedMotion()) return
      const el = event.currentTarget
      const box = el.getBoundingClientRect()
      const x = (event.clientX - box.left) / box.width - 0.5
      const y = (event.clientY - box.top) / box.height - 0.5
      el.style.setProperty('--ry', `${(x * maxDeg).toFixed(2)}deg`)
      el.style.setProperty('--rx', `${(-y * maxDeg).toFixed(2)}deg`)
    },
    onPointerLeave(event: PointerEvent<HTMLElement>) {
      event.currentTarget.style.removeProperty('--rx')
      event.currentTarget.style.removeProperty('--ry')
    },
  }
}
