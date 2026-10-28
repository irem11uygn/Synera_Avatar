import type { ReactNode } from 'react'
import { tiltHandlers } from './Tilt'

type Tone = 'neutral' | 'brand' | 'success' | 'warning' | 'danger'

type Props = {
  label: string
  value: ReactNode
  hint?: ReactNode
  tone?: Tone
  onClick?: () => void
}

/** Özet kutusu: etiket, büyük değer, kısa açıklama. Tıklanabilirse düğmedir. */
export function Stat({ label, value, hint, tone = 'neutral', onClick }: Props) {
  const content = (
    <>
      <span className="stat-label">
        <span className="stat-dot" aria-hidden="true" />
        {label}
      </span>
      <div className="stat-value">{value}</div>
      {hint && <div className="stat-hint">{hint}</div>}
    </>
  )
  if (!onClick) return <div className={`stat tilt is-${tone}`} {...tiltHandlers()}>{content}</div>
  return (
    <button type="button" className={`stat tilt is-${tone}`} onClick={onClick} {...tiltHandlers()}>
      {content}
    </button>
  )
}
