<template>
  <div class="lp">
    <!-- 明暗模式切换（与侧栏按钮同一套 localStorage 约定） -->
    <button class="theme-fab" :aria-label="isDark ? '切换到浅色模式' : '切换到深色模式'" @click="toggleTheme">
      <transition name="tspin" mode="out-in">
        <PhSun v-if="isDark" key="sun" weight="duotone" :size="15" />
        <PhMoon v-else key="moon" weight="duotone" :size="15" />
      </transition>
      <span>{{ isDark ? '浅色' : '深色' }}</span>
    </button>

    <!-- ═══ 左侧展示区 ═══ -->
    <div class="showcase">
      <!-- Logo -->
      <div class="s-logo">
        <img src="@/assets/logo-tudaodao.png" alt="途叨叨" class="s-logo-img" />
        <span>途叨叨</span>
      </div>

      <!-- 轮播内容区 -->
      <div class="s-stage">
        <button class="s-arr s-arr-l" @click="prev">
          <PhCaretLeft weight="duotone" :size="18" />
        </button>

        <transition name="cfade" mode="out-in">
          <div class="s-slide" :key="cur">
            <div class="s-art">
              <!-- 插图 1：数字人智能导览 -->
              <svg v-if="cur === 0" viewBox="0 0 380 260" fill="none" xmlns="http://www.w3.org/2000/svg">
                <defs>
                  <linearGradient id="gradBlue1" x1="0" y1="0" x2="1" y2="1">
                    <stop offset="0%" stop-color="#7DD3FC"/>
                    <stop offset="100%" stop-color="#0EA5E9"/>
                  </linearGradient>
                  <linearGradient id="gradGold1" x1="0" y1="0" x2="1" y2="1">
                    <stop offset="0%" stop-color="#FDE68A"/>
                    <stop offset="100%" stop-color="#F59E0B"/>
                  </linearGradient>
                  <filter id="glow1" x="-60%" y="-60%" width="220%" height="220%">
                    <feGaussianBlur stdDeviation="6" result="b"/>
                    <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
                  </filter>
                </defs>
                <!-- 背景圆弧装饰 -->
                <circle cx="190" cy="130" r="115" fill="rgba(255,255,255,0.06)"/>
                <circle cx="190" cy="130" r="85" fill="rgba(14,165,233,0.05)"/>
                <!-- 山峰剪影 -->
                <polygon points="50,220 110,110 170,220" fill="rgba(125,211,252,0.14)"/>
                <polygon points="110,220 185,85 260,220" fill="rgba(125,211,252,0.2)"/>
                <polygon points="200,220 255,130 310,220" fill="rgba(125,211,252,0.12)"/>
                <!-- 地面 -->
                <ellipse cx="190" cy="222" rx="160" ry="14" fill="rgba(255,255,255,0.08)"/>
                <!-- 数字人：光晕环 -->
                <circle cx="148" cy="118" r="34" fill="none" filter="url(#glow1)" stroke="url(#gradGold1)" stroke-width="1" opacity="0.35"/>
                <circle cx="148" cy="118" r="31" stroke="url(#gradBlue1)" stroke-width="1.5" fill="none" stroke-dasharray="4,3"/>
                <!-- 数字人：头 -->
                <circle cx="148" cy="118" r="24" fill="rgba(255,255,255,0.94)"/>
                <!-- 数字人：面部 -->
                <circle cx="140" cy="114" r="3.5" fill="#1565C0"/>
                <circle cx="156" cy="114" r="3.5" fill="#1565C0"/>
                <path d="M141 124 Q148 130 155 124" stroke="#1565C0" stroke-width="2" stroke-linecap="round" fill="none"/>
                <!-- 数字人：身体 -->
                <rect x="131" y="145" width="34" height="50" rx="14" fill="rgba(255,255,255,0.9)"/>
                <rect x="139" y="153" width="18" height="10" rx="5" fill="url(#gradBlue1)" opacity="0.55"/>
                <!-- 数字人：手臂 -->
                <rect x="100" y="148" width="33" height="11" rx="5.5" fill="rgba(255,255,255,0.72)"/>
                <rect x="165" y="148" width="33" height="11" rx="5.5" fill="rgba(255,255,255,0.72)"/>
                <!-- 右手持平板 -->
                <rect x="192" y="138" width="18" height="26" rx="3" fill="rgba(255,255,255,0.92)" stroke="url(#gradBlue1)" stroke-width="1.5"/>
                <rect x="195" y="142" width="12" height="8" rx="1.5" fill="url(#gradBlue1)" opacity="0.55"/>
                <rect x="195" y="153" width="8" height="2" rx="1" fill="url(#gradGold1)" opacity="0.8"/>
                <rect x="195" y="157" width="12" height="2" rx="1" fill="rgba(120,200,255,0.4)"/>
                <!-- 数字人：腿 -->
                <rect x="134" y="193" width="13" height="28" rx="6.5" fill="rgba(255,255,255,0.82)"/>
                <rect x="149" y="193" width="13" height="28" rx="6.5" fill="rgba(255,255,255,0.82)"/>
                <!-- 游客：头 -->
                <circle cx="275" cy="140" r="19" fill="rgba(255,215,175,0.92)"/>
                <!-- 游客：帽子 -->
                <ellipse cx="275" cy="126" rx="21" ry="6" fill="rgba(255,255,255,0.85)"/>
                <rect x="258" y="117" width="34" height="12" rx="3" fill="rgba(255,255,255,0.9)"/>
                <!-- 游客：身体 -->
                <rect x="260" y="162" width="30" height="38" rx="12" fill="url(#gradBlue1)" opacity="0.8"/>
                <!-- 游客：腿 -->
                <rect x="263" y="198" width="11" height="24" rx="5.5" fill="rgba(80,160,220,0.85)"/>
                <rect x="276" y="198" width="11" height="24" rx="5.5" fill="rgba(80,160,220,0.85)"/>
                <!-- 游客举手 -->
                <rect x="288" y="163" width="24" height="9" rx="4.5" fill="url(#gradBlue1)" opacity="0.75"/>
                <!-- 互动星标 -->
                <path d="M300 150 l3 7 7 1 -5 5 1 7 -6 -4 -6 4 1 -7 -5 -5 7 -1 z" fill="url(#gradGold1)"/>
                <!-- 连接线 -->
                <line x1="182" y1="160" x2="262" y2="155" stroke="url(#gradGold1)" stroke-width="1.5" stroke-dasharray="4,4" opacity="0.8"/>
                <!-- 右侧植物 -->
                <rect x="343" y="188" width="7" height="38" rx="3.5" fill="rgba(80,180,100,0.55)"/>
                <ellipse cx="347" cy="176" rx="17" ry="22" fill="rgba(90,195,115,0.5)"/>
                <ellipse cx="333" cy="184" rx="12" ry="16" fill="rgba(100,205,120,0.45)"/>
                <ellipse cx="360" cy="180" rx="11" ry="15" fill="rgba(75,185,100,0.4)"/>
                <!-- 装饰星点 -->
                <circle cx="85" cy="88" r="3" fill="url(#gradGold1)"/>
                <circle cx="75" cy="74" r="2" fill="rgba(255,255,255,0.3)"/>
                <circle cx="98" cy="70" r="1.5" fill="rgba(255,255,255,0.25)"/>
                <circle cx="315" cy="78" r="2.5" fill="rgba(125,211,252,0.5)"/>
                <circle cx="328" cy="90" r="1.5" fill="rgba(255,255,255,0.25)"/>
              </svg>

              <!-- 插图 2：知识库上传管理 -->
              <svg v-else-if="cur === 1" viewBox="0 0 380 260" fill="none" xmlns="http://www.w3.org/2000/svg">
                <defs>
                  <linearGradient id="gradBlue2" x1="0" y1="0" x2="1" y2="1">
                    <stop offset="0%" stop-color="#7DD3FC"/>
                    <stop offset="100%" stop-color="#0EA5E9"/>
                  </linearGradient>
                  <linearGradient id="gradGold2" x1="0" y1="0" x2="1" y2="1">
                    <stop offset="0%" stop-color="#FDE68A"/>
                    <stop offset="100%" stop-color="#F59E0B"/>
                  </linearGradient>
                  <filter id="glow2" x="-60%" y="-60%" width="220%" height="220%">
                    <feGaussianBlur stdDeviation="7" result="b"/>
                    <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
                  </filter>
                </defs>
                <!-- 背景装饰 -->
                <circle cx="190" cy="130" r="110" fill="rgba(255,255,255,0.06)"/>
                <!-- 云朵存储 -->
                <ellipse cx="190" cy="72" rx="55" ry="32" fill="url(#gradBlue2)" opacity="0.22" filter="url(#glow2)"/>
                <ellipse cx="155" cy="82" rx="35" ry="24" fill="rgba(255,255,255,0.14)"/>
                <ellipse cx="225" cy="80" rx="38" ry="25" fill="rgba(255,255,255,0.14)"/>
                <rect x="145" y="82" width="90" height="28" rx="4" fill="rgba(255,255,255,0.18)"/>
                <!-- 云朵图标 -->
                <path d="M178 70 Q185 58 198 62 Q202 55 212 60 Q220 57 222 67 Q228 67 228 75 L178 75 Q172 75 174 69 Z" fill="rgba(255,255,255,0.9)"/>
                <!-- 上传箭头 -->
                <line x1="190" y1="106" x2="190" y2="138" stroke="url(#gradGold2)" stroke-width="2.5" stroke-dasharray="4,3"/>
                <polygon points="184,112 190,103 196,112" fill="url(#gradGold2)"/>
                <!-- 文档卡片堆叠 -->
                <!-- 最后面 -->
                <rect x="88" y="140" width="88" height="110" rx="8" fill="rgba(125,211,252,0.16)" transform="rotate(-8 132 195)"/>
                <!-- 中间 -->
                <rect x="88" y="140" width="88" height="110" rx="8" fill="rgba(125,211,252,0.22)" transform="rotate(-3 132 195)"/>
                <!-- 最前面（主文档） -->
                <rect x="88" y="140" width="88" height="110" rx="8" fill="rgba(255,255,255,0.92)"/>
                <!-- 文档内容线条 -->
                <rect x="98" y="155" width="55" height="4" rx="2" fill="url(#gradBlue2)" opacity="0.6"/>
                <rect x="98" y="164" width="68" height="3" rx="1.5" fill="rgba(30,100,200,0.18)"/>
                <rect x="98" y="172" width="60" height="3" rx="1.5" fill="rgba(30,100,200,0.18)"/>
                <rect x="98" y="180" width="64" height="3" rx="1.5" fill="rgba(30,100,200,0.18)"/>
                <rect x="98" y="188" width="50" height="3" rx="1.5" fill="rgba(30,100,200,0.18)"/>
                <!-- 文档图标标识 -->
                <rect x="98" y="200" width="20" height="18" rx="3" fill="url(#gradGold2)" opacity="0.28"/>
                <rect x="100" y="204" width="16" height="2" rx="1" fill="url(#gradGold2)" opacity="0.85"/>
                <rect x="100" y="208" width="12" height="2" rx="1" fill="rgba(30,100,200,0.4)"/>
                <rect x="100" y="212" width="14" height="2" rx="1" fill="rgba(30,100,200,0.3)"/>
                <!-- 管理人员 -->
                <circle cx="272" cy="158" r="21" fill="rgba(255,215,175,0.92)"/>
                <!-- 头发 -->
                <path d="M253 155 Q256 138 272 136 Q288 138 291 155" fill="rgba(80,50,30,0.7)"/>
                <!-- 身体 -->
                <rect x="255" y="182" width="34" height="45" rx="13" fill="url(#gradBlue2)" opacity="0.82"/>
                <!-- 手臂（指向文档） -->
                <rect x="222" y="182" width="35" height="10" rx="5" fill="url(#gradBlue2)" opacity="0.75"/>
                <!-- 腿 -->
                <rect x="258" y="225" width="12" height="22" rx="6" fill="rgba(80,160,220,0.8)"/>
                <rect x="273" y="225" width="12" height="22" rx="6" fill="rgba(80,160,220,0.8)"/>
                <!-- 搜索放大镜 -->
                <circle cx="325" cy="170" r="22" stroke="url(#gradGold2)" stroke-width="3" fill="rgba(255,255,255,0.1)"/>
                <line x1="340" y1="185" x2="355" y2="200" stroke="url(#gradGold2)" stroke-width="3" stroke-linecap="round"/>
                <circle cx="320" cy="165" r="4" fill="rgba(255,255,255,0.6)"/>
                <!-- 植物 -->
                <rect x="42" y="198" width="7" height="36" rx="3.5" fill="rgba(80,180,100,0.55)"/>
                <ellipse cx="46" cy="187" rx="16" ry="20" fill="rgba(90,195,115,0.48)"/>
                <ellipse cx="32" cy="195" rx="11" ry="15" fill="rgba(100,205,120,0.43)"/>
                <!-- 装饰 -->
                <circle cx="58" cy="85" r="3" fill="url(#gradGold2)"/>
                <circle cx="310" cy="82" r="2.5" fill="rgba(125,211,252,0.5)"/>
                <circle cx="345" cy="110" r="2" fill="rgba(255,255,255,0.25)"/>
              </svg>

              <!-- 插图 3：数据分析统计 -->
              <svg v-else viewBox="0 0 380 260" fill="none" xmlns="http://www.w3.org/2000/svg">
                <defs>
                  <linearGradient id="gradBlue3" x1="0" y1="0" x2="1" y2="1">
                    <stop offset="0%" stop-color="#7DD3FC"/>
                    <stop offset="100%" stop-color="#0EA5E9"/>
                  </linearGradient>
                  <linearGradient id="gradGold3" x1="0" y1="0" x2="1" y2="1">
                    <stop offset="0%" stop-color="#FDE68A"/>
                    <stop offset="100%" stop-color="#F59E0B"/>
                  </linearGradient>
                  <linearGradient id="gradBar3" x1="0" y1="1" x2="0" y2="0">
                    <stop offset="0%" stop-color="#0EA5E9"/>
                    <stop offset="100%" stop-color="#7DD3FC"/>
                  </linearGradient>
                  <filter id="glow3" x="-60%" y="-60%" width="220%" height="220%">
                    <feGaussianBlur stdDeviation="8" result="b"/>
                    <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
                  </filter>
                </defs>
                <!-- 背景 -->
                <circle cx="190" cy="130" r="110" fill="rgba(255,255,255,0.06)"/>
                <ellipse cx="175" cy="143" rx="120" ry="80" fill="url(#gradBlue3)" opacity="0.08" filter="url(#glow3)"/>
                <!-- 大屏幕框 -->
                <rect x="55" y="68" width="240" height="150" rx="10" fill="rgba(255,255,255,0.12)" stroke="url(#gradBlue3)" stroke-width="1.5" opacity="0.9"/>
                <!-- 屏幕内容背景 -->
                <rect x="62" y="75" width="226" height="136" rx="6" fill="url(#gradBlue3)" opacity="0.07"/>
                <!-- 屏幕支架 -->
                <rect x="162" y="218" width="26" height="14" rx="2" fill="rgba(255,255,255,0.3)"/>
                <rect x="148" y="230" width="54" height="6" rx="3" fill="rgba(255,255,255,0.25)"/>
                <!-- 折线图 -->
                <polyline points="75,175 100,155 125,162 150,140 175,148 200,128 225,135 250,115 275,122" stroke="url(#gradBlue3)" stroke-width="2.5" fill="none" stroke-linejoin="round" stroke-linecap="round"/>
                <!-- 折线图点 -->
                <circle cx="100" cy="155" r="3" fill="#7DD3FC"/>
                <circle cx="150" cy="140" r="3" fill="#7DD3FC"/>
                <circle cx="200" cy="128" r="3" fill="#7DD3FC"/>
                <circle cx="250" cy="115" r="4" fill="url(#gradGold3)"/>
                <!-- 柱状图 -->
                <rect x="78" y="140" width="16" height="38" rx="4" fill="url(#gradBar3)" opacity="0.55"/>
                <rect x="100" y="128" width="16" height="50" rx="4" fill="url(#gradBar3)" opacity="0.7"/>
                <rect x="122" y="118" width="16" height="60" rx="4" fill="url(#gradGold3)"/>
                <rect x="144" y="132" width="16" height="46" rx="4" fill="url(#gradBar3)" opacity="0.6"/>
                <!-- 饼图 -->
                <circle cx="230" cy="115" r="32" fill="rgba(255,255,255,0.08)" stroke="rgba(255,255,255,0.2)" stroke-width="1"/>
                <path d="M230 115 L230 83 A32 32 0 0 1 262 115 Z" fill="url(#gradGold3)"/>
                <path d="M230 115 L262 115 A32 32 0 0 1 218 146 Z" fill="rgba(255,255,255,0.55)"/>
                <path d="M230 115 L218 146 A32 32 0 0 1 198 115 Z" fill="rgba(255,255,255,0.32)"/>
                <path d="M230 115 L198 115 A32 32 0 0 1 230 83 Z" fill="url(#gradBlue3)" opacity="0.7"/>
                <!-- 顶部指标卡 -->
                <rect x="68" y="80" width="56" height="30" rx="4" fill="rgba(255,255,255,0.15)"/>
                <rect x="132" y="80" width="56" height="30" rx="4" fill="rgba(255,255,255,0.15)"/>
                <rect x="196" y="80" width="56" height="30" rx="4" fill="rgba(255,255,255,0.15)"/>
                <rect x="260" y="80" width="28" height="30" rx="4" fill="rgba(255,255,255,0.1)"/>
                <rect x="72" y="86" width="28" height="4" rx="2" fill="rgba(255,255,255,0.5)"/>
                <rect x="72" y="95" width="40" height="5" rx="2.5" fill="url(#gradGold3)"/>
                <rect x="136" y="86" width="28" height="4" rx="2" fill="rgba(255,255,255,0.5)"/>
                <rect x="136" y="95" width="38" height="5" rx="2.5" fill="rgba(255,255,255,0.75)"/>
                <rect x="200" y="86" width="28" height="4" rx="2" fill="rgba(255,255,255,0.5)"/>
                <rect x="200" y="95" width="42" height="5" rx="2.5" fill="url(#gradBlue3)" opacity="0.85"/>
                <!-- 分析人员 -->
                <circle cx="320" cy="175" r="19" fill="rgba(255,215,175,0.92)"/>
                <rect x="304" y="197" width="32" height="42" rx="12" fill="url(#gradBlue3)" opacity="0.82"/>
                <!-- 手指向屏幕 -->
                <rect x="274" y="196" width="32" height="9" rx="4.5" fill="url(#gradBlue3)" opacity="0.75"/>
                <rect x="307" y="218" width="11" height="21" rx="5.5" fill="rgba(80,160,220,0.8)"/>
                <rect x="320" y="218" width="11" height="21" rx="5.5" fill="rgba(80,160,220,0.8)"/>
                <!-- 植物 -->
                <rect x="343" y="196" width="7" height="38" rx="3.5" fill="rgba(80,180,100,0.55)"/>
                <ellipse cx="347" cy="184" rx="17" ry="21" fill="rgba(90,195,115,0.48)"/>
                <ellipse cx="332" cy="192" rx="12" ry="16" fill="rgba(100,205,120,0.43)"/>
                <!-- 装饰 -->
                <circle cx="40" cy="88" r="3" fill="url(#gradGold3)"/>
                <circle cx="52" cy="100" r="2" fill="rgba(255,255,255,0.25)"/>
                <circle cx="348" cy="80" r="2.5" fill="rgba(125,211,252,0.5)"/>
              </svg>
            </div>

            <h2 class="s-title">{{ slides[cur].title }}</h2>
            <p class="s-desc">{{ slides[cur].desc }}</p>
          </div>
        </transition>

        <button class="s-arr s-arr-r" @click="next">
          <PhCaretRight weight="duotone" :size="18" />
        </button>
      </div>

      <!-- 指示点 -->
      <div class="s-dots">
        <span
          v-for="(_, i) in slides"
          :key="i"
          :class="['s-dot', { on: i === cur }]"
          @click="go(i)"
        />
      </div>
    </div>

    <!-- ═══ 右侧登录/注册区 ═══ -->
    <div class="login-side">
      <div class="l-card">

        <!-- Tab 切换 -->
        <div class="l-tabs">
          <button :class="['l-tab', { active: tab === 'login' }]" @click="switchTab('login')">登录</button>
          <button :class="['l-tab', { active: tab === 'register' }]" @click="switchTab('register')">注册</button>
          <div class="l-tab-bar" :style="{ left: tab === 'login' ? '4px' : '50%' }" />
        </div>

        <!-- ── 登录表单 ── -->
        <transition name="tfade" mode="out-in">
        <div v-if="tab === 'login'" class="l-body" key="login">
          <h1 class="l-title">登录 景区管理端</h1>
          <p class="l-sub">途叨叨 · 智能景区管理后台</p>

          <div class="l-field" :class="{ foc: foc === 'lu', err: !!errMsg }">
            <PhUser weight="duotone" :size="16" class="l-ico" />
            <input v-model="form.username" class="l-in" placeholder="请输入管理员账号"
              autocomplete="username" @focus="foc='lu'" @blur="foc=''" @keyup.enter="handleLogin" />
          </div>

          <div class="l-field" :class="{ foc: foc === 'lp', err: !!errMsg }">
            <PhLock weight="duotone" :size="16" class="l-ico" />
            <input v-model="form.password" :type="see ? 'text' : 'password'" class="l-in"
              placeholder="请输入密码" autocomplete="current-password"
              @focus="foc='lp'" @blur="foc=''" @keyup.enter="handleLogin" />
            <button class="l-eye" @click="see=!see" tabindex="-1">
              <PhEye weight="duotone" v-if="!see" :size="14" />
              <PhEyeSlash weight="duotone" v-else :size="14" />
            </button>
          </div>

          <label class="l-rem">
            <input type="checkbox" v-model="remember" class="l-chk" />
            <span>记住密码</span>
          </label>

          <p v-if="errMsg" class="l-err"><PhWarningCircle weight="duotone" :size="12" />{{ errMsg }}</p>

          <button class="l-btn" @click="handleLogin" :disabled="busy">
            <PhCircleNotch weight="duotone" v-if="busy" :size="15" class="spin" />
            {{ busy ? '登录中…' : '登录' }}
          </button>

          <p class="l-switch">还没有账号？<span @click="switchTab('register')">立即注册</span></p>
        </div>

        <!-- ── 注册表单 ── -->
        <div v-else class="l-body" key="register">

          <!-- 进度条 -->
          <div class="reg-bar-wrap">
            <div class="reg-bar-fill" :style="{ width: regStep === 1 ? '33%' : regStep === 2 ? '66%' : '100%' }" />
          </div>

          <transition name="sfade" mode="out-in">

          <!-- Step 1: 账号信息 -->
          <div v-if="regStep === 1" key="s1">
            <h1 class="l-title">创建账号</h1>
            <p class="l-sub">步骤 1 / 3 &nbsp;·&nbsp; 账号信息</p>

            <div class="l-field" :class="{ foc: foc === 'ru', err: !!errMsg }">
              <PhUser weight="duotone" :size="16" class="l-ico" />
              <input v-model="reg.username" class="l-in" placeholder="4–20位字母、数字或下划线"
                autocomplete="username" @focus="foc='ru'" @blur="foc=''" />
            </div>

            <div class="l-field" :class="{ foc: foc === 'rp', err: !!errMsg }">
              <PhLock weight="duotone" :size="16" class="l-ico" />
              <input v-model="reg.password" :type="see ? 'text' : 'password'" class="l-in"
                placeholder="至少 6 位" autocomplete="new-password"
                @focus="foc='rp'" @blur="foc=''" />
              <button class="l-eye" @click="see=!see" tabindex="-1">
                <PhEye weight="duotone" v-if="!see" :size="14" />
                <PhEyeSlash weight="duotone" v-else :size="14" />
              </button>
            </div>

            <div class="l-field" :class="{ foc: foc === 'rc', err: !!errMsg }">
              <PhShieldCheck weight="duotone" :size="16" class="l-ico" />
              <input v-model="reg.confirm" :type="see ? 'text' : 'password'" class="l-in"
                placeholder="再次输入密码" autocomplete="new-password"
                @focus="foc='rc'" @blur="foc=''" @keyup.enter="nextStep" />
            </div>

            <p v-if="errMsg" class="l-err"><PhWarningCircle weight="duotone" :size="12" />{{ errMsg }}</p>

            <button class="l-btn" @click="nextStep">下一步 →</button>
          </div>

          <!-- Step 2: 管理人员信息 -->
          <div v-else-if="regStep === 2" key="s2">
            <h1 class="l-title">管理人员信息</h1>
            <p class="l-sub">步骤 2 / 3 &nbsp;·&nbsp; 完善身份信息，便于景区协同管理</p>

            <div class="l-field" :class="{ foc: foc === 'rn' }">
              <PhIdentificationCard weight="duotone" :size="16" class="l-ico" />
              <input v-model="reg.realName" class="l-in" placeholder="真实姓名"
                autocomplete="name" @focus="foc='rn'" @blur="foc=''" />
            </div>

            <div class="l-field" :class="{ foc: foc === 'rph' }">
              <PhPhone weight="duotone" :size="16" class="l-ico" />
              <input v-model="reg.phone" class="l-in" placeholder="联系电话（11 位手机号）"
                maxlength="11" inputmode="numeric" autocomplete="tel"
                @focus="foc='rph'" @blur="foc=''" />
            </div>

            <div class="l-field" :class="{ foc: foc === 'rem' }">
              <PhEnvelopeSimple weight="duotone" :size="16" class="l-ico" />
              <input v-model="reg.email" class="l-in" placeholder="电子邮箱（选填）"
                autocomplete="email" @focus="foc='rem'" @blur="foc=''" />
            </div>

            <div class="l-field l-field--select" :class="{ foc: foc === 'rd' }">
              <PhBriefcase weight="duotone" :size="16" class="l-ico" />
              <select v-model="reg.department" class="l-in l-select" required
                @focus="foc='rd'" @blur="foc=''">
                <option value="" disabled>所属部门</option>
                <option v-for="d in DEPARTMENTS" :key="d" :value="d">{{ d }}</option>
              </select>
            </div>

            <div class="l-field" :class="{ foc: foc === 'rpos' }">
              <PhUserGear weight="duotone" :size="16" class="l-ico" />
              <input v-model="reg.position" class="l-in" placeholder="岗位职务（选填，如：运营专员 / 值班经理）"
                @focus="foc='rpos'" @blur="foc=''" @keyup.enter="nextStep2" />
            </div>

            <p v-if="errMsg" class="l-err"><PhWarningCircle weight="duotone" :size="12" />{{ errMsg }}</p>

            <div class="reg-actions">
              <button class="l-back" @click="regStep = 1">← 上一步</button>
              <button class="l-btn reg-submit" @click="nextStep2">下一步 →</button>
            </div>
          </div>

          <!-- Step 3: 选择景区 -->
          <div v-else key="s3">
            <h1 class="l-title">选择您的景区</h1>
            <p class="l-sub">步骤 3 / 3 &nbsp;·&nbsp; 管理人员所在景区（系统自动识别类型）</p>

            <!-- 搜索 + GPS -->
            <div class="reg-search-row">
              <div class="reg-search-box" :class="{ focused: searchFocus }">
                <PhMagnifyingGlass weight="duotone" :size="13" class="reg-search-ico" />
                <input v-model="searchText" class="reg-search-in"
                  placeholder="搜索景区名称或省份…"
                  @focus="searchFocus=true" @blur="searchFocus=false" />
                <button v-if="searchText" class="reg-clear" @click="searchText=''">
                  <PhX weight="duotone" :size="11" />
                </button>
              </div>
              <button class="reg-gps-btn" :class="{ active: gpsUsed, loading: gpsLoading }" @click="handleGPS" title="GPS定位">
                <PhCircleNotch weight="duotone" v-if="gpsLoading" :size="13" class="spin" />
                <PhNavigationArrow weight="duotone" v-else :size="13" />
              </button>
            </div>

            <p v-if="gpsUsed && !gpsError" class="reg-gps-ok">
              <PhMapPin weight="duotone" :size="10" />已按距离排序，最近景区在顶部
            </p>
            <p v-if="gpsError" class="reg-gps-err">
              <PhWarningCircle weight="duotone" :size="10" />{{ gpsError }}
            </p>

            <!-- 景区列表 -->
            <div class="reg-spot-list">
              <div v-if="spotsLoading" class="reg-spot-empty">
                <PhCircleNotch weight="duotone" :size="18" class="spin" />
                <p>加载景区中…</p>
              </div>
              <template v-else>
                <div v-for="spot in filteredRegSpots" :key="spot.id"
                  class="reg-spot-item"
                  :class="{ selected: reg.scenicSpotId === spot.id }"
                  @click="selectRegSpot(spot)"
                >
                  <div class="reg-spot-icon"
                    :style="{ color: themeColor(spot.theme), background: themeColor(spot.theme)+'18' }">
                    <component :is="themeIcon(spot.theme)" :size="12" />
                  </div>
                  <div class="reg-spot-body">
                    <span class="reg-spot-name">{{ spot.name }}</span>
                    <span class="reg-spot-meta">{{ spot.province }}</span>
                  </div>
                  <div class="reg-spot-right">
                    <span class="reg-theme-badge"
                      :style="{ color: themeColor(spot.theme), background: themeColor(spot.theme)+'15' }">
                      {{ themeLabel(spot.theme) }}
                    </span>
                    <span v-if="spot.distance != null" class="reg-dist">{{ formatDist(spot.distance) }}</span>
                    <PhCheck weight="duotone" v-if="reg.scenicSpotId === spot.id"
                      :size="12"
                      :style="{ color: themeColor(spot.theme) }" />
                  </div>
                </div>
                <div v-if="filteredRegSpots.length === 0" class="reg-spot-empty">
                  <PhMagnifyingGlass weight="duotone" :size="18" />
                  <p>未找到相关景区</p>
                </div>
              </template>
            </div>

            <!-- 已识别类型提示 -->
            <div v-if="reg.scenicSpotId && detectedScene" class="reg-detected">
              <span class="reg-detected-ico" :style="{ background: detectedScene.color + '18', color: detectedScene.color }">✓</span>
              已识别为&nbsp;<strong :style="{ color: detectedScene.color }">{{ detectedScene.name }}</strong>&nbsp;类景区，配色已匹配
            </div>

            <p v-if="errMsg"     class="l-err"><PhWarningCircle weight="duotone" :size="12" />{{ errMsg }}</p>
            <p v-if="successMsg" class="l-ok"><PhCheckCircle weight="duotone" :size="12" />{{ successMsg }}</p>

            <div class="reg-actions">
              <button class="l-back" @click="regStep = 2">← 上一步</button>
              <button class="l-btn reg-submit" @click="handleRegister" :disabled="busy || !reg.scenicSpotId">
                <PhCircleNotch weight="duotone" v-if="busy" :size="15" class="spin" />
                {{ busy ? '注册中…' : '完成注册' }}
              </button>
            </div>
          </div>

          </transition>

          <p class="l-switch">已有账号？<span @click="switchTab('login')">立即登录</span></p>
        </div>
        </transition>

      </div>

      <p class="l-copy">途叨叨 · 通用智能景区管理方案</p>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useSceneStore } from '@/stores/scene'
