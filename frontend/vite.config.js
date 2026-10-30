import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const appName = env.VITE_APP_NAME || 'UidCore'
  const appDescription = env.VITE_APP_DESCRIPTION || 'UidCore — Template Financeiro Multi-Nicho'

  return {
    plugins: [
      react(),
      {
        name: 'inject-app-name',
        transformIndexHtml(html) {
          return html
            .replace(/__APP_NAME__/g, appName)
            .replace(/__APP_DESCRIPTION__/g, appDescription)
        },
      },
    ],
    server: {
      port: 3000,
      proxy: {
        '/api': {
          target: 'http://localhost:8000',
          changeOrigin: true,
        },
      },
    },
  }
})
