import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { App as AntApp, ConfigProvider } from 'antd'
import trTR from 'antd/locale/tr_TR'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App.tsx'
import { SessionProvider } from './auth/SessionProvider.tsx'
import './index.css'

const queryClient = new QueryClient({
  defaultOptions: {
    // Yetki ve iş kuralı hataları tekrar denemekle düzelmez; yalnız ağ hatası bir kez yeniden denenir.
    queries: { retry: (count, error) => count < 1 && (error as { status?: number }).status === 0 },
  },
})

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ConfigProvider
      locale={trTR}
      theme={{
        // Derinlikli görünüm: yuvarlak köşeler, mavi vurgu, açık zemin; gölgeler index.css'te.
        token: { colorPrimary: '#2563eb', borderRadius: 10, colorBgLayout: 'transparent', fontSize: 14 },
        components: {
          Layout: { headerBg: '#0b1d3a', siderBg: '#ffffff', bodyBg: 'transparent' },
          Card: { borderRadiusLG: 16 },
          Menu: { itemBorderRadius: 10, itemMarginInline: 8 },
          Table: { headerBg: '#f3f6fc', borderRadius: 12 },
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