import { SCENES, applyTheme } from '@/utils/themes'
import PhUser from '@phosphor-icons/vue/dist/icons/PhUser.vue.mjs'
import PhLock from '@phosphor-icons/vue/dist/icons/PhLock.vue.mjs'
import PhEye from '@phosphor-icons/vue/dist/icons/PhEye.vue.mjs'
import PhEyeSlash from '@phosphor-icons/vue/dist/icons/PhEyeSlash.vue.mjs'
import PhWarningCircle from '@phosphor-icons/vue/dist/icons/PhWarningCircle.vue.mjs'
import PhCircleNotch from '@phosphor-icons/vue/dist/icons/PhCircleNotch.vue.mjs'
import PhCaretLeft from '@phosphor-icons/vue/dist/icons/PhCaretLeft.vue.mjs'
import PhCaretRight from '@phosphor-icons/vue/dist/icons/PhCaretRight.vue.mjs'
import PhShieldCheck from '@phosphor-icons/vue/dist/icons/PhShieldCheck.vue.mjs'
import PhIdentificationCard from '@phosphor-icons/vue/dist/icons/PhIdentificationCard.vue.mjs'
import PhPhone from '@phosphor-icons/vue/dist/icons/PhPhone.vue.mjs'
import PhEnvelopeSimple from '@phosphor-icons/vue/dist/icons/PhEnvelopeSimple.vue.mjs'
import PhBriefcase from '@phosphor-icons/vue/dist/icons/PhBriefcase.vue.mjs'
import PhUserGear from '@phosphor-icons/vue/dist/icons/PhUserGear.vue.mjs'
import PhCheckCircle from '@phosphor-icons/vue/dist/icons/PhCheckCircle.vue.mjs'
import PhMagnifyingGlass from '@phosphor-icons/vue/dist/icons/PhMagnifyingGlass.vue.mjs'
import PhX from '@phosphor-icons/vue/dist/icons/PhX.vue.mjs'
import PhNavigationArrow from '@phosphor-icons/vue/dist/icons/PhNavigationArrow.vue.mjs'
import PhMapPin from '@phosphor-icons/vue/dist/icons/PhMapPin.vue.mjs'
import PhCheck from '@phosphor-icons/vue/dist/icons/PhCheck.vue.mjs'
import PhMountains from '@phosphor-icons/vue/dist/icons/PhMountains.vue.mjs'
import PhBuildings from '@phosphor-icons/vue/dist/icons/PhBuildings.vue.mjs'
import PhLeaf from '@phosphor-icons/vue/dist/icons/PhLeaf.vue.mjs'
import PhFlame from '@phosphor-icons/vue/dist/icons/PhFlame.vue.mjs'
import PhCpu from '@phosphor-icons/vue/dist/icons/PhCpu.vue.mjs'
import PhSun from '@phosphor-icons/vue/dist/icons/PhSun.vue.mjs'
import PhMoon from '@phosphor-icons/vue/dist/icons/PhMoon.vue.mjs'

