import {
  AlertOutlined,
  AppstoreOutlined,
  AuditOutlined,
  BarChartOutlined,
  BulbOutlined,
  CalculatorOutlined,
  CarOutlined,
  ClockCircleOutlined,
  DatabaseOutlined,
  ExperimentOutlined,
  FileSearchOutlined,
  HomeOutlined,
  InboxOutlined,
  KeyOutlined,
  LogoutOutlined,
  MailOutlined,
  MenuOutlined,
  NodeIndexOutlined,
  PercentageOutlined,
  ReloadOutlined,
  SafetyCertificateOutlined,
  SettingOutlined,
  ScissorOutlined,
  ShopOutlined,
  ShoppingCartOutlined,
  SolutionOutlined,
  TagsOutlined,
  TeamOutlined,
  ToolOutlined,
  UserOutlined,
} from '@ant-design/icons'
import { useQuery } from '@tanstack/react-query'
import { Badge, Button, Dropdown, Flex, Menu, Result, Spin, type MenuProps } from 'antd'
import { lazy, Suspense, useState, type ReactNode } from 'react'
import { api } from './api/client'
import type { AlertSummary, ReportCode, UserRole } from './api/types'
import { useSession } from './auth/context'
import { AlarmBell } from './components/AlarmBell'
import { LanguageSwitch } from './components/LanguageSwitch'
import { LotSearch } from './components/LotSearch'
import { canOpenPage, ROLE } from './lib/roles'
import { matchPath, navigate, usePath } from './lib/router'
import { t } from './lib/i18n'

// Her sayfa ayrı dosyada yüklenir: ilk açılış hızlı, kullanılmayan ekran indirilmez.
const HomePage = lazy(() => import('./pages/HomePage'))
const StoreSalePage = lazy(() => import('./pages/StoreSalePage'))
const SalesPage = lazy(() => import('./pages/SalesPage'))
const DayEndPage = lazy(() => import('./pages/DayEndPage'))
const PurchasesPage = lazy(() => import('./pages/PurchasesPage'))
const PurchaseNewPage = lazy(() => import('./pages/PurchaseNewPage'))
const StockPage = lazy(() => import('./pages/StockPage'))
const ExpiryPage = lazy(() => import('./pages/ExpiryPage'))
const StockCountPage = lazy(() => import('./pages/StockCountPage'))
const TransfersPage = lazy(() => import('./pages/TransfersPage'))
const LotsPage = lazy(() => import('./pages/LotsPage'))
const LotDetailPage = lazy(() => import('./pages/LotDetailPage'))
const ProductionListPage = lazy(() => import('./pages/ProductionListPage'))
const ProductionNewPage = lazy(() => import('./pages/ProductionNewPage'))
const ProductionDetailPage = lazy(() => import('./pages/ProductionDetailPage'))
const CuttingListPage = lazy(() => import('./pages/CuttingListPage'))
const CuttingNewPage = lazy(() => import('./pages/CuttingNewPage'))
const CuttingDetailPage = lazy(() => import('./pages/CuttingDetailPage'))
const RecipesPage = lazy(() => import('./pages/RecipesPage'))
const ReprocessingPage = lazy(() => import('./pages/ReprocessingPage'))
const TracePage = lazy(() => import('./pages/TracePage'))
const RecallsPage = lazy(() => import('./pages/RecallsPage'))
const RecallDetailPage = lazy(() => import('./pages/RecallDetailPage'))
const MockRecallPage = lazy(() => import('./pages/MockRecallPage'))
const AlertsPage = lazy(() => import('./pages/AlertsPage'))
const AuditPage = lazy(() => import('./pages/AuditPage'))
const MailPage = lazy(() => import('./pages/MailPage'))
const AlarmSettingsPage = lazy(() => import('./pages/AlarmSettingsPage'))
const CalculatorsPage = lazy(() => import('./pages/CalculatorsPage'))
const ReportsPage = lazy(() => import('./pages/ReportsPage'))
const AiPage = lazy(() => import('./pages/AiPage'))
const UsersPage = lazy(() => import('./pages/UsersPage'))
const ProductsPage = lazy(() => import('./pages/ProductsPage'))
const PartnersPage = lazy(() => import('./pages/PartnersPage'))
const ChangePasswordPage = lazy(() => import('./pages/ChangePasswordPage'))
const PrintPage = lazy(() => import('./pages/PrintPage'))

type Route = { pattern: string; render: (params: Record<string, string>) => ReactNode }

/** Yoldaki sayı geçersizse sayfa "bulunamadı" gösterir (NaN ile istek atılmaz). */
function withId(raw: string, render: (id: number) => ReactNode): ReactNode {
  const id = Number(raw)
  return Number.isInteger(id) && id > 0 ? render(id) : <NotFound />
}

