// Üst çubuktaki alarm zili: açık alarm sayısı (kritik varsa kırmızı) ve son beş alarm.
// Yeni bir alarm gelince köşede bildirim açılır; aynı alarm bir oturumda bir kez bildirilir.

import { BellOutlined, ExclamationCircleFilled, InfoCircleFilled, WarningFilled } from '@ant-design/icons'
import { App, Badge, Button, Dropdown, Empty } from 'antd'
import { useEffect } from 'react'
import type { AlertSummary, Severity } from '../api/types'
import { formatDateTime } from '../lib/format'
import { t } from '../lib/i18n'
import { ALERT_KIND, SEVERITY } from '../lib/labels'
import { navigate } from '../lib/router'

const SEEN_KEY = 'synera.alarm.seen'

export function SeverityIcon({ severity }: { severity: Severity }) {
  if (severity === 'KRITIK') return <ExclamationCircleFilled className="sev-icon is-critical" aria-label={SEVERITY.KRITIK} />
  if (severity === 'UYARI') return <WarningFilled className="sev-icon is-warning" aria-label={SEVERITY.UYARI} />
  return <InfoCircleFilled className="sev-icon is-info" aria-label={SEVERITY.BILGI} />
}

function readSeen(): number | null {
  try {
    const value = sessionStorage.getItem(SEEN_KEY)
    return value == null ? null : Number(value)
  } catch {
    return null
  }
}

function writeSeen(id: number) {
  try {
    sessionStorage.setItem(SEEN_KEY, String(id))
  } catch {
    // gizli pencere: bildirimler yine çalışır, yalnız sayfa yenilenince tekrar edebilir
  }
}

export function AlarmBell({ summary }: { summary: AlertSummary | undefined }) {
  const { notification } = App.useApp()

  useEffect(() => {
    if (!summary) return
    const newest = summary.latest.reduce((max, a) => Math.max(max, a.id), 0)
    const seen = readSeen()
    if (seen == null) {
      // Oturumun ilk açılışı: tek tek değil, kritik alarm varsa bir özet bildirimi.
      if (summary.open_critical > 0)
        notification.error({
          key: 'alarm-ozet',
          title: t('{n} kritik alarm açık', { n: summary.open_critical }),
          description: t('Alarm merkezinden ayrıntıya bakın; ilgilendiğiniz alarmı okundu işaretleyin.'),
          actions: (
            <Button type="primary" size="small" onClick={() => navigate('/alarmlar')}>
              {t('Alarm merkezi')}
            </Button>
          ),
          placement: 'bottomRight',
        })
    } else {
      for (const alarm of summary.latest.filter((a) => a.id > seen).reverse()) {
        const open = alarm.severity === 'KRITIK' ? notification.error : alarm.severity === 'UYARI' ? notification.warning : notification.info
        open({
          key: `alarm-${alarm.id}`,
          title: ALERT_KIND[alarm.kind],
          description: alarm.message,
          placement: 'bottomRight',
          duration: alarm.severity === 'KRITIK' ? 0 : 8,
          actions: (
            <Button size="small" onClick={() => navigate('/alarmlar')}>
              {t('Göster')}
            </Button>
          ),
        })
      }
    }
    writeSeen(Math.max(newest, seen ?? 0))
  }, [summary, notification])

  const count = summary?.open_total ?? 0
  const critical = (summary?.open_critical ?? 0) > 0
  return (
    <Dropdown
      trigger={['click']}
      placement="bottomRight"
      popupRender={() => (
        <div className="bell-panel glass">
          <div className="bell-panel-head">
            <strong>{t('Açık alarmlar')}</strong>
            <span className="muted">
              {t('{c} kritik · {w} uyarı', { c: summary?.open_critical ?? 0, w: summary?.open_warning ?? 0 })}
            </span>
          </div>
          {summary && summary.latest.length > 0 ? (
            <ul className="bell-list">
              {summary.latest.map((alarm) => (
                <li key={alarm.id}>
                  <button type="button" onClick={() => navigate('/alarmlar')}>
                    <SeverityIcon severity={alarm.severity} />
                    <span className="bell-text">
                      <span className="bell-title">{ALERT_KIND[alarm.kind]}</span>
                      <span className="bell-message">{alarm.message}</span>
                      <span className="bell-time">{formatDateTime(alarm.created_at)}</span>
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          ) : (
            <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description={t('Açık alarm yok.')} />
          )}
          <Button block type="link" onClick={() => navigate('/alarmlar')}>
            {t('Alarm merkezine git')}
          </Button>
        </div>
      )}
    >
      <Button
        className={`bell-button${critical ? ' is-critical' : ''}`}
        aria-label={t('Alarmlar: {n} açık', { n: count })}
        icon={
          <Badge count={count} size="small" color={critical ? '#c62828' : '#b45309'} offset={[4, -4]}>
            <BellOutlined style={{ fontSize: 18 }} />
          </Badge>
        }
      />
    </Dropdown>
  )
}
