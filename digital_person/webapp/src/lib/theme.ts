// 景区主题换肤 + 深色模式：改 CSS 变量即可整站换色（全站已 token 化）。
import * as api from './api'

// 切景区时套用该景区主题色到根元素 CSS 变量（覆盖 index.css 的默认/暗色）。
// 返回该景区导游名（UI 文案动态化用），取不到时回退通用名。
export async function applyScenicTheme(scenic: string): Promise<string> {
  try {
    const t = await api.getTheme(scenic)
    const root = document.documentElement
    root.style.setProperty('--primary', t.primary)
    root.style.setProperty('--ring', t.primary)
    root.style.setProperty('--sweet', t.sweet)
    // 主色/点缀色都是中明度彩色 → 其上文字恒用近白，保证对比度
    root.style.setProperty('--primary-foreground', 'oklch(0.99 0.012 0)')
    root.style.setProperty('--sweet-foreground', 'oklch(0.99 0.012 0)')
    // 数字人对外名 = 后端 guide_name（已统一「<景区简称>AI智能导览数字人」，去人名化）。
    // 动态取值（品牌铁律），不再前端写死；取不到回退通用名。
    return t.guide_name || '智能导览'
  } catch { return '智能导览' /* 取不到就用默认主题 */ }
}

export type DarkMode = 'light' | 'dark' | 'system'
const DARK_KEY = 'lingjing.dark'

export function loadDarkMode(): DarkMode {
  try { return (localStorage.getItem(DARK_KEY) as DarkMode) || 'system' } catch { return 'system' }
}

export function applyDarkMode(mode: DarkMode) {
  try { localStorage.setItem(DARK_KEY, mode) } catch { /* ignore */ }
  const prefersDark = window.matchMedia?.('(prefers-color-scheme: dark)').matches
  const dark = mode === 'dark' || (mode === 'system' && prefersDark)
  document.documentElement.classList.toggle('dark', dark)
}