// Sıra önemli: "/uretim/yeni", "/uretim/:id"den önce gelir.
const ROUTES: Route[] = [
  { pattern: '/', render: () => <HomePage /> },
  { pattern: '/magaza-satisi', render: () => <StoreSalePage /> },
  { pattern: '/satislar', render: () => <SalesPage /> },
  { pattern: '/gun-sonu', render: () => <DayEndPage /> },
  { pattern: '/alislar', render: () => <PurchasesPage /> },
  { pattern: '/alislar/yeni', render: () => <PurchaseNewPage /> },
  { pattern: '/stok', render: () => <StockPage /> },
  { pattern: '/son-kullanma', render: () => <ExpiryPage /> },
  { pattern: '/sayim', render: () => <StockCountPage /> },
  { pattern: '/transferler', render: () => <TransfersPage /> },
  { pattern: '/lotlar', render: () => <LotsPage /> },
  { pattern: '/lotlar/:lotNo', render: ({ lotNo }) => <LotDetailPage key={lotNo} lotNo={lotNo} /> },
  { pattern: '/uretim', render: () => <ProductionListPage /> },
  { pattern: '/uretim/yeni', render: () => <ProductionNewPage /> },
  { pattern: '/uretim/:id', render: ({ id }) => withId(id, (n) => <ProductionDetailPage key={n} id={n} />) },
  { pattern: '/parcalama', render: () => <CuttingListPage /> },
  { pattern: '/parcalama/yeni', render: () => <CuttingNewPage /> },
  { pattern: '/parcalama/:id', render: ({ id }) => withId(id, (n) => <CuttingDetailPage key={n} id={n} />) },
  { pattern: '/receteler', render: () => <RecipesPage /> },
  { pattern: '/yeniden-isleme', render: () => <ReprocessingPage /> },
  { pattern: '/izleme', render: () => <TracePage /> },
  { pattern: '/izleme/:lotNo', render: ({ lotNo }) => <TracePage key={lotNo} lotNo={lotNo} /> },
  {
    pattern: '/izleme/:lotNo/geri',
    render: ({ lotNo }) => <TracePage key={`${lotNo}-geri`} lotNo={lotNo} direction="backward" />,
  },
  { pattern: '/geri-cagirma', render: () => <RecallsPage /> },
  { pattern: '/geri-cagirma/:id', render: ({ id }) => withId(id, (n) => <RecallDetailPage key={n} id={n} />) },
  { pattern: '/tatbikat', render: () => <MockRecallPage /> },
  { pattern: '/alarmlar', render: () => <AlertsPage /> },
  { pattern: '/uyarilar', render: () => <AlertsPage /> },
  { pattern: '/denetim', render: () => <AuditPage /> },
  { pattern: '/e-posta', render: () => <MailPage /> },
  { pattern: '/alarm-ayarlari', render: () => <AlarmSettingsPage /> },
  { pattern: '/hesaplayicilar', render: () => <CalculatorsPage /> },
  { pattern: '/raporlar', render: () => <ReportsPage /> },
  { pattern: '/raporlar/:code', render: ({ code }) => <ReportsPage code={code as ReportCode} /> },
  { pattern: '/yapay-zeka', render: () => <AiPage /> },
  { pattern: '/kullanicilar', render: () => <UsersPage /> },
  { pattern: '/urunler', render: () => <ProductsPage /> },
  { pattern: '/cariler', render: () => <PartnersPage /> },
  { pattern: '/sifre', render: () => <ChangePasswordPage /> },
]

type NavItem = { to: string; label: string; icon: ReactNode; roles?: UserRole[]; badge?: 'alerts' }
type NavGroup = { label: string; items: NavItem[] }

const ALL: UserRole[] = ['YONETICI', 'DEPO', 'URETIM', 'KALITE', 'MAGAZA']