const ANALYTICS_BASE = '/cloud'

// ── 明暗模式（与 admin-main.js / 侧栏按钮共用 'admin-theme' 约定）──
const THEME_KEY = 'admin-theme'
const isDark = ref(document.documentElement.classList.contains('admin-dark'))
function toggleTheme() {
  isDark.value = !isDark.value
  document.documentElement.classList.toggle('admin-dark', isDark.value)
  localStorage.setItem(THEME_KEY, isDark.value ? 'dark' : 'light')
  window.dispatchEvent(new Event('admin-theme-change'))
}

// API scenic_id → 本地元数据（API 只返回 id + name，省份/主题/坐标/描述从这里补全）
const SPOT_META = {
  lingshan:    { theme: 'buddhist',    province: '江苏无锡',   lat: 31.57, lng: 120.26, desc: '中国最大露天佛教文化景区' },
  nihuawan:    { theme: 'buddhist',    province: '江苏无锡',   lat: 31.53, lng: 120.24, desc: '禅意小镇，灵山脚下的心灵栖息地' },
  xihu:        { theme: 'nature',      province: '浙江杭州',   lat: 30.24, lng: 120.13, desc: '世界文化遗产，江南山水胜地' },
  huangshan:   { theme: 'nature',      province: '安徽黄山',   lat: 30.13, lng: 118.17, desc: '天下第一奇山' },
  gugong:      { theme: 'historical',  province: '北京',       lat: 39.91, lng: 116.39, desc: '中国古代宫廷建筑之精华' },
  zhangjiajie: { theme: 'nature',      province: '湖南张家界', lat: 29.12, lng: 110.48, desc: '世界自然遗产，阿凡达取景地' },
  bingmayong:  { theme: 'historical',  province: '陕西西安',   lat: 34.38, lng: 109.27, desc: '世界第八大奇迹' },
  mogaoku:     { theme: 'historical',  province: '甘肃敦煌',   lat: 40.04, lng: 94.81,  desc: '丝绸之路上的艺术宝库' },
}

