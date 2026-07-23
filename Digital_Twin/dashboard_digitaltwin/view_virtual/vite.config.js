import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { VitePWA } from 'vite-plugin-pwa'

export default defineConfig({
  plugins: [
    vue(),
    VitePWA({
      registerType: 'autoUpdate',
      workbox: {
        // Increase maximum file size to cache (10MB)
        maximumFileSizeToCacheInBytes: 10 * 1024 * 1024,
        // Cache file 3D GLB local
        runtimeCaching: [
          {
            // Cache file GLB dari folder models
            urlPattern: /\/models\/.*\.glb$/,
            handler: 'CacheFirst',
            options: {
              cacheName: '3d-models-cache',
              expiration: {
                maxEntries: 10,
                maxAgeSeconds: 60 * 60 * 24 * 365 // 1 tahun
              },
              cacheableResponse: {
                statuses: [0, 200]
              },
              rangeRequests: true // Support partial requests untuk file besar
            }
          }
        ],
        // Pre-cache asset penting
        globPatterns: ['**/*.{js,css,html,ico,png,svg,woff2}'],
        // Jangan pre-cache file besar, biarkan runtime cache
        globIgnores: ['**/models/**/*', '**/models/*.glb', '**/models/*.blend', '**/models/*.gltf', '**/models/*.bin', '**/models/*.png']
      },
      manifest: {
        name: 'Digital Twin Dashboard',
        short_name: 'DTwin',
        description: 'IoT Digital Twin Dashboard with 3D Visualization',
        theme_color: '#4A90A4',
        background_color: '#1a1a2e',
        display: 'standalone'
      }
    })
  ],
  server: {
    port: 3000,
    host: true,
    open: true,
    hmr: {
      overlay: true
    }
  },
  build: {
    emptyOutDir: true,
    chunkSizeWarningLimit: 7000 // Increase chunk size warning limit (7MB) for Babylon.js
  },
  optimizeDeps: {
    force: true
  },
  clearScreen: false
})

