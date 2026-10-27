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
        // Sade, okunaklı iş uygulaması: düz yüzeyler, 15 px yazı, büyük dokunma alanları.
        token: {
          colorPrimary: '#0f766e',
          colorInfo: '#1d4ed8',
          colorSuccess: '#2e7d32',
          colorWarning: '#b45309',
          colorError: '#c62828',
          colorText: '#1f2328',
          colorTextSecondary: '#4b5563',
          colorBorder: '#d5dae0',
          colorBorderSecondary: '#e3e6ea',
          colorBgLayout: '#f4f5f7',
          borderRadius: 8,
          fontSize: 15,
          controlHeight: 38,
          fontFamily:
            "'Segoe UI', system-ui, -apple-system, Roboto, 'Helvetica Neue', Arial, 'Noto Sans', sans-serif",
        },
        components: {
          Menu: { itemHeight: 42, itemBorderRadius: 6, itemMarginInline: 10, itemSelectedBg: '#e6f4f2', itemSelectedColor: '#0b5d57' },
          Table: { headerBg: '#f8f9fb', headerColor: '#4b5563', cellPaddingBlock: 12, rowHoverBg: '#f8f9fb' },
          Card: { headerFontSize: 16 },
          Button: { fontWeight: 550 },
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
