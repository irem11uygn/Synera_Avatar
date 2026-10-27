// Ana sayfa: kullanıcının rolüne göre "bugün yapılacaklar" ve sık kullanılan işlemler.

import {
  AlertOutlined,
  AppstoreOutlined,
  CalculatorOutlined,
  CarOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  FileSearchOutlined,
  InboxOutlined,
  NodeIndexOutlined,
  ReloadOutlined,
  RollbackOutlined,
  SafetyCertificateOutlined,
  ScissorOutlined,
  ShoppingCartOutlined,
  ToolOutlined,
  WarningOutlined,
} from '@ant-design/icons'
import { useQuery } from '@tanstack/react-query'
import { Button, Col, Row, Skeleton } from 'antd'
import type { ReactNode } from 'react'
import { api } from '../api/client'
import type { Dashboard, UserRole } from '../api/types'
import { useSession } from '../auth/context'
import { Page } from '../components/Page'
import { QueryError } from '../components/QueryError'
import { Stat } from '../components/Stat'
import { formatDate, formatMoney } from '../lib/format'
import { ROLE } from '../lib/roles'
import { navigate } from '../lib/router'
import { t } from '../lib/i18n'

type Tone = 'danger' | 'warning' | 'info' | 'success'
type Todo = { tone: Tone; icon: ReactNode; title: string; sub: string; to: string; action: string; roles: UserRole[] }

function todos(data: Dashboard): Todo[] {
  const expired = data.expiring.filter((lot) => lot.days_left < 0)
  const soon = data.expiring.filter((lot) => lot.days_left >= 0)
  const list: Todo[] = []
  if (data.unread_alerts > 0)
    list.push({
      tone: 'danger',
      icon: <AlertOutlined />,
      title: t('{n} okunmamış uyarı', { n: data.unread_alerts }),
      sub: t('Satışa kapalı ya da son kullanma tarihi geçmiş lot telefondan satılmış olabilir.'),
      to: '/uyarilar',
      action: t('Uyarıları gör'),
      roles: ['YONETICI', 'KALITE'],
    })
  if (data.open_recalls.length > 0)
    list.push({
      tone: 'danger',
      icon: <SafetyCertificateOutlined />,
      title: t('{n} açık geri çağırma', { n: data.open_recalls.length }),
      sub: t('{lots} — müşterilere haber verildi mi, mal toplandı mı?', { lots: data.open_recalls.map((r) => r.lot_no).join(', ') }),
      to: '/geri-cagirma',
      action: t('Geri çağırmalar'),
      roles: ['YONETICI', 'KALITE'],
    })
  if (expired.length > 0)
    list.push({
      tone: 'danger',
      icon: <ClockCircleOutlined />,
      title: t('{n} lotun son kullanma tarihi geçti', { n: expired.length }),
      sub: t('Bu mallar satılamaz. Rafından ayırın ve fire/imha kaydı girin.'),
      to: '/son-kullanma',
      action: t('Listeyi aç'),
      roles: ['YONETICI', 'DEPO', 'MAGAZA', 'KALITE'],
    })
  if (soon.length > 0)
    list.push({
      tone: 'warning',
      icon: <ClockCircleOutlined />,
      title: t('{n} lot {days} gün içinde dolacak', { n: soon.length, days: data.expiry_warning_days }),
      sub: t('Önce bunları satın (ilk dolan ilk çıkar).'),
      to: '/son-kullanma',
      action: t('Listeyi aç'),
      roles: ['YONETICI', 'DEPO', 'MAGAZA'],
    })
  if (data.low_stock.length > 0)
    list.push({
      tone: 'warning',
      icon: <WarningOutlined />,
      title: t('{n} üründe stok azaldı', { n: data.low_stock.length }),
      sub: data.low_stock.map((p) => p.product_name).join(', '),
      to: '/stok',
      action: t('Stoka bak'),
      roles: ['YONETICI', 'DEPO', 'URETIM'],
    })
  if (data.shipped_orders > 0)
    list.push({
      tone: 'info',
      icon: <ToolOutlined />,
      title: t('{n} fason üretim teslim alınmayı bekliyor', { n: data.shipped_orders }),
      sub: t('Fasoncudan gelen ürünü ve faturayı girince birim maliyet hesaplanır.'),
      to: '/uretim',
      action: t('Emirleri aç'),
      roles: ['YONETICI', 'URETIM'],
    })
  if (data.draft_orders > 0)
    list.push({
      tone: 'info',
      icon: <ToolOutlined />,
      title: t('{n} fason üretim emri gönderilmedi', { n: data.draft_orders }),
      sub: t('Hammaddeyi fasoncuya sevk edin ya da emri iptal edin.'),
      to: '/uretim',
      action: t('Emirleri aç'),
      roles: ['YONETICI', 'URETIM'],
    })
  if (data.draft_cuttings > 0)
    list.push({
      tone: 'info',
      icon: <ScissorOutlined />,
      title: t('{n} parçalama onay bekliyor', { n: data.draft_cuttings }),
      sub: t('Tartılan parçaları girip onaylayınca parçalar stoka girer.'),
      to: '/parcalama',
      action: t('Parçalamaları aç'),
      roles: ['YONETICI', 'URETIM'],
    })
  return list
}

type Quick = { label: string; icon: ReactNode; to: string; roles: UserRole[] }

