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
      title: `${data.unread_alerts} okunmamış uyarı`,
      sub: 'Satışa kapalı ya da son kullanma tarihi geçmiş lot telefondan satılmış olabilir.',
      to: '/uyarilar',
      action: 'Uyarıları gör',
      roles: ['YONETICI', 'KALITE'],
    })
  if (data.open_recalls.length > 0)
    list.push({
      tone: 'danger',
      icon: <SafetyCertificateOutlined />,
      title: `${data.open_recalls.length} açık geri çağırma`,
      sub: `${data.open_recalls.map((r) => r.lot_no).join(', ')} — müşterilere haber verildi mi, mal toplandı mı?`,
      to: '/geri-cagirma',
      action: 'Geri çağırmalar',
      roles: ['YONETICI', 'KALITE'],
    })
  if (expired.length > 0)
    list.push({
      tone: 'danger',
      icon: <ClockCircleOutlined />,
      title: `${expired.length} lotun son kullanma tarihi geçti`,
      sub: 'Bu mallar satılamaz. Rafından ayırın ve fire/imha kaydı girin.',
      to: '/son-kullanma',
      action: 'Listeyi aç',
      roles: ['YONETICI', 'DEPO', 'MAGAZA', 'KALITE'],
    })
  if (soon.length > 0)
    list.push({
      tone: 'warning',
      icon: <ClockCircleOutlined />,
      title: `${soon.length} lot ${data.expiry_warning_days} gün içinde dolacak`,
      sub: 'Önce bunları satın (ilk dolan ilk çıkar).',
      to: '/son-kullanma',
      action: 'Listeyi aç',
      roles: ['YONETICI', 'DEPO', 'MAGAZA'],
    })
  if (data.low_stock.length > 0)
    list.push({
      tone: 'warning',
      icon: <WarningOutlined />,
      title: `${data.low_stock.length} üründe stok azaldı`,
      sub: data.low_stock.map((p) => p.product_name).join(', '),
      to: '/stok',
      action: 'Stoka bak',
      roles: ['YONETICI', 'DEPO', 'URETIM'],
    })
  if (data.shipped_orders > 0)
    list.push({
      tone: 'info',
      icon: <ToolOutlined />,
      title: `${data.shipped_orders} fason üretim teslim alınmayı bekliyor`,
      sub: 'Fasoncudan gelen ürünü ve faturayı girince birim maliyet hesaplanır.',
      to: '/uretim',
      action: 'Emirleri aç',
      roles: ['YONETICI', 'URETIM'],
    })
  if (data.draft_orders > 0)
    list.push({
      tone: 'info',
      icon: <ToolOutlined />,
      title: `${data.draft_orders} fason üretim emri gönderilmedi`,
      sub: 'Hammaddeyi fasoncuya sevk edin ya da emri iptal edin.',
      to: '/uretim',
      action: 'Emirleri aç',
      roles: ['YONETICI', 'URETIM'],
    })
  if (data.draft_cuttings > 0)
    list.push({
      tone: 'info',
      icon: <ScissorOutlined />,
      title: `${data.draft_cuttings} parçalama onay bekliyor`,
      sub: 'Tartılan parçaları girip onaylayınca parçalar stoka girer.',
      to: '/parcalama',
      action: 'Parçalamaları aç',
      roles: ['YONETICI', 'URETIM'],
    })
  return list
}

type Quick = { label: string; icon: ReactNode; to: string; roles: UserRole[] }

const QUICK: Quick[] = [
  { label: 'Mağaza satışı', icon: <ShoppingCartOutlined />, to: '/magaza-satisi', roles: ['YONETICI', 'MAGAZA'] },
  { label: 'İade al', icon: <RollbackOutlined />, to: '/satislar', roles: ['YONETICI', 'MAGAZA'] },
  { label: 'Gün sonu', icon: <CalculatorOutlined />, to: '/gun-sonu', roles: ['YONETICI', 'MAGAZA'] },
  { label: 'Mal kabul', icon: <InboxOutlined />, to: '/alislar/yeni', roles: ['YONETICI', 'DEPO'] },
  { label: 'Araca yükleme', icon: <CarOutlined />, to: '/transferler', roles: ['YONETICI', 'DEPO'] },
  { label: 'Sayım yap', icon: <AppstoreOutlined />, to: '/sayim', roles: ['YONETICI', 'DEPO'] },
  { label: 'Yeni fason üretim', icon: <ToolOutlined />, to: '/uretim/yeni', roles: ['YONETICI', 'URETIM'] },
  { label: 'Yeni parçalama', icon: <ScissorOutlined />, to: '/parcalama/yeni', roles: ['YONETICI', 'URETIM'] },
  { label: 'Yeniden işleme', icon: <ReloadOutlined />, to: '/yeniden-isleme', roles: ['URETIM'] },
  { label: 'Lot izle', icon: <NodeIndexOutlined />, to: '/izleme', roles: ['YONETICI', 'KALITE', 'DEPO', 'URETIM', 'MAGAZA'] },
  { label: 'Geri çağırma', icon: <SafetyCertificateOutlined />, to: '/geri-cagirma', roles: ['KALITE'] },
  { label: 'Tatbikat yap', icon: <FileSearchOutlined />, to: '/tatbikat', roles: ['KALITE'] },
]

function greeting(): string {
  const hour = new Date().getHours()
  if (hour < 11) return 'Günaydın'
  if (hour < 18) return 'İyi çalışmalar'
  return 'İyi akşamlar'
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
        Bugün yapılacaklar
      </div>
      {dashboard.isPending && <Skeleton active paragraph={{ rows: 3 }} />}
      {data && mine.length === 0 && (
        <div className="todo is-success">
          <span className="todo-icon" aria-hidden="true">
            <CheckCircleOutlined />
          </span>
          <div className="todo-text">
            <div className="todo-title">Acil bir iş yok</div>
            <div className="todo-sub">Bekleyen uyarı, dolan lot ya da yarım kalmış belge görünmüyor.</div>
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
          <div className="section-title">Hızlı işlemler</div>
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
          <div className="section-title">Özet</div>
          <Row gutter={[12, 12]}>
            {(role === 'YONETICI' || role === 'MAGAZA') && (
              <Col xs={12} lg={6}>
                <Stat
                  label="Bugünkü satış"
                  value={formatMoney(data.today_sales_amount)}
                  hint={`${data.today_sale_count} satış belgesi`}
                  tone="success"
                  onClick={() => navigate('/gun-sonu')}
                />
              </Col>
            )}
            {(role === 'YONETICI' || role === 'DEPO') && (
              <Col xs={12} lg={6}>
                <Stat
                  label="Elimizdeki stokun değeri"
                  value={formatMoney(data.stock_value)}
                  hint="Maliyet fiyatıyla"
                  tone="brand"
                  onClick={() => navigate('/stok')}
                />
              </Col>
            )}
            <Col xs={12} lg={6}>
              <Stat
                label="Dolmak üzere / dolmuş lot"
                value={data.expiring.length}
                hint={`${data.expiry_warning_days} gün içinde ya da geçmiş`}
                tone={data.expiring.length ? 'warning' : 'neutral'}
                onClick={() => navigate('/son-kullanma')}
              />
            </Col>
            <Col xs={12} lg={6}>
              <Stat
                label="Açık geri çağırma"
                value={data.open_recalls.length}
                hint="Satışa kapalı lotlar"
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
