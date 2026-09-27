import { defineStore } from 'pinia'
import { ref } from 'vue'
import axios from 'axios'
import { applyTheme } from '@/utils/themes'

export const useAuthStore = defineStore('auth', () => {
  const user    = ref(null)   // { username, scene_type, scenic_spot_id, real_name, phone, email, department, position } 或 null
  const checked = ref(false)

  async function checkSession() {
    try {
      const res = await axios.get('/api/auth/me', { withCredentials: true })
      user.value = res.data
      applyTheme(res.data.scene_type)
    } catch {
      user.value = null
    } finally {
      checked.value = true
    }
  }

  async function login(username, password) {
    const res = await axios.post('/api/auth/login', { username, password }, { withCredentials: true })
    user.value = res.data
    applyTheme(res.data.scene_type)
  }

  // profile = { real_name, phone, email, department, position }（可选，管理人员信息）
  async function register(username, password, scene_type = 'historical', scenic_spot_id = null, profile = {}) {
    const res = await axios.post(
      '/api/auth/register',
      { username, password, scene_type, scenic_spot_id, ...profile },
      { withCredentials: true },
    )
    user.value = res.data
    applyTheme(res.data.scene_type)
  }

  async function logout(router) {
    try {
      await axios.post('/api/auth/logout', {}, { withCredentials: true })
    } catch { /* 无论后端是否报错都清空本地状态 */ }
    user.value = null
    checked.value = false
    router.push('/login')
  }

  return { user, checked, checkSession, login, register, logout }
})
