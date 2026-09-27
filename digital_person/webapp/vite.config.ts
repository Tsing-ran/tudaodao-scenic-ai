import path from 'path'
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: { '@': path.resolve(__dirname, './src') },
  },
  server: {
    host: true,
    // 开发期把后端/流量代理到桥接(:9000)，前端单源调用（与生产一致）
    proxy: {
      '/rag': 'http://localhost:9000',
      '/live': 'http://localhost:9000',
      '/hls': 'http://localhost:9000',
      '/stream.flv': 'http://localhost:9000',
      '/vendor': 'http://localhost:9000',
    },
  },
})
