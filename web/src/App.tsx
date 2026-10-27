import { useQuery } from '@tanstack/react-query'
import { Badge, Button, Flex, Layout, Menu, Result, Typography, type MenuProps } from 'antd'
import { useState, type ReactNode } from 'react'
import { api } from './api/client'
import type { AlertRow, ReportCode } from './api/types'
import { useSession } from './auth/context'
import { Link } from './components/Link'
import { matchPath, navigate, usePath } from './lib/router'
import AiPage from './pages/AiPage'
import AlertsPage from './pages/AlertsPage'
import CuttingDetailPage from './pages/CuttingDetailPage'
import CuttingListPage from './pages/CuttingListPage'
import CuttingNewPage from './pages/CuttingNewPage'
import HomePage from './pages/HomePage'
import LotDetailPage from './pages/LotDetailPage'
import LotsPage from './pages/LotsPage'
import PartnersPage from './pages/PartnersPage'
import ProductionDetailPage from './pages/ProductionDetailPage'
import ProductionListPage from './pages/ProductionListPage'
import ProductionNewPage from './pages/ProductionNewPage'
import ProductsPage from './pages/ProductsPage'
import PurchaseNewPage from './pages/PurchaseNewPage'
import PurchasesPage from './pages/PurchasesPage'
import RecallDetailPage from './pages/RecallDetailPage'
import RecallsPage from './pages/RecallsPage'
import RecipesPage from './pages/RecipesPage'
import ReportsPage from './pages/ReportsPage'
import ReprocessingPage from './pages/ReprocessingPage'
import SalesPage from './pages/SalesPage'
import StockPage from './pages/StockPage'
import TracePage from './pages/TracePage'
import TransfersPage from './pages/TransfersPage'

const { Header, Sider, Content } = Layout

type Route = { pattern: string; render: (params: Record<string, string>) => ReactNode }

// Sıra önemli: "/uretim/yeni", "/uretim/:id"den önce gelir.
const ROUTES: Route[] = [
  { pattern: '/', render: () => <HomePage /> },
  { pattern: '/urunler', render: () => <ProductsPage /> },
  { pattern: '/cariler', render: () => <PartnersPage /> },
  { pattern: '/alislar', render: () => <PurchasesPage /> },
  { pattern: '/alislar/yeni', render: () => <PurchaseNewPage /> },
  { pattern: '/stok', render: () => <StockPage /> },
  { pattern: '/lotlar', render: () => <LotsPage /> },
  { pattern: '/lotlar/:lotNo', render: ({ lotNo }) => <LotDetailPage lotNo={lotNo} /> },
  { pattern: '/transferler', render: () => <TransfersPage /> },
  { pattern: '/uretim', render: () => <ProductionListPage /> },
  { pattern: '/uretim/yeni', render: () => <ProductionNewPage /> },
  { pattern: '/uretim/:id', render: ({ id }) => <ProductionDetailPage id={Number(id)} /> },
  { pattern: '/parcalama', render: () => <CuttingListPage /> },
  { pattern: '/parcalama/yeni', render: () => <CuttingNewPage /> },
  { pattern: '/parcalama/:id', render: ({ id }) => <CuttingDetailPage id={Number(id)} /> },
  { pattern: '/receteler', render: () => <RecipesPage /> },
  { pattern: '/satislar', render: () => <SalesPage /> },
  { pattern: '/yeniden-isleme', render: () => <ReprocessingPage /> },
  { pattern: '/izleme', render: () => <TracePage /> },
  { pattern: '/izleme/:lotNo', render: ({ lotNo }) => <TracePage key={lotNo} lotNo={lotNo} /> },
  {
    pattern: '/izleme/:lotNo/geri',
    render: ({ lotNo }) => <TracePage key={`${lotNo}-geri`} lotNo={lotNo} direction="backward" />,
  },
  { pattern: '/geri-cagirma', render: () => <RecallsPage /> },
  { pattern: '/geri-cagirma/:id', render: ({ id }) => <RecallDetailPage id={Number(id)} /> },
  { pattern: '/uyarilar', render: () => <AlertsPage /> },
  { pattern: '/raporlar', render: () => <ReportsPage /> },
  { pattern: '/raporlar/:code', render: ({ code }) => <ReportsPage code={code as ReportCode} /> },
  { pattern: '/yapay-zeka', render: () => <AiPage /> },
]

const link = (to: string, label: string) => ({ key: to, label: <Link to={to}>{label}</Link> })

