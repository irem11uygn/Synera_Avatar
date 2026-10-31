import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { App as AntApp, ConfigProvider } from 'antd'
import enUS from 'antd/locale/en_US'
import trTR from 'antd/locale/tr_TR'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App.tsx'
import { SessionProvider } from './auth/SessionProvider.tsx'
import { lang } from './lib/i18n'
import './index.css'

document.documentElement.lang = lang

const queryClient = new QueryClient({
  defaultOptions: {
    // Yetki ve iş kuralı hataları tekrar denemekle düzelmez; yalnız ağ hatası bir kez yeniden denenir.
    queries: { retry: (count, error) => count < 1 && (error as { status?: number }).status === 0 },
  },
})

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ConfigProvider
      locale={lang === 'en' ? enUS : trTR}
      theme={{
        // Turkuaz + 3B: turkuaz ana renk, yuvarlak köşeler, 15 px yazı, büyük dokunma alanları.
        // Ana renk #0f766e: beyaz yazıyla 5,47:1 (WCAG AA 4,5:1; açık ton #0d9488 3,74:1 ile kalıyordu).
        token: {
          colorPrimary: '#0f766e',
          colorInfo: '#1d4ed8',
          colorSuccess: '#2e7d32',
          colorWarning: '#b45309',
          colorError: '#c62828',
          colorText: '#102a2a',
          colorTextSecondary: '#3f5655',
          colorBorder: '#c9dad7',
          colorBorderSecondary: '#e1ecea',
          colorBgLayout: 'transparent',
          borderRadius: 10,
          fontSize: 15,
          controlHeight: 38,
          fontFamily:
            "'Segoe UI', system-ui, -apple-system, Roboto, 'Helvetica Neue', Arial, 'Noto Sans', sans-serif",
        },
        components: {
          // Sol menü turkuaz geçiş üzerinde: koyu menü teması, saydam zemin, beyaz yazı.
          Menu: {
            itemHeight: 42,
            itemBorderRadius: 10,
            itemMarginInline: 10,
            darkItemBg: 'transparent',
            darkSubMenuItemBg: 'transparent',
            // Geçişin en açık yerinde bile en az 4,5:1 (WCAG AA); seçili ve üzerine gelinen satır koyulaşır.
            darkItemColor: 'rgba(255,255,255,0.95)',
            darkItemHoverBg: 'rgba(4,47,46,0.22)',
            darkItemHoverColor: '#ffffff',
            darkItemSelectedBg: 'rgba(4,47,46,0.35)',
            darkItemSelectedColor: '#ffffff',
            darkGroupTitleColor: 'rgba(255,255,255,0.92)',
          },
          Table: { headerBg: 'rgba(240,249,247,0.9)', headerColor: '#3f5655', cellPaddingBlock: 12, rowHoverBg: '#f0f9f7' },
          Card: { headerFontSize: 16 },
          Button: { fontWeight: 600, primaryShadow: '0 6px 14px -8px rgba(13,148,136,0.8)' },
        },
      }}
    >
      <AntApp>
        <QueryClientProvider client={queryClient}>
          <SessionProvider>
            <App />
          </SessionProvider>
        </QueryClientProvider>
      </AntApp>
    </ConfigProvider>
  </StrictMode>,
)