// 景区 theme → 管理端 scene_type
const THEME_TO_SCENE = {
  buddhist:    'historical',
  nature:      'natural',
  ancient_town:'historical',
  historical:  'historical',
  modern:      'park',
}

function themeIcon(theme) {
  return { buddhist: PhMountains, nature: PhLeaf, ancient_town: PhFlame, historical: PhBuildings, modern: PhCpu }[theme] || PhMapPin
}
// 徽章色分明暗两套：浅色沿用品牌深蓝系，深色换高亮度霓虹系（深蓝压暗底看不清）
const THEME_COLOR_LIGHT = { buddhist:'#004098', nature:'#005A8B', ancient_town:'#1A5BAE', historical:'#002D70', modern:'#0052CC' }
const THEME_COLOR_DARK  = { buddhist:'#A78BFA', nature:'#34D399', ancient_town:'#FBBF24', historical:'#7DD3FC', modern:'#22D3EE' }
function themeColor(theme) {
  const map = isDark.value ? THEME_COLOR_DARK : THEME_COLOR_LIGHT
  return map[theme] || (isDark.value ? '#A78BFA' : '#004098')
}
function themeLabel(theme) {
  return { buddhist:'佛教文化', nature:'自然山水', ancient_town:'古镇民俗', historical:'历史遗址', modern:'现代主题' }[theme] || '综合'
}
function formatDist(m) {
  return m < 1000 ? `${Math.round(m)}m` : `${(m/1000).toFixed(1)}km`
}
function haversine(lat1, lng1, lat2, lng2) {
  const R = 6371000, toRad = d => d * Math.PI / 180
  const dLat = toRad(lat2-lat1), dLng = toRad(lng2-lng1)
  const a = Math.sin(dLat/2)**2 + Math.cos(toRad(lat1))*Math.cos(toRad(lat2))*Math.sin(dLng/2)**2
  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a))
}