const QUICK: Quick[] = [
  { label: t('Mağaza satışı'), icon: <ShoppingCartOutlined />, to: '/magaza-satisi', roles: ['YONETICI', 'MAGAZA'] },
  { label: t('İade al'), icon: <RollbackOutlined />, to: '/satislar', roles: ['YONETICI', 'MAGAZA'] },
  { label: t('Gün sonu'), icon: <CalculatorOutlined />, to: '/gun-sonu', roles: ['YONETICI', 'MAGAZA'] },
  { label: t('Mal kabul'), icon: <InboxOutlined />, to: '/alislar/yeni', roles: ['YONETICI', 'DEPO'] },
  { label: t('Araca yükleme'), icon: <CarOutlined />, to: '/transferler', roles: ['YONETICI', 'DEPO'] },
  { label: t('Sayım yap'), icon: <AppstoreOutlined />, to: '/sayim', roles: ['YONETICI', 'DEPO'] },
  { label: t('Yeni fason üretim'), icon: <ToolOutlined />, to: '/uretim/yeni', roles: ['YONETICI', 'URETIM'] },
  { label: t('Yeni parçalama'), icon: <ScissorOutlined />, to: '/parcalama/yeni', roles: ['YONETICI', 'URETIM'] },
  { label: t('Yeniden işleme'), icon: <ReloadOutlined />, to: '/yeniden-isleme', roles: ['URETIM'] },
  { label: t('Lot izle'), icon: <NodeIndexOutlined />, to: '/izleme', roles: ['YONETICI', 'KALITE', 'DEPO', 'URETIM', 'MAGAZA'] },
  { label: t('Geri çağırma'), icon: <SafetyCertificateOutlined />, to: '/geri-cagirma', roles: ['KALITE'] },
  { label: t('Tatbikat yap'), icon: <FileSearchOutlined />, to: '/tatbikat', roles: ['KALITE'] },
]

function greeting(): string {
  const hour = new Date().getHours()
  if (hour < 11) return t('Günaydın')
  if (hour < 18) return t('İyi çalışmalar')
  return t('İyi akşamlar')
}

export default function HomePage() {
  const { user } = useSession()
  const dashboard = useQuery({
    queryKey: ['dashboard'],
    queryFn: () => api<Dashboard>('/dashboard'),
    refetchInterval: 120_000,
  })
  const data = dashboard.data
  const role = user.role
  const mine = data ? todos(data).filter((todo) => todo.roles.includes(role)) : []
  const quick = QUICK.filter((q) => q.roles.includes(role))

  return (
    <Page
      title={`${greeting()}, ${user.full_name}`}
      description={data ? `${formatDate(data.today)} · ${ROLE[role]}` : ROLE[role]}
    >
      {dashboard.isError && <QueryError error={dashboard.error} onRetry={() => dashboard.refetch()} />}

      <div className="section-title" style={{ marginTop: 0 }}>
        {t('Bugün yapılacaklar')}
      </div>
      {dashboard.isPending && <Skeleton active paragraph={{ rows: 3 }} />}
      {data && mine.length === 0 && (
        <div className="todo is-success">
          <span className="todo-icon" aria-hidden="true">
            <CheckCircleOutlined />
          </span>
          <div className="todo-text">
            <div className="todo-title">{t('Acil bir iş yok')}</div>
            <div className="todo-sub">{t('Bekleyen uyarı, dolan lot ya da yarım kalmış belge görünmüyor.')}</div>
          </div>
        </div>
      )}
      {mine.map((todo) => (
        <div key={todo.title} className={`todo is-${todo.tone}`}>
          <span className="todo-icon" aria-hidden="true">
            {todo.icon}
          </span>
          <div className="todo-text">
            <div className="todo-title">{todo.title}</div>
            <div className="todo-sub">{todo.sub}</div>
          </div>
          <Button onClick={() => navigate(todo.to)}>{todo.action}</Button>
        </div>
      ))}

      {quick.length > 0 && (
        <>
          <div className="section-title">{t('Hızlı işlemler')}</div>
          <div className="quick-actions">
            {quick.map((q) => (
              <button key={q.to} type="button" className="quick-action" onClick={() => navigate(q.to)}>
                {q.icon}
                {q.label}
              </button>
            ))}
          </div>
        </>
      )}

      {data && (
        <>
          <div className="section-title">{t('Özet')}</div>
          <Row gutter={[12, 12]}>
            {(role === 'YONETICI' || role === 'MAGAZA') && (
              <Col xs={12} lg={6}>
                <Stat
                  label={t('Bugünkü satış')}
                  value={formatMoney(data.today_sales_amount)}
                  hint={t('{n} satış belgesi', { n: data.today_sale_count })}
                  tone="success"
                  onClick={() => navigate('/gun-sonu')}
                />
              </Col>
            )}
            {(role === 'YONETICI' || role === 'DEPO') && (
              <Col xs={12} lg={6}>
                <Stat
                  label={t('Elimizdeki stokun değeri')}
                  value={formatMoney(data.stock_value)}
                  hint={t('Maliyet fiyatıyla')}
                  tone="brand"
                  onClick={() => navigate('/stok')}
                />
              </Col>
            )}
            <Col xs={12} lg={6}>
              <Stat
                label={t('Dolmak üzere / dolmuş lot')}
                value={data.expiring.length}
                hint={t('{n} gün içinde ya da geçmiş', { n: data.expiry_warning_days })}
                tone={data.expiring.length ? 'warning' : 'neutral'}
                onClick={() => navigate('/son-kullanma')}
              />
            </Col>
            <Col xs={12} lg={6}>
              <Stat
                label={t('Açık geri çağırma')}
                value={data.open_recalls.length}
                hint={t('Satışa kapalı lotlar')}
                tone={data.open_recalls.length ? 'danger' : 'neutral'}
                onClick={() => navigate(role === 'YONETICI' || role === 'KALITE' ? '/geri-cagirma' : '/izleme')}
              />
            </Col>
          </Row>
        </>
      )}
    </Page>
  )
}
