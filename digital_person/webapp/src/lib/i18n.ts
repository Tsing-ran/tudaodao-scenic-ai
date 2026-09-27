// 轻量 i18n：UI 文案多语言；数字人口播答案由后端 lang 参数驱动。
export type Lang = 'zh' | 'en' | 'ja' | 'ko'

export const LANGS: { id: Lang; label: string; backend: string }[] = [
  { id: 'zh', label: '中文', backend: 'zh' },
  { id: 'en', label: 'English', backend: 'en' },
  { id: 'ja', label: '日本語', backend: 'ja' },
  { id: 'ko', label: '한국어', backend: 'ko' },
]

type Dict = Record<string, string>
const ZH: Dict = {
  subtitle: 'AI 数字人导游',
  start: '开始导览', waking: '正在唤醒…',
  placeholderOn: '问点什么…', placeholderOff: '点「开始导览」连接', listening: '正在聆听…', recognizing: '识别中…',
  thinking: '{guide}正在思考', intro: '点上方「开始导览」连接数字人，TA 会主动和你打招呼，随后可语音、打字提问，或拍照让我帮你定位讲解。',
  stage_hint: '你的 AI 导游已就位，点亮和 TA 打个招呼',
  st_idle: '未连接', st_connecting: '连接中', st_buffering: '缓冲中', st_connected: '已连接', st_error: '播放失败',
  greet_pill: '主动迎宾',
  // onboarding（数字人迎宾式开场）
  ob_greet: '你好呀，我是你的 AI 导游',
  ob_greet_sub: '告诉我你想去哪、喜欢什么，这一程交给我',
  ob_guide_wait: '{guide} 在这里等你',
  ob_scenic: '想逛哪个景区', ob_who: '和谁一起', ob_interest: '感兴趣的（可多选）',
  ob_enter: '进入导览', ob_skip: '跳过，直接开始',
  ob_replay: '重看开场', ob_replay_sub: '重新选择景区与偏好',
  // today card
  today: '今日游园', today_tip: '贴心建议',
  // settings
  set_title: '设置', set_lang: '语言', set_elder: '适老模式（大字·慢语速·语音优先）',
  set_autonarrate: '走到景点自动讲解', set_autonarrate_sub: '走近景点 50 米，数字人自动开讲（需定位授权·已连接）',
  geo_arrived: '已到达 {name}，为你讲解',
  set_avatar: '数字人形象', set_avatar_sub: '形象·服饰·声音，在景区默认上精调',
  // 结束导览 + 告别（去人名化：用 {guide}/{scenic} 占位，文案温暖不生硬）
  end_tour: '结束这次导览', end_tour_sub: '和向导道个别，收下你的旅行明信片',
  farewell: '今天的{scenic}之行就到这儿啦，谢谢你一路上和我聊了这么多。{guide}把这段旅程做成了一张明信片送给你，愿这里的好风景一直记在你心里，下次再来找我玩呀。',
  set_appearance: '外观', mode_light: '浅色', mode_dark: '深色', mode_system: '跟随系统',
  // quick funcs
  qf_photo: '拍照定位', qf_tour: '跟我游', qf_gps: '定位', qf_facility: '设施', qf_trace: '足迹',
  // onboarding 向导（多步引导）
  ob_back: '返回', ob_next: '下一步', ob_start_btn: '开始', ob_skip_short: '跳过',
  ob_step1_title: '想逛哪个景区？', ob_step1_sub: '选好了，我就是这里的专属导游',
  ob_step2_title: '和谁一起来？', ob_step2_sub: '我会照顾到同行的每个人',
  ob_first_q: '第一次来吗？',
  ob_step3_title: '打算怎么逛？', ob_step3_sub: '按你的节奏和脚力来安排',
  ob_pace_q: '游览节奏', ob_mobility_q: '出行方式',
  ob_step4_title: '此行最想要什么？', ob_step4_sub: '说说心情，我把行程调成你的味道',
  ob_age_q: '你的年龄段',
  ob_step5_title: '还喜欢点什么？', ob_step5_sub: '挑几个感兴趣的，多讲你爱听的（可多选）',
}
const EN: Dict = {
  subtitle: 'AI Digital Tour Guide',
  start: 'Start Tour', waking: 'Waking up…',
  placeholderOn: 'Ask me anything…', placeholderOff: 'Tap “Start Tour” to connect', listening: 'Listening…', recognizing: 'Recognizing…',
  thinking: '{guide} is thinking', intro: 'Tap “Start Tour” to connect. Your guide will greet you, then you can ask by voice or text, or take a photo for on-site explanation.',
  stage_hint: 'Your AI guide is ready — tap to say hello',
  st_idle: 'Offline', st_connecting: 'Connecting', st_buffering: 'Buffering', st_connected: 'Live', st_error: 'Playback failed',
  greet_pill: 'Welcome',
  ob_greet: 'Hi, I’m your AI tour guide',
  ob_greet_sub: 'Tell me where you’re headed and what you love — I’ll take it from here',
  ob_guide_wait: '{guide} is waiting for you here',
  ob_scenic: 'Which scenic area', ob_who: 'Who’s with you', ob_interest: 'Your interests (multi-select)',
  ob_enter: 'Enter', ob_skip: 'Skip & start',
  ob_replay: 'Replay intro', ob_replay_sub: 'Re-pick scenic area & preferences',
  today: 'Today', today_tip: 'Tip',
  set_title: 'Settings', set_lang: 'Language', set_elder: 'Senior mode (big text · slow · voice-first)',
  set_autonarrate: 'Auto-narrate on arrival', set_autonarrate_sub: 'Within 50m of a spot, your guide starts talking (needs location · connected)',
  geo_arrived: 'Arrived at {name} — here’s the story',
  set_avatar: 'Digital Guide', set_avatar_sub: 'Look · outfit · voice, fine-tune on defaults',
  end_tour: 'End this tour', end_tour_sub: 'Say goodbye to your guide and get your postcard',
  farewell: 'That’s a wrap on your {scenic} tour — thank you for all the chats along the way. {guide} has turned this journey into a postcard for you. May these views stay with you, and come find me again next time.',
  set_appearance: 'Appearance', mode_light: 'Light', mode_dark: 'Dark', mode_system: 'System',
  qf_photo: 'Photo Locate', qf_tour: 'Tour', qf_gps: 'Locate', qf_facility: 'Spots', qf_trace: 'Trail',
  ob_back: 'Back', ob_next: 'Next', ob_start_btn: 'Start', ob_skip_short: 'Skip',
  ob_step1_title: 'Which scenic area?', ob_step1_sub: 'Pick one and I’m your private guide here',
  ob_step2_title: 'Who’s with you?', ob_step2_sub: 'I’ll look after everyone in your group',
  ob_first_q: 'First time here?',
  ob_step3_title: 'How do you want to explore?', ob_step3_sub: 'I’ll plan around your pace and energy',
  ob_pace_q: 'Pace', ob_mobility_q: 'Getting around',
  ob_step4_title: 'What do you want most?', ob_step4_sub: 'Tell me the vibe — I’ll tune the trip to it',
  ob_age_q: 'Your age group',
  ob_step5_title: 'Anything you love?', ob_step5_sub: 'Pick a few — I’ll talk more about what you like (multi-select)',
}
const JA: Dict = {
  subtitle: 'AI デジタルガイド',
  start: 'ガイド開始', waking: '起動中…',
  placeholderOn: '何でも聞いてね…', placeholderOff: '「ガイド開始」で接続', listening: '聞いています…', recognizing: '認識中…',
  thinking: '{guide}が考え中', intro: '「ガイド開始」で接続。ガイドが挨拶し、音声や文字で質問、写真で現地解説もできます。',
  stage_hint: 'AI ガイドが待機中 — タップして挨拶しよう',
  st_idle: '未接続', st_connecting: '接続中', st_buffering: 'バッファ中', st_connected: '接続済み', st_error: '再生失敗',
  greet_pill: 'ようこそ',
  ob_greet: 'こんにちは、あなたの AI ガイドです',
  ob_greet_sub: '行き先と好みを教えてね、あとは任せて',
  ob_guide_wait: '{guide}がここで待っています',
  ob_scenic: 'どの観光地', ob_who: '誰と一緒', ob_interest: '興味（複数選択可）',
  ob_enter: '入る', ob_skip: 'スキップして開始',
  ob_replay: 'オープニングを再表示', ob_replay_sub: '観光地と好みを選び直す',
  today: '本日', today_tip: 'ヒント',
  set_title: '設定', set_lang: '言語', set_elder: 'シニアモード（大文字・ゆっくり・音声優先）',
  set_autonarrate: '到着で自動ガイド', set_autonarrate_sub: '名所の50m以内で自動的に解説（位置情報が必要・接続中）',
  geo_arrived: '{name}に到着、解説します',
  set_avatar: 'ガイドの姿', set_avatar_sub: '姿・衣装・声をカスタマイズ',
  end_tour: 'ガイドを終える', end_tour_sub: 'ガイドに挨拶して、旅の絵はがきを受け取ろう',
  farewell: '本日の{scenic}めぐりはここまで。たくさんお話しできて嬉しかったです。{guide}がこの旅を一枚の絵はがきにしました。ここの景色がずっと心に残りますように。また会いに来てね。',
  set_appearance: '外観', mode_light: 'ライト', mode_dark: 'ダーク', mode_system: 'システム',
  qf_photo: '写真で位置', qf_tour: '巡る', qf_gps: '位置', qf_facility: '施設', qf_trace: '足あと',
  ob_back: '戻る', ob_next: '次へ', ob_start_btn: 'はじめる', ob_skip_short: 'スキップ',
  ob_step1_title: 'どの観光地へ？', ob_step1_sub: '選べば、ここ専属のガイドになります',
  ob_step2_title: '誰と一緒？', ob_step2_sub: '同行の皆さんに気を配ります',
  ob_first_q: '初めてですか？',
  ob_step3_title: 'どう巡りますか？', ob_step3_sub: 'あなたのペースと体力に合わせます',
  ob_pace_q: 'ペース', ob_mobility_q: '移動手段',
  ob_step4_title: '今回いちばん欲しいのは？', ob_step4_sub: '気分を教えて、旅をその色に',
  ob_age_q: '年齢層',
  ob_step5_title: '好きなものは？', ob_step5_sub: 'いくつか選んで、好きな話を多めに（複数選択可）',
}
const KO: Dict = {
  subtitle: 'AI 디지털 가이드',
  start: '투어 시작', waking: '준비 중…',
  placeholderOn: '무엇이든 물어보세요…', placeholderOff: '“투어 시작”으로 연결', listening: '듣고 있어요…', recognizing: '인식 중…',
  thinking: '{guide} 생각 중', intro: '“투어 시작”으로 연결하세요. 가이드가 인사하고, 음성·텍스트 질문이나 사진으로 현장 설명을 받을 수 있어요.',
  stage_hint: 'AI 가이드가 대기 중 — 탭하여 인사해요',
  st_idle: '미연결', st_connecting: '연결 중', st_buffering: '버퍼링', st_connected: '연결됨', st_error: '재생 실패',
  greet_pill: '환영',
  ob_greet: '안녕하세요, 당신의 AI 가이드예요',
  ob_greet_sub: '어디로 갈지, 무엇을 좋아하는지 알려주세요. 나머지는 맡겨요',
  ob_guide_wait: '{guide}가 여기서 기다려요',
  ob_scenic: '어느 관광지', ob_who: '누구와 함께', ob_interest: '관심사 (다중 선택)',
  ob_enter: '입장', ob_skip: '건너뛰고 시작',
  ob_replay: '인트로 다시 보기', ob_replay_sub: '관광지·취향 다시 선택',
  today: '오늘', today_tip: '팁',
  set_title: '설정', set_lang: '언어', set_elder: '시니어 모드 (큰 글씨·천천히·음성 우선)',
  set_autonarrate: '도착 시 자동 해설', set_autonarrate_sub: '명소 50m 이내에서 자동 해설 (위치 권한 필요·연결됨)',
  geo_arrived: '{name} 도착 — 해설해 드릴게요',
  set_avatar: '가이드 모습', set_avatar_sub: '모습·의상·목소리 맞춤 설정',
  end_tour: '투어 마치기', end_tour_sub: '가이드와 인사하고 여행 엽서를 받아요',
  farewell: '오늘 {scenic} 여행은 여기까지예요. 오는 길 내내 많은 이야기 나눠줘서 고마워요. {guide}가 이 여정을 한 장의 엽서로 만들었어요. 이곳의 풍경이 오래 마음에 남길 바라요. 다음에 또 놀러 와요.',
  set_appearance: '화면', mode_light: '라이트', mode_dark: '다크', mode_system: '시스템',
  qf_photo: '사진 위치', qf_tour: '투어', qf_gps: '위치', qf_facility: '시설', qf_trace: '발자취',
  ob_back: '뒤로', ob_next: '다음', ob_start_btn: '시작', ob_skip_short: '건너뛰기',
  ob_step1_title: '어느 관광지로?', ob_step1_sub: '고르면 여기 전담 가이드가 될게요',
  ob_step2_title: '누구와 함께?', ob_step2_sub: '동행 모두를 살펴드릴게요',
  ob_first_q: '처음 오셨나요?',
  ob_step3_title: '어떻게 둘러볼까요?', ob_step3_sub: '속도와 체력에 맞춰 짤게요',
  ob_pace_q: '속도', ob_mobility_q: '이동 방식',
  ob_step4_title: '이번 여행에서 가장 원하는 건?', ob_step4_sub: '기분을 알려주면 거기에 맞출게요',
  ob_age_q: '연령대',
  ob_step5_title: '좋아하는 게 있나요?', ob_step5_sub: '몇 개 골라요 — 좋아하는 얘기를 더 해드릴게요 (다중 선택)',
}
const DICTS: Record<Lang, Dict> = { zh: ZH, en: EN, ja: JA, ko: KO }

