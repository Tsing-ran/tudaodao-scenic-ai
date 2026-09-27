export const SCENES = [
  {
    key:   'historical',
    name:  '历史古迹',
    desc:  '文化遗址 · 古建 · 寺庙',
    color: '#2F7CF6',
  },
  {
    key:   'natural',
    name:  '自然山水',
    desc:  '山岳 · 森林 · 湖泊湿地',
    color: '#0E9CC7',
  },
  {
    key:   'coastal',
    name:  '海滨滨水',
    desc:  '海岸 · 沙滩 · 港湾水上',
    color: '#38A8E8',
  },
  {
    key:   'desert',
    name:  '沙漠西域',
    desc:  '大漠 · 戈壁 · 丝路遗迹',
    color: '#5B7FD4',
  },
  {
    key:   'park',
    name:  '城市公园',
    desc:  '都市绿地 · 生态 · 休闲',
    color: '#4D9AF0',
  },
]

/* 浅色模式主题色盘（2026-07-11 全面调淡：弃 HHU 深藏蓝，改天青蓝系；
   深色模式的 --c-gold* 在 admin-dark.css 里带 !important，不受此处内联覆盖影响） */
export const THEMES = {
  historical: {
    '--c-gold-dark': '#1B5FD9',
    '--c-gold':      '#2F7CF6',
    '--c-gold-2':    '#5B9CF8',
    '--c-gold-3':    '#8FBFFA',
    '--c-gold-bg':   '#E8F2FF',
    '--c-gold-bdr':  '#C7DDFB',
  },
  natural: {
    '--c-gold-dark': '#067A9E',
    '--c-gold':      '#0E9CC7',
    '--c-gold-2':    '#3DB8DC',
    '--c-gold-3':    '#8ADCF0',
    '--c-gold-bg':   '#E6F7FC',
    '--c-gold-bdr':  '#B8E6F4',
  },
  coastal: {
    '--c-gold-dark': '#0284C7',
    '--c-gold':      '#38A8E8',
    '--c-gold-2':    '#5FBFF2',
    '--c-gold-3':    '#93D8F8',
    '--c-gold-bg':   '#E7F6FF',
    '--c-gold-bdr':  '#B5E0FA',
  },
  desert: {
    '--c-gold-dark': '#3B5BA8',
    '--c-gold':      '#5B7FD4',
    '--c-gold-2':    '#7DA0E4',
    '--c-gold-3':    '#A9C4F0',
    '--c-gold-bg':   '#ECF1FC',
    '--c-gold-bdr':  '#C8D8F5',
  },
  park: {
    '--c-gold-dark': '#2580C8',
    '--c-gold':      '#4D9AF0',
    '--c-gold-2':    '#74B3F5',
    '--c-gold-3':    '#A5CFF9',
    '--c-gold-bg':   '#EAF4FE',
    '--c-gold-bdr':  '#C3DEFB',
  },
}

export function applyTheme(sceneType) {
  const theme = THEMES[sceneType] || THEMES.historical
  const root = document.documentElement
  Object.entries(theme).forEach(([key, val]) => root.style.setProperty(key, val))
}
