import { Button, Flex, Layout, Menu, Result, Typography, type MenuProps } from 'antd'
import { useState, type ReactNode } from 'react'
import { useSession } from './auth/context'
import { Link } from './components/Link'
import { matchPath, navigate, usePath } from './lib/router'
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
import StockPage from './pages/StockPage'
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
]

const link = (to: string, label: string) => ({ key: to, label: <Link to={to}>{label}</Link> })

const MENU: MenuProps['items'] = [
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
  { type: 'group', label: 'Görev 1', children: [link('/uretim', 'Dış üretim emirleri')] },
]

const MENU_KEYS = ['/urunler', '/cariler', '/alislar', '/stok', '/lotlar', '/transferler', '/uretim']

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

export default function App() {
  const path = usePath()
  const { user, logout } = useSession()
  // Dar ekranda menü gizlenir; üst çubuktaki "Menü" düğmesiyle açılır, bir sayfa seçilince kapanır.
  const [narrow, setNarrow] = useState(false)
  const [menuClosed, setMenuClosed] = useState(false)

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Header style={{ paddingInline: 16 }}>
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
            <Typography.Text strong style={{ color: '#fff', fontSize: 16 }} ellipsis>
              AVATAR · Üretim, Maliyet ve Lot İzlenebilirliği
            </Typography.Text>
          </Flex>
          <Flex align="center" gap="small" style={{ flexShrink: 0 }}>
            <Typography.Text style={{ color: 'rgba(255,255,255,0.85)' }}>{user.full_name}</Typography.Text>
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
              items={MENU}
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