const router     = useRouter()
const authStore  = useAuthStore()
const sceneStore = useSceneStore()

const tab        = ref('login')
const foc        = ref('')
const see        = ref(false)
const busy       = ref(false)
const errMsg     = ref('')
const successMsg = ref('')
const remember   = ref(false)
const regStep    = ref(1)
const form = ref({ username: '', password: '' })
const reg  = ref({
  username: '', password: '', confirm: '',
  realName: '', phone: '', email: '', department: '', position: '',
  sceneType: 'historical', scenicSpotId: '',
})
const DEPARTMENTS = ['运营管理部', '游客服务部', '市场营销部', '信息技术部', '安全保卫部', '综合办公室', '其他']

// 景区搜索 / GPS
const searchText  = ref('')
const searchFocus = ref(false)
const gpsLoading  = ref(false)
const gpsError    = ref('')
const gpsUsed     = ref(false)
const spotsWithDist = ref([])
const spotsLoading  = ref(false)

async function loadScenicSpots() {
  spotsLoading.value = true
  try {
    const res = await fetch(`${ANALYTICS_BASE}/analytics/bi/scenics`)
    if (!res.ok) throw new Error()
    const data = await res.json()
    spotsWithDist.value = (data.scenics || []).map(s => {
      const meta = SPOT_META[s.scenic_id] || {}
      return {
        id:       s.scenic_id,
        name:     s.name,
        theme:    meta.theme    || 'historical',
        province: meta.province || '',
        lat:      meta.lat      || 0,
        lng:      meta.lng      || 0,
        desc:     meta.desc     || '',
        distance: null,
      }
    })
  } catch {
    spotsWithDist.value = sceneStore.scenicSpots.map(s => ({ ...s, distance: null }))
  } finally {
    spotsLoading.value = false
  }
}