// Menü işe göre gruplanır; herkes yalnız kendi işinin ekranlarını görür (yönetici hepsini).
const NAV: NavGroup[] = [
  {
    label: t('Satış'),
    items: [
      { to: '/magaza-satisi', label: t('Mağaza satışı'), icon: <ShoppingCartOutlined />, roles: ['YONETICI', 'MAGAZA'] },
      { to: '/satislar', label: t('Satışlar ve iadeler'), icon: <SolutionOutlined />, roles: ['YONETICI', 'MAGAZA', 'KALITE'] },
      { to: '/gun-sonu', label: t('Gün sonu'), icon: <CalculatorOutlined />, roles: ['YONETICI', 'MAGAZA'] },
    ],
  },
  {
    label: t('Depo'),
    items: [
      { to: '/alislar', label: t('Mal kabul'), icon: <InboxOutlined />, roles: ['YONETICI', 'DEPO'] },
      { to: '/stok', label: t('Stok durumu'), icon: <DatabaseOutlined />, roles: ALL },
      { to: '/son-kullanma', label: t('Son kullanma takibi'), icon: <ClockCircleOutlined />, roles: ['YONETICI', 'DEPO', 'MAGAZA', 'KALITE'] },
      { to: '/sayim', label: t('Sayım'), icon: <AppstoreOutlined />, roles: ['YONETICI', 'DEPO'] },
      { to: '/transferler', label: t('Araca yükleme'), icon: <CarOutlined />, roles: ['YONETICI', 'DEPO'] },
      { to: '/lotlar', label: t('Lotlar (partiler)'), icon: <TagsOutlined />, roles: ALL },
    ],
  },
  {
    label: t('Üretim'),
    items: [
      { to: '/uretim', label: t('Fason üretim'), icon: <ToolOutlined />, roles: ['YONETICI', 'URETIM'] },
      { to: '/parcalama', label: t('Parçalama'), icon: <ScissorOutlined />, roles: ['YONETICI', 'URETIM'] },
      { to: '/yeniden-isleme', label: t('Yeniden işleme'), icon: <ReloadOutlined />, roles: ['YONETICI', 'URETIM'] },
      { to: '/receteler', label: t('Parçalama reçeteleri'), icon: <ExperimentOutlined />, roles: ['YONETICI', 'URETIM'] },
    ],
  },
  {
    label: t('Kalite'),
    items: [
      { to: '/izleme', label: t('Lot izleme'), icon: <NodeIndexOutlined />, roles: ALL },
      { to: '/geri-cagirma', label: t('Geri çağırma'), icon: <SafetyCertificateOutlined />, roles: ['YONETICI', 'KALITE'] },
      { to: '/tatbikat', label: t('Geri çağırma tatbikatı'), icon: <FileSearchOutlined />, roles: ['YONETICI', 'KALITE'] },
      { to: '/alarmlar', label: t('Alarm merkezi'), icon: <AlertOutlined />, roles: ALL, badge: 'alerts' },
    ],
  },
  {
    label: t('Raporlar'),
    items: [
      { to: '/raporlar', label: t('Raporlar'), icon: <BarChartOutlined />, roles: ALL },
      { to: '/e-posta', label: t('Rapor gönder (e-posta)'), icon: <MailOutlined />, roles: ALL },
      { to: '/hesaplayicilar', label: t('Ne olur hesaplayıcıları'), icon: <PercentageOutlined />, roles: ALL },
      { to: '/yapay-zeka', label: t('Yapay zekâ tahminleri'), icon: <BulbOutlined />, roles: ['YONETICI', 'URETIM'] },
    ],
  },
  {
    label: t('Yönetim'),
    items: [
      { to: '/kullanicilar', label: t('Kullanıcılar'), icon: <TeamOutlined />, roles: ['YONETICI'] },
      { to: '/urunler', label: t('Ürünler ve fiyatlar'), icon: <ShopOutlined />, roles: ['YONETICI'] },
      { to: '/cariler', label: t('Müşteri ve tedarikçiler'), icon: <UserOutlined />, roles: ['YONETICI', 'DEPO', 'MAGAZA'] },
      { to: '/alarm-ayarlari', label: t('Alarm ve e-posta ayarları'), icon: <SettingOutlined />, roles: ['YONETICI'] },
      { to: '/denetim', label: t('Denetim günlüğü'), icon: <AuditOutlined />, roles: ['YONETICI'] },
    ],
  },
]

const ALL_KEYS = NAV.flatMap((group) => group.items.map((item) => item.to))

function selectedKey(path: string): string {
  return ALL_KEYS.find((key) => path === key || path.startsWith(`${key}/`)) ?? '/'
}

function NotFound() {
  return (
    <Result
      status="404"
      title={t('Sayfa bulunamadı')}
      subTitle={t('Adres yanlış ya da kayıt silinmiş olabilir.')}
      extra={
        <Button type="primary" onClick={() => navigate('/')}>
          {t('Ana sayfaya dön')}
        </Button>
      }
    />
  )
}

function Forbidden() {
  return (
    <Result
      status="403"
      title={t('Bu ekrana yetkiniz yok')}
      subTitle={t('Bu ekran rolünüzün işine dahil değil; gerekiyorsa yöneticinize başvurun.')}
      extra={
        <Button type="primary" onClick={() => navigate('/')}>
          {t('Ana sayfaya dön')}
        </Button>
      }
    />
  )
}

function renderRoute(path: string, role: UserRole): ReactNode {
  if (!canOpenPage(path, role)) return <Forbidden />
  for (const route of ROUTES) {
    const params = matchPath(route.pattern, path)
    if (params) return route.render(params)
  }
  return <NotFound />
}

