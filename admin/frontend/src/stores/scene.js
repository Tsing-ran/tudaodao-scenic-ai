import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import axios from 'axios'
import { chatStream } from '@/api/index'

export const useSceneStore = defineStore('scene', () => {
  // 当前景区主题类型
  const currentTheme = ref('buddhist')

  // 所有主题配置（从后端加载）
  const themes = ref({
    buddhist: {
      name: '佛教文化类',
      example: '灵山胜境、峨眉山',
      colors: {
        primary: '#004098', secondary: '#1A5BAE',
        background: '#030C1E', surface: '#07172E',
        text: '#E9F3FF', accent: '#97CBE0'
      },
      decoration: 'lotus',
      greeting: '阿弥陀佛，欢迎来到灵山胜境。我是您的AI导览师，请问您想了解哪处圣境？'
    },
    nature: {
      name: '自然山水类',
      example: '张家界、黄山',
      colors: {
        primary: '#005A8B', secondary: '#0077B6',
        background: '#021218', surface: '#042030',
        text: '#DCF4FF', accent: '#7CC4D8'
      },
      decoration: 'leaf',
      greeting: '您好！我是您的AI导览师，随时为您讲解山水奥秘。'
    },
    ancient_town: {
      name: '古镇民俗类',
      example: '乌镇、凤凰古城',
      colors: {
        primary: '#1A5BAE', secondary: '#004098',
        background: '#030C1E', surface: '#071528',
        text: '#EAF3FF', accent: '#A8C8E8'
      },
      decoration: 'ink',
      greeting: '欢迎来到古镇！我是您的AI导览师，且听我为您讲述千年故事。'
    },
    historical: {
      name: '历史遗址类',
      example: '故宫、兵马俑',
      colors: {
        primary: '#002D70', secondary: '#004098',
        background: '#020810', surface: '#050F20',
        text: '#E4F0FF', accent: '#7CA8D4'
      },
      decoration: 'bronze',
      greeting: '欢迎光临！我是您的AI导览师，带您感受华夏文明的厚重积淀。'
    },
    modern: {
      name: '现代主题类',
      example: '科技馆、主题乐园',
      colors: {
        primary: '#0052CC', secondary: '#0096C7',
        background: '#030810', surface: '#081422',
        text: '#DCEFFF', accent: '#60C0E8'
      },
      decoration: 'circuit',
      greeting: '欢迎！我是您的AI导览师，随时为您提供专业讲解服务。'
    }
  })

  // 当前数字人形象图片（通义万相生成）
  const avatarImageUrl = ref('')
  const isGeneratingAvatar = ref(false)

  // 当前数字人会话
  const sessionId = ref('')
  const isSessionActive = ref(false)
  const sessionCredentials = ref(null)  // DVH RTC 凭证，供前端 SDK 使用

  // 景区名称（可自定义）
  const scenicName = ref('')

  // 云端景区ID（对应队友后端的 scenic_id 枚举）
  const scenicId = ref('lingshan')

  // 景区类型 → 云端 scenic_id 映射（支持的5个ID：lingshan/nihuawan/xihu/huangshan/gugong）
  const scenicIdMap = {
    buddhist:     'lingshan',
    nature:       'huangshan',
    ancient_town: 'nihuawan',
    historical:   'gugong',
    modern:       'xihu',
  }

  // 单个景区ID → 云端 scenic_id 映射（不在列表内的回落到主题默认）
  const spotToScenicId = {
    lingshan: 'lingshan', emei: 'lingshan', putuo: 'lingshan',
    huangshan: 'huangshan', zhangjiajie: 'huangshan', jiuzhaigou: 'huangshan',
    wuzhen: 'nihuawan', fenghuang: 'nihuawan', lijiang: 'nihuawan',
    gugong: 'gugong', bingmayong: 'gugong', dunhuang: 'gugong',
    shanghai_tech: 'xihu', disney: 'xihu', universal: 'xihu',
  }

  // 内置景区列表（通用平台演示数据）
  const scenicSpots = [
    { id:'lingshan',     name:'灵山胜境',       theme:'buddhist',    province:'江苏无锡', lat:31.57, lng:120.26, desc:'中国最大露天佛教文化景区' },
    { id:'emei',         name:'峨眉山',          theme:'buddhist',    province:'四川乐山', lat:29.52, lng:103.33, desc:'世界文化与自然双遗产' },
    { id:'putuo',        name:'普陀山',          theme:'buddhist',    province:'浙江舟山', lat:29.97, lng:122.38, desc:'海天佛国，四大佛教名山之一' },
    { id:'huangshan',    name:'黄山风景区',       theme:'nature',      province:'安徽黄山', lat:30.13, lng:118.17, desc:'天下第一奇山' },
    { id:'zhangjiajie',  name:'张家界',          theme:'nature',      province:'湖南张家界', lat:29.12, lng:110.48, desc:'世界自然遗产，阿凡达取景地' },
    { id:'jiuzhaigou',   name:'九寨沟',          theme:'nature',      province:'四川阿坝', lat:33.27, lng:103.92, desc:'童话世界，世界自然遗产' },
    { id:'wuzhen',       name:'乌镇景区',        theme:'ancient_town', province:'浙江桐乡', lat:30.64, lng:120.49, desc:'千年水乡古镇' },
    { id:'fenghuang',    name:'凤凰古城',        theme:'ancient_town', province:'湖南凤凰', lat:27.95, lng:109.60, desc:'中国最美古城之一' },
    { id:'lijiang',      name:'丽江古城',        theme:'ancient_town', province:'云南丽江', lat:26.87, lng:100.23, desc:'世界文化遗产，纳西族古城' },
    { id:'gugong',       name:'故宫博物院',       theme:'historical',  province:'北京',    lat:39.91, lng:116.39, desc:'中国古代宫廷建筑之精华' },
    { id:'bingmayong',   name:'秦始皇兵马俑',    theme:'historical',  province:'陕西西安', lat:34.38, lng:109.27, desc:'世界第八大奇迹' },
    { id:'dunhuang',     name:'敦煌莫高窟',       theme:'historical',  province:'甘肃敦煌', lat:40.04, lng:94.81, desc:'丝绸之路上的艺术宝库' },
    { id:'shanghai_tech',name:'上海科技馆',       theme:'modern',      province:'上海',    lat:31.22, lng:121.54, desc:'国家一级科学技术博物馆' },
    { id:'disney',       name:'上海迪士尼乐园',   theme:'modern',      province:'上海',    lat:31.15, lng:121.67, desc:'中国首座迪士尼主题乐园' },
    { id:'universal',    name:'北京环球影城',     theme:'modern',      province:'北京',    lat:39.92, lng:116.68, desc:'全球最大的环球主题公园' },
  ]

  // 当前选中的景区对象
  const selectedSpot = ref(null)

  function selectSpot(spot) {
    selectedSpot.value = spot
    scenicName.value = spot.name
    scenicId.value = spotToScenicId[spot.id] || scenicIdMap[spot.theme] || 'lingshan'
    currentTheme.value = spot.theme
  }

  // 对话历史（最近5轮，客户端维护）
  const chatHistory = ref([])
  const isChatting = ref(false)

  // 当前情绪（驱动数字人表情）
  const currentEmotion = ref('neutral')

  const activeTheme = computed(() => themes.value[currentTheme.value] || themes.value.buddhist)
  const activeColors = computed(() => activeTheme.value.colors)
  const greeting = computed(() => activeTheme.value.greeting)

  function setTheme(type) {
    currentTheme.value = type
    scenicId.value = scenicIdMap[type] || 'lingshan'
  }

  /**
   * 核心对话函数：调用云端 SSE → 逐句驱动数字人播报
   * @param {string} userMessage  用户问题
   * @param {Function} onSpeakSentence  收到每句回答时的回调（送 DVH SendText）
   */
  async function askQuestion(userMessage, onSpeakSentence) {
    if (isChatting.value) return
    isChatting.value = true
    currentEmotion.value = 'neutral'

    // 构建本轮历史（最近5轮）
    const history = chatHistory.value.slice(-10)

    let fullReply = ''

    await chatStream({
      message: userMessage,
      scenicId: scenicId.value,
      sessionId: sessionId.value || 'anonymous',
      history,
      onEmotion: (emotion) => {
        currentEmotion.value = emotion
      },
      onSentence: async (text, index) => {
        fullReply += text
        // 回调通知前端（触发说话动画 + D-ID 驱动）
        if (onSpeakSentence) onSpeakSentence(text)
      },
      onEnd: () => {
        // 记录本轮对话到历史
        chatHistory.value.push(
          { role: 'user', content: userMessage },
          { role: 'assistant', content: fullReply },
        )
        isChatting.value = false
      },
    })
  }

  async function generateAvatar(sceneType, customPrompt = null) {
    isGeneratingAvatar.value = true
    try {
      const res = await axios.post('/api/image/avatar/generate', {
        scene_type: sceneType,
        custom_prompt: customPrompt
      })
      if (res.data.code === 0) {
        avatarImageUrl.value = res.data.data.url
        return res.data.data.url
      }
    } finally {
      isGeneratingAvatar.value = false
    }
  }

  async function startSession() {
    const res = await axios.post('/api/avatar/session/start')
    if (res.data.code === 0) {
      const data = res.data.data
      sessionId.value = data.session_id
      sessionCredentials.value = data   // 保存全部凭证供 RTC SDK 使用
      isSessionActive.value = true
      return data
    }
  }

  async function sendText(text) {
    // 优先用 DVH（若已配置），否则走本地 TTS
    if (isSessionActive.value && sessionId.value) {
      await axios.post('/api/avatar/session/send', {
        session_id: sessionId.value,
        text,
      }).catch(() => {})
    }
  }

  /**
   * 调用本地 TTS 合成语音，返回可播放的 Blob URL
   */
  async function synthesizeSpeech(text) {
    const res = await axios.post('/api/tts/synthesize',
      { text, scene_type: currentTheme.value },
      { responseType: 'blob' }
    )
    return URL.createObjectURL(res.data)
  }

  async function stopSession() {
    if (!sessionId.value) return
    await axios.post('/api/avatar/session/stop', { session_id: sessionId.value })
    sessionId.value = ''
    sessionCredentials.value = null
    isSessionActive.value = false
  }

  return {
    currentTheme, themes, avatarImageUrl, isGeneratingAvatar,
    sessionId, isSessionActive, scenicName, scenicId,
    activeTheme, activeColors, greeting,
    chatHistory, isChatting, currentEmotion,
    sessionCredentials,
    scenicSpots, selectedSpot, selectSpot,
    setTheme, generateAvatar, startSession, sendText, stopSession, askQuestion, synthesizeSpeech
  }
})
