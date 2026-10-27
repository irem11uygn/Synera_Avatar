import { Space, Typography } from 'antd'
import { useEffect, type ReactNode } from 'react'
import { Link } from './Link'

type Props = {
  title: string
  /** Başlığın altındaki bir iki cümle: bu ekranda ne yapılır. */
  description?: ReactNode
  /** Üst sayfaya dönüş bağlantısı, ör. { to: '/satislar', label: 'Satışlar' }. */
  back?: { to: string; label: string }
  extra?: ReactNode
  children: ReactNode
}

/** Sayfa başlığı (aynı zamanda sekme başlığı), kısa açıklama, sağda işlem düğmeleri. */
export function Page({ title, description, back, extra, children }: Props) {
  useEffect(() => {
    document.title = `${title} — Synera`
  }, [title])

  return (
    <>
      <div className="page-head">
        <div style={{ minWidth: 0 }}>
          {back && (
            <span className="page-back">
              <Link to={back.to}>← {back.label}</Link>
            </span>
          )}
          <Typography.Title level={1} className="page-title">
            {title}
          </Typography.Title>
          {description && <p className="page-description">{description}</p>}
        </div>
        {extra && <Space wrap>{extra}</Space>}
      </div>
      {children}
    </>
  )
}
