import { Flex, Space, Typography } from 'antd'
import { useEffect, type ReactNode } from 'react'

/** Sayfa başlığı (aynı zamanda sekme başlığı), sağda işlem düğmeleri. */
export function Page({ title, extra, children }: { title: string; extra?: ReactNode; children: ReactNode }) {
  useEffect(() => {
    document.title = `${title} — AVATAR`
  }, [title])

  return (
    <>
      <Flex justify="space-between" align="center" wrap gap="small" style={{ marginBottom: 16 }}>
        <Typography.Title level={3} style={{ margin: 0 }}>
          {title}
        </Typography.Title>
        {extra && <Space wrap>{extra}</Space>}
      </Flex>
      {children}
    </>
  )
}