export function makeT(lang: Lang) {
  const d = DICTS[lang] || ZH
  // vars: 文案占位替换，如 t('thinking', { guide: '婉清' }) → "婉清正在思考"
  return (k: string, vars?: Record<string, string>) => {
    let s = d[k] ?? ZH[k] ?? k
    if (vars) for (const [key, val] of Object.entries(vars)) s = s.replaceAll(`{${key}}`, val)
    return s
  }
}

// 同行类型 / 兴趣：含各语言标签（图标见 lib/icons.tsx 的 GROUP_ICONS/INTEREST_ICONS）
export const GROUPS: { id: string; label: Record<Lang, string> }[] = [
  { id: 'adult', label: { zh: '独自/朋友', en: 'Solo/Friends', ja: '一人/友人', ko: '혼자/친구' } },
  { id: 'family_kids', label: { zh: '亲子同行', en: 'With Kids', ja: '親子', ko: '가족(아이)' } },
  { id: 'senior', label: { zh: '陪伴长辈', en: 'With Elders', ja: '年長者と', ko: '어르신과' } },
  { id: 'couple', label: { zh: '情侣出游', en: 'Couple', ja: 'カップル', ko: '커플' } },
]
export const INTERESTS: { id: string; label: Record<Lang, string> }[] = [
  { id: 'history', label: { zh: '历史人文', en: 'History', ja: '歴史', ko: '역사' } },
  { id: 'nature', label: { zh: '自然风光', en: 'Nature', ja: '自然', ko: '자연' } },
  { id: 'photo', label: { zh: '拍照打卡', en: 'Photo Spots', ja: '撮影', ko: '사진' } },
  { id: 'food', label: { zh: '特色美食', en: 'Food', ja: 'グルメ', ko: '음식' } },
  { id: 'culture', label: { zh: '禅意文化', en: 'Culture', ja: '文化', ko: '문화' } },
]

