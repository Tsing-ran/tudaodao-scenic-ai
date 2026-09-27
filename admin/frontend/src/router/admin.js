import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const routes = [
  {
    path: '/login',
    name: 'AdminLogin',
    component: () => import('@/views/AdminLoginView.vue'),
    meta: { title: '管理后台 · 登录' }
  },
  {
    path: '/',
    name: 'Admin',
    component: () => import('@/views/AdminView.vue'),
    meta: { title: '管理后台', requiresAuth: true }
  }
]

const router = createRouter({
  history: createWebHistory('/admin/'),
  routes
})

router.afterEach((to) => {
  document.title = (to.meta.title ? to.meta.title + ' · ' : '') + '途叨叨景区管理后台'
})

router.beforeEach(async (to) => {
  if (to.path === '/login') {
    const auth = useAuthStore()
    if (!auth.checked) await auth.checkSession()
    if (auth.user) return '/'
    return true
  }
  if (to.meta.requiresAuth) {
    const auth = useAuthStore()
    if (!auth.checked) await auth.checkSession()
    if (!auth.user) return '/login'
  }
})

export default router