const filteredRegSpots = computed(() => {
  let list = spotsWithDist.value
  const q = searchText.value.trim()
  if (q) list = list.filter(s => s.name.includes(q) || s.province.includes(q) || s.desc.includes(q))
  return list
})

const detectedScene = computed(() =>
  SCENES.find(s => s.key === reg.value.sceneType) || null
)

function selectRegSpot(spot) {
  reg.value.scenicSpotId = spot.id
  reg.value.sceneType    = THEME_TO_SCENE[spot.theme] || 'historical'
  applyTheme(reg.value.sceneType)   // 即时预览配色
}

function handleGPS() {
  if (!navigator.geolocation) { gpsError.value = '浏览器不支持 GPS'; return }
  gpsLoading.value = true; gpsError.value = ''
  navigator.geolocation.getCurrentPosition(
    pos => {
      const { latitude: lat, longitude: lng } = pos.coords
      spotsWithDist.value = spotsWithDist.value
        .map(s => ({ ...s, distance: haversine(lat, lng, s.lat, s.lng) }))
        .sort((a, b) => a.distance - b.distance)
      gpsUsed.value = true; gpsLoading.value = false
      if (!reg.value.scenicSpotId) selectRegSpot(spotsWithDist.value[0])
    },
    () => { gpsLoading.value = false; gpsError.value = '定位失败，请手动搜索' }
  )
}

function switchTab(t) {
  tab.value = t
  regStep.value = 1
  errMsg.value = ''
  successMsg.value = ''
  see.value = false
  foc.value = ''
}

function nextStep() {
  errMsg.value = ''
  const { username, password, confirm } = reg.value
  if (!username.trim() || !password || !confirm) { errMsg.value = '请填写所有字段'; return }
  if (!/^[\w]{4,20}$/.test(username.trim())) { errMsg.value = '用户名须为 4–20 位字母、数字或下划线'; return }
  if (password.length < 6) { errMsg.value = '密码至少需要 6 位'; return }
  if (password !== confirm) { errMsg.value = '两次密码不一致'; return }
  regStep.value = 2
}

function nextStep2() {
  errMsg.value = ''
  const { realName, phone, email, department } = reg.value
  if (!realName.trim()) { errMsg.value = '请填写真实姓名'; return }
  if (realName.trim().length < 2 || realName.trim().length > 20) { errMsg.value = '姓名长度须为 2–20 个字符'; return }
  if (!phone.trim()) { errMsg.value = '请填写联系电话'; return }
  if (!/^1[3-9]\d{9}$/.test(phone.trim())) { errMsg.value = '请输入正确的 11 位手机号'; return }
  if (email.trim() && !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email.trim())) { errMsg.value = '邮箱格式不正确'; return }
  if (!department) { errMsg.value = '请选择所属部门'; return }
  regStep.value = 3
}

const slides = [
  { title: '数字人智能导览', desc: '自动识别游客需求，提供个性化景区导览服务' },
  { title: '知识库上传管理', desc: '便捷上传景区资料，构建专属知识问答体系' },
  { title: '数据分析统计',   desc: '实时掌握游客互动数据，助力景区运营决策' },
]

const cur = ref(0)
let timer = null

function prev() { cur.value = (cur.value - 1 + slides.length) % slides.length; resetTimer() }
function next() { cur.value = (cur.value + 1) % slides.length; resetTimer() }
function go(i)  { cur.value = i; resetTimer() }

function resetTimer() {
  clearInterval(timer)
  timer = setInterval(next, 4000)
}

onMounted(() => { timer = setInterval(next, 4000); loadScenicSpots() })
onUnmounted(() => clearInterval(timer))

async function handleLogin() {
  errMsg.value = ''
  if (!form.value.username.trim() || !form.value.password) {
    errMsg.value = '请填写用户名和密码'; return
  }
  busy.value = true
  try {
    await authStore.login(form.value.username.trim(), form.value.password)
    router.push('/')
  } catch (e) {
    errMsg.value = e.response?.data?.detail || e.message || '用户名或密码错误'
  } finally {
    busy.value = false
  }
}

async function handleRegister() {
  errMsg.value = ''
  successMsg.value = ''
  busy.value = true
  try {
    await authStore.register(reg.value.username.trim(), reg.value.password, reg.value.sceneType, reg.value.scenicSpotId || null, {
      real_name:  reg.value.realName.trim(),
      phone:      reg.value.phone.trim(),
      email:      reg.value.email.trim(),
      department: reg.value.department,
      position:   reg.value.position.trim(),
    })
    successMsg.value = '注册成功，正在进入…'
    reg.value = {
      username: '', password: '', confirm: '',
      realName: '', phone: '', email: '', department: '', position: '',
      sceneType: 'historical', scenicSpotId: '',
    }
    setTimeout(() => router.push('/'), 800)
  } catch (e) {
    errMsg.value = e.response?.data?.detail || e.message || '注册失败，请重试'
    regStep.value = 1
  } finally {
    busy.value = false
  }
}
</script>

