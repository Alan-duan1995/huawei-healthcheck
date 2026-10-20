import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// Vite 配置 - 代理 API 请求到后端服务
export default defineConfig({
  plugins: [vue()],
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
