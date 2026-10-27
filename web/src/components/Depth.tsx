// Derinlikli (3D) yüzey bileşenleri: imleçle hafifçe eğilen kart ve gösterge kutusu.
// Eğilme yalnız fareyle ve hareket azaltma tercihi yokken çalışır; dokunmatikte kart sabit kalır.

import { useRef, type CSSProperties, type PointerEvent, type ReactNode } from 'react'

const MAX_TILT_DEG = 6

function reducedMotion(): boolean {
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches
}

export function Tilt({ children, className = '', style }: { children: ReactNode; className?: string; style?: CSSProperties }) {
  const ref = useRef<HTMLDivElement>(null)

  function move(event: PointerEvent<HTMLDivElement>) {
    const element = ref.current
    if (!element || event.pointerType !== 'mouse' || reducedMotion()) return
    const box = element.getBoundingClientRect()
    const x = (event.clientX - box.left) / box.width - 0.5
    const y = (event.clientY - box.top) / box.height - 0.5
    element.style.setProperty('--rx', `${(-y * MAX_TILT_DEG).toFixed(2)}deg`)
    element.style.setProperty('--ry', `${(x * MAX_TILT_DEG).toFixed(2)}deg`)
    element.classList.add('is-tilting')
  }

  function leave() {
    const element = ref.current
    if (!element) return
    element.style.setProperty('--rx', '0deg')
    element.style.setProperty('--ry', '0deg')
    element.classList.remove('is-tilting')
  }

  return (
    <div ref={ref} className={`tilt ${className}`} style={style} onPointerMove={move} onPointerLeave={leave}>
      {children}
    </div>
  )
}

type StatTileProps = {
  label: string
  value: ReactNode
  hint?: ReactNode
  color?: string
  onClick?: () => void
}

/** Ana sayfa ve özet ekranlarındaki gösterge kutusu; tıklanabilirse düğme gibi davranır. */
export function StatTile({ label, value, hint, color, onClick }: StatTileProps) {
  const body = (
    <Tilt className="stat-tile" style={{ '--tile-color': color, cursor: onClick ? 'pointer' : undefined } as CSSProperties}>
      <div className="stat-tile-label">{label}</div>
      <div className="stat-tile-value">{value}</div>
      {hint && <div className="stat-tile-hint">{hint}</div>}
    </Tilt>
  )
  if (!onClick) return body
  return (
    <button type="button" className="stat-button" onClick={onClick} aria-label={`${label}: ayrıntıya git`}>
      {body}
    </button>
  )
}