const loading = (
  <Flex justify="center" style={{ padding: 64 }}>
    <Spin size="large" />
  </Flex>
)

function menuItems(role: UserRole, openAlerts: number, go: (to: string) => void): MenuProps['items'] {
  const entry = (item: NavItem) => ({
    key: item.to,
    icon: item.icon,
    label: (
      <a
        href={item.to}
        onClick={(event) => {
          if (event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey) return
          event.preventDefault()
          go(item.to)
        }}
      >
        <Flex justify="space-between" align="center" gap="small">
          {item.label}
          {item.badge === 'alerts' && openAlerts > 0 && (
            <Badge count={openAlerts} size="small" aria-label={t('{n} okunmamış uyarı', { n: openAlerts })} />
          )}
        </Flex>
      </a>
    ),
  })
  const groups = NAV.map((group) => ({
    type: 'group' as const,
    label: group.label,
    children: group.items.filter((item) => !item.roles || item.roles.includes(role)).map(entry),
  })).filter((group) => group.children.length > 0)
  return [entry({ to: '/', label: t('Ana sayfa'), icon: <HomeOutlined /> }), ...groups]
}

export default function App() {
  const path = usePath()
  const { user, logout } = useSession()
  const [menuOpen, setMenuOpen] = useState(false)

  // Yazdırma sayfaları çerçevesiz açılır (yalnız belge ve "Yazdır" düğmesi).
  if (path.startsWith('/yazdir/')) {
    return <Suspense fallback={loading}>{<PrintPage path={path} />}</Suspense>
  }

  return (
    <Shell path={path} menuOpen={menuOpen} setMenuOpen={setMenuOpen} userName={user.full_name} role={user.role} logout={logout} />
  )
}

function Shell({
  path,
  menuOpen,
  setMenuOpen,
  userName,
  role,
  logout,
}: {
  path: string
  menuOpen: boolean
  setMenuOpen: (open: boolean) => void
  userName: string
  role: UserRole
  logout: () => Promise<void>
}) {
  // Açık alarm sayısı zilde ve menüde görünür; yeni alarm köşede bildirilir (30 sn'de bir bakılır).
  const alerts = useQuery({
    queryKey: ['alerts', 'summary'],
    queryFn: () => api<AlertSummary>('/alerts/summary'),
    refetchInterval: 30_000,
  })

  const go = (to: string) => {
    setMenuOpen(false)
    navigate(to)
  }

  const userMenu: MenuProps['items'] = [
    { key: 'role', label: ROLE[role], disabled: true },
    { type: 'divider' },
    { key: 'password', icon: <KeyOutlined />, label: t('Şifremi değiştir'), onClick: () => go('/sifre') },
    { key: 'logout', icon: <LogoutOutlined />, label: t('Çıkış'), danger: true, onClick: () => void logout() },
  ]

  return (
    <div className={`shell${menuOpen ? ' is-menu-open' : ''}`}>
      <aside className="shell-sider" aria-label={t('Ana menü')}>
        <a
          className="shell-brand"
          href="/"
          onClick={(event) => {
            event.preventDefault()
            go('/')
          }}
        >
          <span className="shell-brand-mark" aria-hidden="true">
            S
          </span>
          <span>
            <span className="shell-brand-name">Synera</span>
            <br />
            <span className="shell-brand-sub">{t('Üretim · Stok · Satış · İzlenebilirlik')}</span>
          </span>
        </a>
        <nav className="shell-nav" id="ana-menu">
          <Menu mode="inline" theme="dark" items={menuItems(role, alerts.data?.open_total ?? 0, go)} selectedKeys={[selectedKey(path)]} />
        </nav>
      </aside>
      <div className="shell-backdrop" onClick={() => setMenuOpen(false)} aria-hidden="true" />
      <div className="shell-main">
        <header className="shell-topbar">
          <Button
            className="shell-menu-button"
            icon={<MenuOutlined />}
            aria-label={t('Menüyü aç')}
            aria-expanded={menuOpen}
            aria-controls="ana-menu"
            onClick={() => setMenuOpen(!menuOpen)}
          />
          <LotSearch />
          <span style={{ marginLeft: 'auto' }}>
            <LanguageSwitch />
          </span>
          <AlarmBell summary={alerts.data} />
          <Dropdown menu={{ items: userMenu }} trigger={['click']} placement="bottomRight">
            <Button icon={<UserOutlined />} aria-label={t('Hesap: {name}', { name: userName })}>
              <span className="shell-user-name">{userName}</span>
            </Button>
          </Dropdown>
        </header>
        <main className="shell-content">
          <Suspense fallback={loading}>{renderRoute(path, role)}</Suspense>
        </main>
      </div>
    </div>
  )
}
