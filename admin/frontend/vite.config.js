import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

// 管理端 SPA fallback 插件：/admin/* 无扩展名路径一律转发到 admin/index.html
const adminSpaPlugin = {
  name: 'admin-spa-fallback',
  configureServer(server) {
    server.middlewares.use((req, _res, next) => {
      const pathname = req.url.split('?')[0]
      if (pathname.startsWith('/admin/') && !pathname.split('/').pop().includes('.')) {
        req.url = '/admin/index.html'
      }
      next()
    })
  }
}

export default defineConfig({
  base: '/admin/',   // 经桥接 :8443/admin/ 提供服务 → 资源路径前缀 /admin/
  plugins: [vue(), adminSpaPlugin],
  resolve: {
    alias: { '@': resolve(__dirname, 'src') }
  },
  build: {
    rollupOptions: {
      input: {
        admin: resolve(__dirname, 'admin/index.html'),
      }
    }
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true
      },
      '/cloud': {
        target: 'https://u891802-x4xd-7f8146e7.bjb2.seetacloud.com:8443',
        changeOrigin: true,
        secure: false,
        rewrite: (path) => path.replace(/^\/cloud/, '/rag')
      }
    }
  }
})