function menuItems(openAlerts: number): MenuProps['items'] {
  return [
    link('/', 'Ana sayfa'),
    { type: 'group', label: 'Ana veriler', children: [link('/urunler', 'Ürünler'), link('/cariler', 'Cariler')] },
    {
      type: 'group',
      label: 'Stok ve lotlar',
      children: [
        link('/alislar', 'Hammadde alışları'),
        link('/stok', 'Stok durumu'),
        link('/lotlar', 'Lotlar'),
        link('/transferler', 'Transferler'),
      ],
    },
    {
      type: 'group',
      label: 'Görev 1 — üretim',
      children: [link('/uretim', 'Dış üretim emirleri'), link('/yeniden-isleme', 'Yeniden işleme')],
    },
    {
      type: 'group',
      label: 'Görev 2 — parçalama ve satış',
      children: [link('/parcalama', 'Parçalama'), link('/receteler', 'Parçalama reçeteleri'), link('/satislar', 'Satışlar ve iadeler')],
    },
    {
      type: 'group',
      label: 'Görev 3 — izlenebilirlik',
      children: [
        link('/izleme', 'Lot izleme'),
        link('/geri-cagirma', 'Geri çağırma'),
        {
          key: '/uyarilar',
          label: (
            <Link to="/uyarilar">
              <Flex justify="space-between" align="center" gap="small">
                Uyarılar
                <Badge count={openAlerts} size="small" aria-label={`${openAlerts} okunmamış uyarı`} />
              </Flex>
            </Link>
          ),
        },
      ],
    },
    {
      type: 'group',
      label: 'Analiz',
      children: [link('/raporlar', 'Raporlar'), link('/yapay-zeka', 'Yapay zekâ')],
    },
  ]
}

const MENU_KEYS = [
  '/urunler',
  '/cariler',
  '/alislar',
  '/stok',
  '/lotlar',
  '/transferler',
  '/uretim',
  '/parcalama',
  '/receteler',
  '/satislar',
  '/yeniden-isleme',
  '/izleme',
  '/geri-cagirma',
  '/uyarilar',
  '/raporlar',
  '/yapay-zeka',
]

function selectedKey(path: string): string {
  return MENU_KEYS.find((key) => path === key || path.startsWith(`${key}/`)) ?? '/'
}

function renderRoute(path: string): ReactNode {
  for (const route of ROUTES) {
    const params = matchPath(route.pattern, path)
    if (params) return route.render(params)
  }
  return (
    <Result
      status="404"
      title="Sayfa bulunamadı"
      extra={
        <Button type="primary" onClick={() => navigate('/')}>
          Ana sayfaya dön
        </Button>
      }
    />
  )
}

// antd "lg" kırılım noktası (992 px) altı.
function isNarrowScreen(): boolean {
  return window.matchMedia('(max-width: 991.98px)').matches
}

export default function App() {
  const path = usePath()
  const { user, logout } = useSession()
  // Dar ekranda menü gizlenir; üst çubuktaki "Menü" düğmesiyle açılır, bir sayfa seçilince kapanır.
  // Başlangıç değeri ekran genişliğinden: menü açık başlayıp kapanırsa o arada tıklama menüye gider.
  const [narrow, setNarrow] = useState(isNarrowScreen)
  const [menuClosed, setMenuClosed] = useState(isNarrowScreen)
  // Okunmamış uyarı sayısı menüde görünür (ör. geri çağrılmış lotun çevrimdışı satışı).
  const alerts = useQuery({
    queryKey: ['alerts', true],
    queryFn: () => api<AlertRow[]>('/alerts', { query: { only_open: true } }),
    refetchInterval: 60_000,
  })

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Header className="app-header" style={{ paddingInline: 16 }}>
        <Flex justify="space-between" align="center" gap="small" style={{ height: '100%' }}>
          <Flex align="center" gap="small" style={{ minWidth: 0 }}>
            {narrow && (
              <Button
                size="small"
                aria-expanded={!menuClosed}
                aria-controls="ana-menu"
                onClick={() => setMenuClosed((closed) => !closed)}
              >
                Menü
              </Button>
            )}
            <Link to="/">
              <span className="app-brand">
                <span className="app-brand-mark" aria-hidden="true">
                  A
                </span>
                <Typography.Text strong style={{ color: '#fff', fontSize: 16 }} ellipsis>
                  AVATAR · Synera<span className="app-brand-long"> — Üretim, Maliyet ve Lot İzlenebilirliği</span>
                </Typography.Text>
              </span>
            </Link>
          </Flex>
          <Flex align="center" gap="small" style={{ flexShrink: 0 }}>
            <Typography.Text className="app-user" style={{ color: 'rgba(255,255,255,0.85)' }}>
              {user.full_name}
            </Typography.Text>
            <Button size="small" onClick={logout}>
              Çıkış
            </Button>
          </Flex>
        </Flex>
      </Header>
      <Layout>
        <Sider
          breakpoint="lg"
          collapsedWidth={0}
          width={220}
          theme="light"
          className="app-sider"
          trigger={null}
          collapsed={menuClosed}
          // Dar ekranda menü içeriği itmez, üzerine açılır.
          style={narrow ? { position: 'fixed', top: 64, bottom: 0, left: 0, zIndex: 100, overflowY: 'auto' } : undefined}
          onBreakpoint={(broken) => {
            setNarrow(broken)
            setMenuClosed(broken)
          }}
        >
          <nav id="ana-menu" aria-label="Ana menü">
            <Menu
              mode="inline"
              items={menuItems(alerts.data?.length ?? 0)}
              selectedKeys={[selectedKey(path)]}
              onClick={() => narrow && setMenuClosed(true)}
              style={{ borderInlineEnd: 0 }}
            />
          </nav>
        </Sider>
        {/* Content zaten <main> öğesidir. */}
        <Content style={{ padding: narrow ? 16 : 24, minWidth: 0 }}>{renderRoute(path)}</Content>
      </Layout>
    </Layout>
  )
}
