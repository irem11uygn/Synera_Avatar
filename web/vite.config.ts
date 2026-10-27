import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// Geliştirmede /api istekleri yerelde çalışan API'ye yönlendirilir; Docker'da bunu nginx yapar.
// API portu docker-compose ile aynı değişkenden okunur (8000 doluysa ör. API_PORT=18000).
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': `http://localhost:${process.env.API_PORT ?? '8000'}`,
    },
  },
})