// ── 自身情况标签（多步 onboarding 新增 5 维）：默认值=中性，使老画像/未选时行为零变化，
//    后端缓存键也逐字节不变（默认值→空哈希，详见后端 _situation_key）。每维都拉动真实杠杆，非装饰。──
export interface Situation { age: string; pace: string; mobility: string; purpose: string; first_time: string }
export const SIT_DEFAULTS: Situation = { age: 'youth', pace: 'day', mobility: 'normal', purpose: 'relax', first_time: 'first' }

type Opt = { id: string; label: Record<Lang, string> }
export const AGES: Opt[] = [
  { id: 'teen',   label: { zh: '青少年', en: 'Teen', ja: '青少年', ko: '청소년' } },
  { id: 'youth',  label: { zh: '青年', en: 'Youth', ja: '青年', ko: '청년' } },
  { id: 'middle', label: { zh: '中年', en: 'Middle-aged', ja: '中年', ko: '중년' } },
  { id: 'elder',  label: { zh: '长者', en: 'Senior', ja: '年配', ko: '어르신' } },
]
export const PACES: Opt[] = [
  { id: 'half', label: { zh: '半天精华', en: 'Half-day', ja: '半日', ko: '반나절' } },
  { id: 'day',  label: { zh: '玩一整天', en: 'Full day', ja: 'まる一日', ko: '하루 종일' } },
  { id: 'deep', label: { zh: '深度慢游', en: 'Deep & slow', ja: 'じっくり', ko: '깊이 천천히' } },
]
export const MOBILITIES: Opt[] = [
  { id: 'stroller',   label: { zh: '推婴儿车', en: 'Stroller', ja: 'ベビーカー', ko: '유모차' } },
  { id: 'wheelchair', label: { zh: '需无障碍', en: 'Step-free', ja: 'バリアフリー', ko: '무장애' } },
  { id: 'normal',     label: { zh: '步行自如', en: 'Walk freely', ja: '普通に歩ける', ko: '자유 보행' } },
  { id: 'hiker',      label: { zh: '能爬山徒步', en: 'Hiking-fit', ja: '山も登れる', ko: '등산 가능' } },
]
export const PURPOSES: Opt[] = [
  { id: 'photo',    label: { zh: '拍照打卡', en: 'Photos', ja: '撮影', ko: '사진' } },
  { id: 'kids_fun', label: { zh: '遛娃带玩', en: 'Kids fun', ja: '子供と', ko: '아이와' } },
  { id: 'pray',     label: { zh: '祈福参拜', en: 'Praying', ja: '参拝', ko: '기원' } },
  { id: 'relax',    label: { zh: '休闲放松', en: 'Relax', ja: 'のんびり', ko: '휴식' } },
  { id: 'study',    label: { zh: '研学求知', en: 'Learn', ja: '学び', ko: '학습' } },
]
export const FIRSTTIMES: Opt[] = [
  { id: 'first',  label: { zh: '第一次来', en: 'First time', ja: '初めて', ko: '처음' } },
  { id: 'return', label: { zh: '故地重游', en: 'Been before', ja: '再訪', ko: '재방문' } },
]
