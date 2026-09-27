import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'
import AdminApp from './AdminApp.vue'
import router from './router/admin'
import './styles/main.css'
import './styles/admin-dark.css'

// ── 浅 / 深色模式切换 ──────────────────────────────────────────
// 深色 = <html>.admin-dark（霓虹 CRM，所有深色样式都 scope 在此类下）；
// 浅色 = 去掉该类，队友原版浅色样式原样复活。默认深色，偏好存 localStorage。
const THEME_KEY = 'admin-theme'
let _mode = localStorage.getItem(THEME_KEY) || 'dark'
const applyAdminTheme = (m) => document.documentElement.classList.toggle('admin-dark', m === 'dark')
applyAdminTheme(_mode)

const ICON_SUN  = '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"><circle cx="12" cy="12" r="4.2"/><path d="M12 2v2.2M12 19.8V22M4.2 4.2l1.6 1.6M18.2 18.2l1.6 1.6M2 12h2.2M19.8 12H22M4.2 19.8l1.6-1.6M18.2 5.8l1.6-1.6"/></svg>'
const ICON_MOON = '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"/></svg>'

function mountThemeToggle() {
  if (document.getElementById('admin-theme-toggle')) return
  const btn = document.createElement('button')
  btn.id = 'admin-theme-toggle'
  btn.type = 'button'
  const render = () => {
    // 显示「切换到的目标模式」
    btn.innerHTML = (_mode === 'dark' ? ICON_SUN + '<span>浅色</span>' : ICON_MOON + '<span>深色</span>')
    btn.setAttribute('aria-label', _mode === 'dark' ? '切换到浅色模式' : '切换到深色模式')
  }
  render()
  btn.addEventListener('click', () => {
    _mode = _mode === 'dark' ? 'light' : 'dark'
    localStorage.setItem(THEME_KEY, _mode)
    applyAdminTheme(_mode)
    render()
    // 通知图表（echarts 配置随模式切换，需重绘）
    window.dispatchEvent(new Event('admin-theme-change'))
  })
  document.body.appendChild(btn)
}

const app = createApp(AdminApp)

for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component)
}

app.use(createPinia())
app.use(router)
app.use(ElementPlus)
app.mount('#app')
// theme toggle moved into sidebar Vue component
// mountThemeToggle()
