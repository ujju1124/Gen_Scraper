import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        secure: false,
        cookieDomainRewrite: 'localhost',
        // Enable SSE support
        configure: (proxy, _options) => {
          proxy.on('proxyReq', (proxyReq, req, _res) => {
            // For SSE endpoints, set appropriate headers
            if (req.url.includes('/stream')) {
              proxyReq.setHeader('Accept', 'text/event-stream')
              proxyReq.setHeader('Cache-Control', 'no-cache')
              proxyReq.setHeader('Connection', 'keep-alive')
            }
          })
        }
      }
    }
  },
  define: {
    // Make environment variables available
    'import.meta.env': 'import.meta.env'
  }
})
