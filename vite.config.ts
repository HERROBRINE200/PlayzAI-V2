import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, '.', 'VITE_')
  return {
    plugins: [react()],
    base: './',
    server: {
      host: '0.0.0.0',
      port: 4173,
      strictPort: false,
      allowedHosts: true,
      proxy: {
        '/playzai-backend': {
          target: env.VITE_DEV_BACKEND_URL || 'http://127.0.0.1:8000',
          changeOrigin: true,
          ws: true,
          rewrite: path => path.replace(/^\/playzai-backend/, ''),
        },
      },
    },
  }
})
