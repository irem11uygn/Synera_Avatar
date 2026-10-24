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
    <ConfigProvider locale={trTR}>
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