<style scoped lang="scss">
/* ── 整体布局 ── */
.lp {
  display: flex;
  width: 100vw;
  height: 100vh;
  overflow: hidden;
  font-family: var(--font-sans);
  /* 整页一张连续渐变：左侧 HHU 蓝在中缝(58%)前后羽化过渡进右侧纸白，消除两栏割裂感。
     深色模式由 admin-dark.css 覆盖为深紫→深蓝底的同款连续渐变 */
  /* 羽化带用多级中间色标做缓入缓出，避免斜率突变产生马赫带（视觉亮线） */
  background: linear-gradient(90deg,
    #062A56 0%, #004098 34%, #0A5AB8 44%,
    #2E6BBE 48%, #6D9BD3 53%, #A9C4E5 58%,
    #D7E3F3 62%, var(--c-paper-2) 66%, var(--c-paper-2) 100%);
}

/* ── 明暗切换按钮（token 驱动，两种模式自适应）── */
.theme-fab {
  position: fixed;
  top: 18px; right: 20px;
  z-index: 50;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 32px;
  padding: 0 13px;
  border-radius: 999px;
  border: 1px solid var(--c-border);
  background: var(--c-surface);
  color: var(--c-ink-3);
  font-size: 12px;
  font-weight: 500;
  font-family: var(--font-sans);
  cursor: pointer;
  box-shadow: var(--shadow-xs);
  -webkit-backdrop-filter: blur(6px);
  backdrop-filter: blur(6px);
  transition: color .18s, border-color .18s, box-shadow .18s;

  &:hover {
    color: var(--c-gold);
    border-color: var(--c-gold-bdr, var(--c-gold));
    box-shadow: 0 0 0 3px var(--c-gold-bg, rgba(0,64,152,0.10));
  }
  &:active { transform: translateY(1px); }
  svg { flex-shrink: 0; }
}

/* 图标日月旋转切换 */
.tspin-enter-active, .tspin-leave-active { transition: transform .22s ease, opacity .22s ease; }
.tspin-enter-from { transform: rotate(-90deg) scale(.5); opacity: 0; }
.tspin-leave-to   { transform: rotate(90deg) scale(.5); opacity: 0; }

/* ── 左侧展示区 ── */
.showcase {
  flex: 0 0 58%;
  position: relative;
  /* 背景透明：蓝色渐变由父级 .lp 整页画布提供，与右侧无缝衔接 */
  background: transparent;
  display: flex;
  flex-direction: column;
  padding: 32px 40px 28px;
  overflow: hidden;

  /* 顶部光晕：天蓝柔光 */
  &::before {
    content: '';
    position: absolute;
    width: 500px; height: 500px;
    border-radius: 50%;
    background: radial-gradient(circle, rgba(125,211,252,0.16) 0%, transparent 65%);
    top: -180px; left: -100px;
    pointer-events: none;
  }
  /* 底部光晕：天蓝微光（不能用白色、不能贴右缘——会叠亮渐变羽化带） */
  &::after {
    content: '';
    position: absolute;
    width: 400px; height: 400px;
    border-radius: 50%;
    background: radial-gradient(circle, rgba(125,211,252,0.10) 0%, transparent 65%);
    bottom: -150px; right: 30%;
    pointer-events: none;
  }
}

.s-logo {
  display: flex;
  align-items: center;
  gap: 12px;
  position: relative; z-index: 1;

  .s-logo-img {
    width: 40px;
    height: 40px;
    object-fit: contain;
    flex-shrink: 0;
  }

  span {
    font-size: 24px;
    font-weight: 700;
    color: #fff;   /* 蓝底上用白字；深色模式由 admin-dark.css 覆盖回紫罗兰 */
    letter-spacing: 1px;
    font-family: var(--font-serif);
  }
}

/* 轮播舞台 */
.s-stage {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  z-index: 1;
  min-height: 0;
}

.s-slide {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  padding: 0 56px;
  width: 100%;
}

.s-art {
  width: 100%;
  max-width: 420px;
  margin-bottom: 20px;

  svg {
    width: 100%;
    height: auto;
    max-height: 260px;
  }
}

.s-title {
  font-size: 22px;
  font-weight: 700;
  color: rgba(255,255,255,0.96);
  margin-bottom: 8px;
  letter-spacing: 0.5px;
  font-family: var(--font-serif);
}

.s-desc {
  font-size: 13px;
  color: rgba(255,255,255,0.62);
  line-height: 1.7;
  max-width: 340px;
}

/* 箭头按钮 */
.s-arr {
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  width: 36px; height: 36px;
  border-radius: 50%;
  border: 1px solid rgba(255,255,255,0.3);
  background: rgba(255,255,255,0.12);
  color: rgba(255,255,255,0.85);
  cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  transition: all 0.18s;
  z-index: 2;

  &:hover { background: rgba(255,255,255,0.22); border-color: rgba(255,255,255,0.5); }
  &.s-arr-l { left: 4px; }
  /* 右箭头落在渐变过渡带偏白区域，浅色模式换蓝描边样式（深色模式由 admin-dark.css 拉回白色幽灵样式） */
  &.s-arr-r {
    right: 4px;
    border-color: rgba(0,64,152,0.30);
    background: rgba(0,64,152,0.06);
    color: #004098;
    &:hover { background: rgba(0,64,152,0.12); border-color: rgba(0,64,152,0.50); }
  }
}

/* 指示点 */
.s-dots {
  display: flex;
  justify-content: center;
  gap: 8px;
  position: relative; z-index: 1;
  padding-bottom: 4px;
}

.s-dot {
  width: 8px; height: 8px;
  border-radius: 50%;
  background: rgba(255,255,255,0.2);
  cursor: pointer;
  transition: all 0.2s;

  &.on {
    width: 22px;
    border-radius: 4px;
    background: #FBBF24;   /* 暖金激活点，呼应插画金色元素；深色模式覆盖回紫罗兰 */
  }
}

/* 轮播切换动画 */
.cfade-enter-active,
.cfade-leave-active { transition: opacity 0.3s ease, transform 0.3s ease; }
.cfade-enter-from   { opacity: 0; transform: translateX(16px); }
.cfade-leave-to     { opacity: 0; transform: translateX(-16px); }

/* ── 右侧登录区 ── */
.login-side {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: transparent;   /* 底色由 .lp 整页渐变提供 */
  padding: 40px 48px;
  position: relative;
}

.l-card {
  width: 100%;
  max-width: 340px;
  background: var(--c-surface);
  border: 1px solid var(--c-border);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow);
  overflow: hidden;
}

/* Tab 切换栏 */
.l-tabs {
  position: relative;
  display: flex;
  background: var(--c-paper);
  padding: 4px;
  border-bottom: 1px solid var(--c-border);
}

.l-tab {
  flex: 1;
  padding: 9px;
  border: none;
  background: transparent;
  font-size: 13px;
  font-weight: 500;
  color: var(--c-ink-4);
  cursor: pointer;
  border-radius: var(--radius-sm);
  transition: color 0.2s;
  font-family: var(--font-sans);
  position: relative; z-index: 1;

  &.active { color: var(--c-ink); font-weight: 600; }
}

.l-tab-bar {
  position: absolute;
  top: 4px; bottom: 4px;
  width: calc(50% - 4px);
  background: var(--c-surface);
  border-radius: var(--radius-sm);
  border: 1px solid var(--c-border);
  box-shadow: var(--shadow-xs);
  transition: left 0.22s cubic-bezier(0.4,0,0.2,1);
  z-index: 0;
}

/* 表单体 */
.l-body {
  padding: 28px 32px 24px;
}

.l-title {
  font-size: 22px;
  font-weight: 700;
  color: var(--c-ink);
  margin-bottom: 5px;
  font-family: var(--font-serif);
  letter-spacing: 0.5px;
}

.l-sub {
  font-size: 12px;
  color: var(--c-ink-4);
  margin-bottom: 24px;
  letter-spacing: 2px;
}

/* 输入框 */
.l-field {
  display: flex;
  align-items: center;
  gap: 10px;
  border: 1px solid var(--c-border);
  border-radius: var(--radius-sm);
  background: var(--c-paper);
  padding: 11px 14px;
  margin-bottom: 16px;
  transition: all 0.18s;

  &.foc {
    border-color: var(--c-gold);
    background: var(--c-surface);
    box-shadow: 0 0 0 3px var(--c-gold-bg, rgba(0,64,152,0.12));
  }

  &.err {
    border-color: rgba(190,53,53,0.5);
  }
}

.l-ico {
  color: var(--c-ink-4);
  flex-shrink: 0;
}

.l-in {
  flex: 1;
  border: none;
  background: transparent;
  outline: none;
  font-size: 14px;
  color: var(--c-ink);
  font-family: var(--font-sans);
  min-width: 0;

  &::placeholder { color: var(--c-ink-4); }
}

