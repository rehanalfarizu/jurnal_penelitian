import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { VitePWA } from 'vite-plugin-pwa'
import path from 'path'

export default defineConfig({
  plugins: [
    vue(),
    VitePWA({
      registerType: 'prompt', // Beri user pilihan untuk update atau skip
      includeVersion: true, // Track version untuk debugging
      workbox: {
        maximumFileSizeToCacheInBytes: 15 * 1024 * 1024, // 15MB untuk bundle besar (Cesium + Babylon)
        runtimeCaching: [
          {
            urlPattern: /\/models\/.*\.glb$/,
            handler: 'CacheFirst',
            options: {
              cacheName: '3d-models-cache',
              expiration: { maxEntries: 10, maxAgeSeconds: 60 * 60 * 24 * 365 },
              cacheableResponse: { statuses: [0, 200] },
              rangeRequests: true
            }
          }
        ],
        globPatterns: ['**/*.{js,css,html,ico,png,svg,woff2}'],
        globIgnores: ['**/models/**/*', '**/models/*.glb']
      },
      manifest: {
        name: 'Digital Twin Dashboard',
        short_name: 'DTwin',
        description: 'IoT Digital Twin Dashboard',
        theme_color: '#4A90A4',
        background_color: '#1a1a2e',
        display: 'standalone'
      }
    })
  ],
  server: {
    port: 3000,
    host: true,
    open: false
  },
  build: {
    emptyOutDir: true,
    chunkSizeWarningLimit: 10000
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src')
    }
  },
  define: {
    CESIUM_BASE_URL: JSON.stringify('/cesium')
  }
})