/* 下拉选择（所属部门）：去原生外观 + 自绘下箭头，与 .l-in 视觉统一 */
.l-field--select { position: relative; }
.l-select {
  appearance: none;
  -webkit-appearance: none;
  -moz-appearance: none;
  cursor: pointer;
  padding-right: 20px;
}
.l-select:invalid { color: var(--c-ink-4); }   /* 未选择时占位灰 */
.l-select option { color: #1f2330; }
.l-field--select::after {
  content: '';
  position: absolute;
  right: 16px;
  top: 50%;
  width: 7px;
  height: 7px;
  border-right: 1.5px solid var(--c-ink-4);
  border-bottom: 1.5px solid var(--c-ink-4);
  transform: translateY(-70%) rotate(45deg);
  pointer-events: none;
}

.l-eye {
  background: none;
  border: none;
  cursor: pointer;
  color: var(--c-ink-4);
  padding: 0;
  display: flex;
  align-items: center;
  transition: color 0.15s;
  &:hover { color: var(--c-ink-3); }
}

/* 记住密码 */
.l-rem {
  display: flex;
  align-items: center;
  gap: 7px;
  cursor: pointer;
  margin-bottom: 20px;
  user-select: none;

  span {
    font-size: 13px;
    color: var(--c-ink-3);
  }
}

.l-chk {
  width: 15px; height: 15px;
  accent-color: var(--c-gold);
  cursor: pointer;
}

/* 错误提示（token 驱动，深色下自动换暗底亮红） */
.l-err {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 12px;
  color: var(--c-red, #be3535);
  background: var(--c-red-bg, #fff5f5);
  border-radius: 5px;
  padding: 7px 10px;
  margin-bottom: 14px;

  svg { flex-shrink: 0; }
}

/* 成功提示 */
.l-ok {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 12px;
  color: var(--c-green);
  background: var(--c-green-bg);
  border-radius: 5px;
  padding: 7px 10px;
  margin-bottom: 14px;

  svg { flex-shrink: 0; }
}

/* 切换提示 */
.l-switch {
  text-align: center;
  font-size: 12px;
  color: var(--c-ink-4);
  margin-top: 4px;

  span {
    color: var(--c-gold);
    cursor: pointer;
    font-weight: 500;
    transition: color 0.15s;
    &:hover { color: var(--c-gold-2); }
  }
}

/* Tab 内容切换动画 */
.tfade-enter-active, .tfade-leave-active { transition: opacity 0.18s ease; }
.tfade-enter-from, .tfade-leave-to { opacity: 0; }

/* 登录按钮 */
.l-btn {
  width: 100%;
  padding: 12px;
  border: 1px solid var(--c-gold);
  border-radius: var(--radius-sm);
  background: var(--c-gold);
  color: #fff;
  font-size: 15px;
  font-weight: 600;
  font-family: var(--font-sans);
  cursor: pointer;
  transition: all 0.18s;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 7px;
  margin-bottom: 14px;

  &:hover:not(:disabled) { background: var(--c-gold-2); border-color: var(--c-gold-2); }
  &:disabled { opacity: 0.65; cursor: not-allowed; }
}

/* 版权 */
.l-copy {
  position: absolute;
  bottom: 24px;
  font-size: 12px;
  color: var(--c-ink-4);
  letter-spacing: 1px;
}

/* 旋转动画 */
.spin { animation: spin 1s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

/* ── 注册进度条 ── */
.reg-bar-wrap {
  height: 2px;
  background: var(--c-border);
  border-radius: 2px;
  margin-bottom: 24px;
  overflow: hidden;
}
.reg-bar-fill {
  height: 100%;
  background: var(--c-gold);
  border-radius: 2px;
  transition: width 0.4s cubic-bezier(0.4, 0, 0.2, 1);
}

/* 步骤内容切换 */
.sfade-enter-active, .sfade-leave-active { transition: opacity 0.15s, transform 0.15s; }
.sfade-enter-from { opacity: 0; transform: translateX(10px); }
.sfade-leave-to  { opacity: 0; transform: translateX(-10px); }

/* ── 景区搜索 ── */
.reg-search-row {
  display: flex;
  gap: 8px;
  margin-bottom: 8px;
}

.reg-search-box {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 7px;
  border: 1px solid var(--c-border);
  border-radius: var(--radius-sm);
  background: var(--c-paper);
  padding: 8px 10px;
  transition: border-color .15s, box-shadow .15s;

  &.focused {
    border-color: var(--c-gold);
    box-shadow: 0 0 0 2px var(--c-gold-bg, rgba(0,64,152,0.12));
    background: var(--c-surface);
  }
}

.reg-search-ico { color: var(--c-ink-4); flex-shrink: 0; }

.reg-search-in {
  flex: 1; border: none; background: transparent; outline: none;
  font-size: 12px; color: var(--c-ink); font-family: var(--font-sans); min-width: 0;
  &::placeholder { color: var(--c-ink-4); }
}

.reg-clear {
  border: none; background: none; cursor: pointer; color: var(--c-ink-4);
  padding: 0; display: flex; align-items: center;
  &:hover { color: var(--c-ink-3); }
}

.reg-gps-btn {
  width: 36px; height: 36px; border-radius: var(--radius-sm);
  border: 1px solid var(--c-border); background: var(--c-paper);
  color: var(--c-ink-3); cursor: pointer; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
  transition: all .15s;
  &:hover { border-color: var(--c-gold); color: var(--c-gold); }
  &.active { border-color: var(--c-green); color: var(--c-green); background: var(--c-green-bg); }
  &.loading { opacity: 0.7; cursor: wait; }
}

.reg-gps-ok {
  display: flex; align-items: center; gap: 4px;
  font-size: 11px; color: var(--c-green); margin-bottom: 8px;
}
.reg-gps-err {
  display: flex; align-items: center; gap: 4px;
  font-size: 11px; color: var(--c-red); margin-bottom: 8px;
}

/* ── 景区列表 ── */
.reg-spot-list {
  border: 1px solid var(--c-border);
  border-radius: var(--radius);
  overflow: hidden;
  max-height: 210px;
  overflow-y: auto;
  margin-bottom: 10px;
}

.reg-spot-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 9px 10px;
  cursor: pointer;
  border-bottom: 1px solid var(--c-border);
  transition: background .12s;

  &:last-child { border-bottom: none; }
  &:hover { background: var(--c-paper-2); }
  &.selected { background: var(--c-gold-bg); }
}

.reg-spot-icon {
  width: 26px; height: 26px; border-radius: var(--radius-xs);
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
}

.reg-spot-body {
  flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 1px;
  .reg-spot-name { font-size: 12px; font-weight: 600; color: var(--c-ink); }
  .reg-spot-meta { font-size: 10px; color: var(--c-ink-4); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
}

.reg-spot-right {
  display: flex; align-items: center; gap: 5px; flex-shrink: 0;
}

.reg-theme-badge {
  font-size: 10px; font-weight: 500; padding: 2px 5px;
  border-radius: var(--radius-xs); white-space: nowrap;
}

.reg-dist { font-size: 10px; color: var(--c-ink-4); }

.reg-spot-empty {
  display: flex; flex-direction: column; align-items: center; gap: 6px;
  padding: 20px; color: var(--c-ink-4); font-size: 12px;
}

/* ── 已识别类型 ── */
.reg-detected {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--c-ink-3);
  background: var(--c-paper);
  border: 1px solid var(--c-border);
  border-radius: var(--radius-sm);
  padding: 8px 10px;
  margin-bottom: 14px;

  .reg-detected-ico {
    width: 16px; height: 16px; border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-size: 9px; font-weight: 700; flex-shrink: 0;
  }
}

/* ── 注册按钮行 ── */
.reg-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 14px;
}
.l-back {
  display: flex; align-items: center; gap: 3px;
  padding: 10px 14px;
  border: 1px solid var(--c-border);
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--c-ink-3);
  font-size: 13px;
  cursor: pointer;
  font-family: var(--font-sans);
  white-space: nowrap;
  transition: all .15s;
  &:hover { border-color: var(--c-border-2); color: var(--c-ink-2); }
}
.reg-submit { flex: 1; margin-bottom: 0; }
</style>
