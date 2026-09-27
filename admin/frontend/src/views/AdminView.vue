<template>
  <div class="admin-layout">

    <!-- ── 顶部导航栏 ── -->
    <header class="top-nav">
      <div class="tn-left">
        <img class="tn-logo" src="@/assets/logo-tudaodao.png" alt="途叨叨" aria-hidden="true" />
        <span class="tn-brand">途叨叨</span>
        <span class="tn-divider" aria-hidden="true"></span>
        <span class="tn-scenic">景区管理后台</span>
      </div>
      <div class="tn-mid" v-if="danmakuOn">
        <span class="tn-dmk-label"><IconMessages :size="14" aria-hidden="true" />游客正在问</span>
        <DanmakuFlow :key="'tn-' + sceneStore.scenicId" :scenic-id="sceneStore.scenicId || 'lingshan'"
          :lanes="1" variant="light" :speed="68" class="tn-dmk" />
      </div>
      <div class="tn-right">
        <span class="tn-date">{{ dashDate }}</span>
        <span class="tn-clock">{{ dashClock }}</span>
      </div>
    </header>


    <!-- ── 左侧导航栏 ── -->
    <aside class="sidebar">
<nav class="sidebar-nav">
        <template v-for="g in navGroups" :key="g.label">
          <div class="nav-group-label">{{ g.label }}</div>
          <button
            v-for="item in g.items" :key="item.key"
            class="nav-item"
            :class="{ active: activeTab === item.key }"
            :aria-current="activeTab === item.key ? 'page' : undefined"
            @click="selectNav(item.key)"
          >
            <component :is="item.icon" :size="16" aria-hidden="true" />
            <span>{{ item.label }}</span>
          </button>
        </template>

        <!-- 数据大屏 = 全屏投放模式（非页面 tab），入口是一张醒目的启动卡 -->
        <div class="nav-group-label">投放</div>
        <button class="bigscreen-card" @click="enterDashboard">
          <span class="bs-ico"><PhMonitorPlay weight="duotone" :size="20" aria-hidden="true" /></span>
          <span class="bs-txt">
            <b>数据大屏</b>
            <i>全屏投放 · Esc 随时退出</i>
          </span>
        </button>
      </nav>

      <div class="sidebar-footer">
        <div class="sf-scenic">
          <span class="sf-scenic-ico"><PhMapPin weight="duotone" :size="16" /></span>
          <div class="sf-scenic-body">
            <span class="sf-scenic-name">{{ sceneStore.scenicName || '未绑定景区' }}</span>
            <span class="sf-scenic-status"><i class="sf-live-dot" />服务中</span>
          </div>
        </div>
        <div class="sf-account" v-if="authStore.user">
          <span class="sf-avatar">{{ (authStore.user.username || 'A').slice(0,1).toUpperCase() }}</span>
          <div class="sf-account-body">
            <span class="sf-account-name">{{ authStore.user.username }}</span>
            <span class="sf-account-role">管理员</span>
          </div>
          <button class="sf-icon-btn" @click="handleLogout" title="退出登录" aria-label="退出登录">
            <PhSignOut weight="duotone" :size="15" aria-hidden="true" />
          </button>
        </div>
        <button class="sf-theme-btn" @click="toggleTheme">
          <PhSun weight="duotone" v-if="sidebarDark" :size="14" />
          <PhMoon weight="duotone" v-else :size="14" />
          <span>{{ sidebarDark ? '切换浅色模式' : '切换深色模式' }}</span>
        </button>
      </div>
    </aside>

    <!-- ── 主内容区 ── -->
    <main class="admin-main">

      <!-- ═══ 形象管理 ═══ -->
      <div v-show="activeTab === 'avatar'" class="tab-content">
        <div class="page-header">
          <h2>数字人形象管理</h2>
          <span class="page-sub">为「{{ sceneStore.scenicName || '当前景区' }}」管理导览形象：发布可见性 · 艺名 · 服装 · 音色 · 背景 · 情绪 · 欢迎语，离线预览确认后一键应用到大屏</span>
        </div>

        <!-- KPI 概览条 -->
        <div class="rpt-kpi-card av2-kpi">
          <div class="rpt-kpi">
            <div class="rpt-kpi-ico k0"><PhUserCircle weight="duotone" :size="22" /></div>
            <div class="rpt-kpi-body"><span class="rpt-kpi-label">形象总数</span><span class="rpt-kpi-num">{{ kpiTotal }}</span></div>
          </div>
          <div class="rpt-kpi-div" />
          <div class="rpt-kpi">
            <div class="rpt-kpi-ico k1"><PhBroadcast weight="duotone" :size="22" /></div>
            <div class="rpt-kpi-body"><span class="rpt-kpi-label">本景区已发布</span><span class="rpt-kpi-num">{{ kpiPublished }}</span></div>
          </div>
          <div class="rpt-kpi-div" />
          <div class="rpt-kpi">
            <div class="rpt-kpi-ico k2"><PhCheckCircle weight="duotone" :size="22" /></div>
            <div class="rpt-kpi-body"><span class="rpt-kpi-label">底板就绪</span><span class="rpt-kpi-num">{{ kpiReady }}</span></div>
          </div>
          <div class="rpt-kpi-div" />
          <div class="rpt-kpi">
            <div class="rpt-kpi-ico k3"><PhMagicWand weight="duotone" :size="22" /></div>
            <div class="rpt-kpi-body"><span class="rpt-kpi-label">AI 定制</span><span class="rpt-kpi-num">{{ kpiCustom }}</span></div>
          </div>
        </div>

        <div class="av2-layout">
          <!-- 左列：形象库 + 参数工作台 -->
          <div class="av2-col-main">
            <!-- 形象库 -->
            <div class="card">
              <div class="rpt-card-hd">
                <PhUserCircle weight="duotone" :size="16" />
                <span class="rpt-card-title">形象库</span>
                <span class="rpt-hd-sub">点选进入工作台 · 开关控制游客端可见</span>
              </div>
              <div class="av-filters">
                <el-radio-group v-model="avStyle" size="small">
                  <el-radio-button v-for="s in AV_STYLES" :key="s" :value="s">{{ s }}</el-radio-button>
                </el-radio-group>
                <el-radio-group v-model="avGender" size="small">
                  <el-radio-button value="all">全部</el-radio-button>
                  <el-radio-button value="female">女</el-radio-button>
                  <el-radio-button value="male">男</el-radio-button>
                </el-radio-group>
              </div>
              <div class="av2-grid">
                <div v-for="a in shownAvatars" :key="a.id"
                  :class="['av2-card', { sel: a.id === draft.avatarId }]" @click="selectAvatar(a)">
                  <div class="av2-thumb">
                    <img :src="a.preview" :alt="a.name" loading="lazy" />
                    <PhCheckCircle weight="fill" v-if="a.id === draft.avatarId" class="av2-check" :size="18" />
                  </div>
                  <div class="av2-info">
                    <span class="av2-stage">{{ a.stage_name || a.name }}</span>
                    <span class="av2-orig">{{ a.name }}</span>
                    <div class="av2-pills">
                      <span :class="['sentiment-tag', a.published ? 'positive' : 'neutral']">{{ a.published ? '已发布' : '未发布' }}</span>
                      <span :class="['sentiment-tag', a.coming_soon ? 'negative' : 'neutral']">{{ a.coming_soon ? '未烘' : '就绪' }}</span>
                    </div>
                    <div class="av2-pubrow" @click.stop>
                      <span class="av2-pub-label">游客可见</span>
                      <el-switch v-model="a.published" size="small" :disabled="a.coming_soon" @change="(v) => togglePublish(a, v)" />
                    </div>
                  </div>
                </div>
                <p v-if="!shownAvatars.length" class="av-empty">该分类暂无形象</p>
              </div>
            </div>

            <!-- 参数工作台（离线，调整即预览） -->
            <div class="card">
              <div class="rpt-card-hd">
                <PhSlidersHorizontal weight="duotone" :size="16" />
                <span class="rpt-card-title">参数工作台</span>
                <span class="rpt-hd-sub">调整即离线预览 · 不影响大屏</span>
              </div>

              <div v-if="outfits.length" class="av2-field">
                <label class="av2-flabel"><PhTShirt weight="duotone" :size="14" />服装 · 同一张脸多套</label>
                <div class="av-wardrobe">
                  <button v-for="o in outfits" :key="o.id"
                    :class="['wd-card', { sel: o.id === draft.avatarId }]" @click="selectAvatar(o)">
                    <img :src="o.preview" :alt="o.outfit || o.name" loading="lazy" />
                    <span>{{ o.outfit || o.name }}</span>
                  </button>
                </div>
              </div>

              <div class="av2-field">
                <label class="av2-flabel"><PhTag weight="duotone" :size="14" />艺名 · 游客端显示</label>
                <el-input v-model="draft.stageName" maxlength="8" show-word-limit size="large"
                  placeholder="文艺平实、不低俗" @blur="saveStageName" @keyup.enter="saveStageName" />
              </div>

              <div class="av2-field">
                <label class="av2-flabel"><PhChatText weight="duotone" :size="14" />欢迎语 · 换上时播报</label>
                <el-input v-model="draft.welcome" type="textarea" :rows="2" maxlength="60" show-word-limit
                  resize="none" placeholder="留空则用默认欢迎语" @blur="saveWelcome" />
              </div>

              <div class="av2-field">
                <label class="av2-flabel"><PhSpeakerHigh weight="duotone" :size="14" />音色</label>
                <div class="av2-voice-row">
                  <el-select v-model="draft.voiceId" size="large" class="av-select" popper-class="av-opt-popper">
                    <el-option v-for="v in voices" :key="v.id" :value="v.id" :label="v.name">
                      <span class="opt-line"><b class="opt-name">{{ v.name }}</b><small class="opt-sub">{{ v.tone }}</small></span>
                    </el-option>
                  </el-select>
                  <button class="ghost-btn av2-try" :disabled="!canPlayVoice(draft.voiceId)" @click="tryVoice(draft.voiceId)">
                    <PhSpeakerHigh weight="duotone" :size="14" /> 试听
                  </button>
                </div>
              </div>

              <div class="av2-field">
                <label class="av2-flabel"><PhEye weight="duotone" :size="14" />场景背景</label>
                <el-select v-model="draft.bgId" size="large" class="av-select" popper-class="av-opt-popper" @change="refreshPlate">
                  <el-option v-for="b in backgrounds" :key="b.id" :value="b.id" :label="bgLabel(b.name)">
                    <span class="opt-line opt-bg">
                      <img v-if="b.preview" :src="b.preview" :alt="b.name" class="opt-thumb" loading="lazy" />
                      <span v-else class="opt-thumb opt-thumb-none"><PhEyeSlash weight="duotone" :size="13" /></span>
                      <span class="opt-name">{{ b.name }}</span>
                    </span>
                  </el-option>
                </el-select>
              </div>

              <div class="av2-field">
                <label class="av2-flabel"><PhSmiley weight="duotone" :size="14" />默认情绪基调</label>
                <div class="av2-inline">
                  <el-radio-group v-model="draft.emotion" size="small">
                    <el-radio-button value="neutral">平静</el-radio-button>
                    <el-radio-button value="happy">愉悦</el-radio-button>
                    <el-radio-button value="concerned">关切</el-radio-button>
                  </el-radio-group>
                  <span class="av2-inline-hint">应用后大屏实时生效</span>
                </div>
              </div>

              <div class="av2-field">
                <label class="av2-flabel"><PhSlidersHorizontal weight="duotone" :size="14" />说话嘴幅</label>
                <el-slider v-model="draft.lipScale" :min="0.5" :max="1.0" :step="0.02" :disabled="!lipEnabled"
                  :format-tooltip="(v) => v.toFixed(2)" :marks="{0.68:'默认',1:'原始'}" />
                <span class="av2-inline-hint">{{ lipEnabled ? '数值越小张口越含蓄（0.68≈刚刚不露齿），作用于两路直播流，「应用到大屏」后即时生效' : '当前为固定值' }}</span>
              </div>
            </div>
          </div>

          <!-- 右列：离线预览 + 应用闸门 + AI 定制 -->
          <div class="av2-col-preview">
            <div class="card">
              <div class="rpt-card-hd">
                <PhEye weight="duotone" :size="16" />
                <span class="rpt-card-title">形象预览</span>
                <span class="rpt-hd-sub">离线合成 · 零串扰</span>
              </div>
              <div class="av2-preview-box">
                <img v-if="plateUrl" :src="plateUrl" class="av2-preview-img" alt="形象预览" />
                <div v-else class="av2-preview-empty"><PhUserCircle weight="duotone" :size="40" /><p>选择形象查看预览</p></div>
                <span class="av2-preview-chip">{{ draft.stageName || '—' }}</span>
              </div>
              <p v-if="draft.welcome" class="av2-welcome">「{{ draft.welcome }}」</p>
              <p v-if="plateNote" class="av2-plate-note"><PhWarningCircle weight="duotone" :size="13" />{{ plateNote }}</p>
              <div class="av2-preview-meta">
                <span>音色 {{ selVoiceName || '—' }}</span>
                <span>情绪 {{ emoLabel(draft.emotion) }}</span>
              </div>

              <el-checkbox v-model="setAsDefault" size="small" class="av2-default-check">同时设为本景区默认形象</el-checkbox>
              <button class="primary-btn full-btn mt12" :disabled="applying || !draft.avatarId" @click="applyToScreen">
                <PhBroadcast weight="duotone" v-if="!applying" :size="14" />
                <PhCircleNotch weight="duotone" v-else :size="14" class="spin" />
                {{ applying ? '应用中…' : '应用到大屏' }}
              </button>
              <p class="av2-apply-hint">将改变现场大屏画面（每屏一流，应用者生效）</p>

              <button class="av2-monitor-toggle" @click="toggleMonitor">
                <PhMonitorPlay weight="duotone" :size="13" /> {{ monitorOpen ? '收起大屏实况' : '查看大屏实况（仅监看）' }}
              </button>
              <div v-show="monitorOpen" class="av2-monitor">
                <video ref="previewVideoEl" class="preview-video" muted autoplay playsinline />
              </div>
            </div>

            <div class="card">
              <div class="rpt-card-hd">
                <PhMagicWand weight="duotone" :size="16" />
                <span class="rpt-card-title">AI 定制形象</span>
                <span class="rpt-hd-sub">通义万相 · 人景一体</span>
              </div>
              <el-input v-model="customPrompt" type="textarea" :rows="2" resize="none"
                placeholder="描述形象（如：身着米色针织衫、温柔亲切的年轻女导游）" />
              <button class="primary-btn full-btn mt12" @click="handleGenerate" :disabled="sceneStore.isGeneratingAvatar">
                <PhSparkle weight="duotone" v-if="!sceneStore.isGeneratingAvatar" :size="14" />
                <PhCircleNotch weight="duotone" v-else :size="14" class="spin" />
                {{ sceneStore.isGeneratingAvatar ? '生成中…' : '生成并加入形象库' }}
              </button>
              <div v-if="sceneStore.isGeneratingAvatar" class="progress-wrap">
                <div class="progress-bar indeterminate"><div class="progress-fill" style="width:35%" /></div>
                <span>万相云端绘制中，已用时 {{ genElapsed }}s（通常 20-40s）</span>
              </div>
            </div>

            <div class="card">
              <div class="rpt-card-hd">
                <PhSparkle weight="duotone" :size="16" />
                <span class="rpt-card-title">甜美默认候选</span>
                <span class="rpt-hd-sub">批量生成 · 挑选 · 体检 · 设默认</span>
              </div>
              <button class="primary-btn full-btn" :disabled="candRunning" @click="genCandidates">
                <PhSparkle weight="duotone" v-if="!candRunning" :size="14" />
                <PhCircleNotch weight="duotone" v-else :size="14" class="spin" />
                {{ candRunning ? `生成中 ${candDone}/${candTarget}…` : '生成 6 张甜美候选' }}
              </button>
              <div v-if="candRunning" class="progress-wrap">
                <div class="progress-bar"><div class="progress-fill" :style="{width:`${candTarget?candDone/candTarget*100:0}%`}" /></div>
                <span>万相绘制中，每张约 30s（同 seed 双比例）</span>
              </div>
              <div v-if="candidates.length" class="cand-grid">
                <div v-for="c in candidates" :key="c.cand_id" :class="['cand-card',{sel:c.cand_id===candSel}]" @click="candSel=c.cand_id">
                  <img :src="candPreview(c)" :alt="c.cand_id" loading="lazy" />
                  <span :class="['cand-badge', c.centered?'ok':'warn']">
                    {{ c.centered ? '居中✓' : `偏${c.center_offset_pct}%` }}
                  </span>
                  <PhCheckCircle weight="fill" v-if="c.cand_id===candSel" class="cand-check" :size="16" />
                </div>
              </div>
              <div v-if="candSel" class="cand-adopt">
                <el-input v-model="candStageName" size="small" maxlength="8" placeholder="艺名（可选）" style="flex:1" />
                <button class="ghost-btn" :disabled="candAdopting || !candSelCentered" @click="adoptCandidate_">
                  {{ candAdopting ? '采用中…' : '采用为形象' }}
                </button>
              </div>
              <p v-if="candSel && !candSelCentered" class="av2-plate-note">
                <PhWarningCircle weight="duotone" :size="13" />该候选人物未居中，播放会裁切偏移，请挑居中的
              </p>
              <p class="cand-hint">采用后需在 GPU 机过 lipmatrix 开口体检，再「应用/设默认」上岗</p>
            </div>
          </div>
        </div>
      </div>

      <!-- ═══ 知识库管理 ═══ -->
      <div v-show="activeTab === 'knowledge'" class="tab-content">
        <div class="page-header">
          <h2>知识库管理</h2>
          <span class="page-sub">管理景区讲解词、文史资料、常见问答等知识内容</span>
        </div>

        <!-- 子 Tab 导航 -->
        <div class="kb-nav mb24">
          <button :class="['kb-nav-btn', { active: kbTab === 'upload' }]" @click="kbTab = 'upload'">
            <PhCloudArrowUp weight="duotone" :size="13" />文件上传
          </button>
          <button :class="['kb-nav-btn', { active: kbTab === 'faq' }]" @click="kbTab = 'faq'">
            <PhQuestion weight="duotone" :size="13" />FAQ 问答
          </button>
          <button :class="['kb-nav-btn', { active: kbTab === 'text' }]" @click="kbTab = 'text'">
            <PhPencilLine weight="duotone" :size="13" />文本段落
          </button>
          <button :class="['kb-nav-btn', { active: kbTab === 'config' }]" @click="kbTab = 'config'">
            <PhGear weight="duotone" :size="13" />检索设置
          </button>
          <button :class="['kb-nav-btn', { active: kbTab === 'selftest' }]" @click="kbTab = 'selftest'">
            <PhCheckCircle weight="duotone" :size="13" />知识库体检
          </button>
        </div>

        <!-- ── 文件上传 Tab ── -->
        <template v-if="kbTab === 'upload'">
          <div class="card mb16">
            <div class="card-title"><PhUpload weight="duotone" :size="14" />上传文档</div>
            <div class="upload-entry">
              <div class="upload-entry-info">
                <PhCloudArrowUp weight="duotone" :size="30" class="upload-ico" />
                <div>
                  <p class="upload-main">上传景区讲解词、文史资料等文档</p>
                  <p class="upload-hint">支持 .txt / .pdf / .docx / .md，单文件 ≤ 20MB，可批量上传</p>
                </div>
              </div>
              <button class="primary-btn lg" @click="openUploadDialog">
                <PhUpload weight="duotone" :size="15" />上传文档
              </button>
            </div>
          </div>

          <div class="card">
            <div v-if="docDeletePending" class="undo-toast">
              已删除「{{ docDeletePending.name }}」
              <button class="link-btn" style="color:var(--c-gold-3);margin-left:auto" @click="undoDeleteDoc">撤销</button>
            </div>
            <div class="card-title">
              <PhFileText weight="duotone" :size="14" />文档列表
              <div class="search-wrap ml-auto">
                <PhMagnifyingGlass weight="duotone" :size="13" class="search-ico" aria-hidden="true" />
                <input v-model="kbSearch" class="search-input" placeholder="搜索文档…" aria-label="搜索文档" />
              </div>
            </div>
            <el-table :data="filteredDocs" size="small">
              <el-table-column label="文档名称" min-width="200">
                <template #default="{ row }">
                  <div class="doc-cell">
                    <span class="doc-type" :class="row.type">{{ row.type.toUpperCase() }}</span>
                    {{ row.name }}
                  </div>
                </template>
              </el-table-column>
              <el-table-column prop="chunks" label="片段数" width="72" />
              <el-table-column prop="uploadTime" label="上传时间" width="138" />
              <el-table-column prop="size" label="大小" width="64" />
              <el-table-column label="状态" width="82">
                <template #default="{ row }">
                  <span class="status-pill" :class="[row.status === '已索引' ? 'green' : row.status === '不支持' ? 'red' : 'amber', { pulsing: row.status === '索引中' }]">{{ row.status }}</span>
                </template>
              </el-table-column>
              <el-table-column label="操作" width="130">
                <template #default="{ row }">
                  <div class="ops-cell">
                    <button class="link-btn rebuild" title="删除旧片段，重新解析原文件并分块向量化"
                      :disabled="row.status === '索引中'" @click="reindexDoc(row)">重建索引</button>
                    <span class="ops-sep" />
                    <button class="link-btn danger" @click="deleteDoc(row)">删除</button>
                  </div>
                </template>
              </el-table-column>
            </el-table>
            <div class="kb-summary">
              共 {{ knowledgeDocs.length }} 份 · 已索引 {{ knowledgeDocs.filter(d=>d.status==='已索引').length }} 份 · {{ totalSize }}
            </div>
          </div>

        </template>

        <!-- ── 检索设置 Tab ── -->
        <template v-else-if="kbTab === 'config'">
          <div class="card">
            <div class="card-title"><PhGear weight="duotone" :size="14" />检索配置
              <span v-if="kbConfigDirty" class="status-pill amber ml-auto">未保存</span>
              <span v-else-if="kbConfigured" class="status-pill green ml-auto">已生效（自定义）</span>
              <span v-else class="status-pill ml-auto">系统默认</span>
            </div>
            <div class="form-grid">
              <div class="form-row">
                <label>检索策略</label>
                <el-select v-model="kbConfig.strategy" size="small" style="width:180px" @change="kbConfigDirty=true">
                  <el-option label="混合检索（推荐）" value="hybrid" />
                  <el-option label="仅语义检索" value="semantic" />
                  <el-option label="仅关键词检索" value="keyword" />
                </el-select>
              </div>
              <p class="config-hint">混合检索 = 语义向量 + 关键词 BM25 融合（系统默认，问答准确率在此配置下验收）；单一策略仅建议排查检索问题时临时使用</p>
              <div class="form-row">
                <label>最大召回数</label>
                <el-input-number v-model="kbConfig.topK" :min="1" :max="10" size="small" @change="kbConfigDirty=true" />
              </div>
              <p class="config-hint">送入大模型的知识片段条数：调大提高覆盖但增加延迟与干扰，调小反之</p>
              <div class="form-row">
                <label>置信度阈值</label>
                <el-slider v-model="kbConfig.threshold" :min="0" :max="1" :step="0.05" style="width:160px" @change="kbConfigDirty=true" />
                <span class="threshold-val">{{ kbConfig.threshold.toFixed(2) }}</span>
              </div>
              <p class="config-hint">检索置信度低于阈值时数字人如实说「暂无资料」而不是编造（防幻觉门控；在本地重排部署下生效，云端轻量部署自动忽略）</p>
            </div>
            <div class="edit-actions" style="justify-content:flex-start">
              <button class="primary-btn mt12" :disabled="kbConfigSaving" @click="saveKbConfig">
                {{ kbConfigSaving ? '保存中…' : '保存并生效' }}
              </button>
              <button class="ghost-btn mt12" @click="resetKbConfig">恢复系统默认</button>
            </div>
          </div>
        </template>

        <!-- ── 知识库体检 Tab ── -->
        <template v-else-if="kbTab === 'selftest'">
          <div class="card mb16">
            <div class="card-title"><PhCheckCircle weight="duotone" :size="14" />知识库体检 · 自动出题验证准确率</div>
            <p class="config-hint" style="margin-top:0">
              系统从当前知识库自动抽取含确定性事实（数字/专名）的内容出题，让数字人作答后按关键词命中评分——
              上传或更新知识库后跑一轮，即可验证「数字人学会了没有」。
            </p>
            <div class="edit-actions" style="justify-content:flex-start;align-items:center">
              <label style="display:flex;align-items:center;gap:6px">题量
                <el-select v-model="stSample" size="small" style="width:80px" :disabled="stLoading">
                  <el-option :value="5" label="5 题" /><el-option :value="8" label="8 题" /><el-option :value="10" label="10 题" />
                </el-select>
              </label>
              <button class="primary-btn" :disabled="stLoading" @click="runSelfTest">
                <PhCircleNotch weight="duotone" v-if="stLoading" :size="14" class="spin" />
                <PhSparkle weight="duotone" v-else :size="14" />
                {{ stLoading ? `体检中，已用时 ${stElapsed}s…` : '开始体检' }}
              </button>
              <span v-if="stLoading" class="config-hint" style="margin:0">每题需完整跑一遍检索+生成链路，约 5-10 秒/题，请耐心等待</span>
            </div>
          </div>

          <div v-if="stResult" class="card">
            <div class="card-title">体检报告</div>
            <!-- KPI 概览条 -->
            <div class="st-kpis">
              <div class="st-gauge">
                <div class="st-gauge-ring" :style="{ background: `conic-gradient(${stResult.accuracy>=90?'var(--c-green)':'var(--c-amber)'} ${stResult.accuracy*3.6}deg, var(--c-border) 0)` }">
                  <div class="st-gauge-inner">
                    <span class="st-gauge-val" :style="{ color: stResult.accuracy>=90 ? 'var(--c-green)':'var(--c-amber)' }">{{ stResult.accuracy }}%</span>
                    <span class="st-gauge-lbl">准确率</span>
                  </div>
                </div>
              </div>
              <div class="st-kpi-cells">
                <div class="st-kpi-cell"><b>{{ stResult.passed }}</b><span>通过</span></div>
                <div class="st-kpi-cell"><b :style="{color: stResult.failed ? 'var(--c-red)' : ''}">{{ stResult.failed ?? (stResult.sample - stResult.passed) }}</b><span>未过</span></div>
                <div class="st-kpi-cell"><b>{{ stResult.sample }}</b><span>抽测题</span></div>
                <div class="st-kpi-cell"><b>{{ stResult.total_chunks }}</b><span>知识片段</span></div>
                <div class="st-kpi-cell" v-if="stResult.avg_duration_ms != null"><b>{{ (stResult.avg_duration_ms/1000).toFixed(1) }}s</b><span>单题均耗时</span></div>
              </div>
            </div>
            <!-- 按题型通过率 -->
            <div v-if="stResult.by_type && stResult.by_type.length" class="st-bytype">
              <div v-for="t in stResult.by_type" :key="t.type" class="st-bytype-row">
                <span class="st-bytype-name">{{ t.type }}</span>
                <div class="st-bytype-bar"><div class="st-bytype-fill" :style="{ width: t.accuracy+'%', background: t.accuracy>=90?'var(--c-green)':'var(--c-amber)' }" /></div>
                <span class="st-bytype-val">{{ t.accuracy }}% ({{ t.passed }}/{{ t.total }})</span>
              </div>
            </div>
            <div class="st-items">
              <div v-for="(it, i) in stResult.items" :key="i" class="st-item" :class="{ fail: !it.passed }">
                <div class="st-q">
                  <span class="status-pill" :class="it.passed ? 'green' : 'red'">{{ it.passed ? '通过' : '未过' }}</span>
                  {{ i + 1 }}. {{ it.question }}
                </div>
                <div class="st-meta">
                  <span v-if="it.kw_type" class="st-chip">{{ it.kw_type }}</span>
                  <span v-if="it.source" class="st-chip"><PhFileText weight="duotone" :size="11" />{{ it.source }}</span>
                  <span v-if="it.duration_ms != null" class="st-chip"><PhClock weight="duotone" :size="11" />{{ (it.duration_ms/1000).toFixed(1) }}s</span>
                  <span v-if="it.score != null" class="st-chip">命中 {{ Math.round(it.score*100) }}%</span>
                </div>
                <div class="st-kw">评分关键词：
                  <span v-for="k in it.keywords" :key="k" class="cat-badge" :style="it.hit_keywords.includes(k) ? 'color:var(--c-green);border-color:var(--c-green)' : ''">{{ k }}</span>
                </div>
                <div class="st-a">{{ it.answer }}</div>
              </div>
            </div>
          </div>
          <div v-else-if="!stLoading" class="card empty-state">
            <PhCheckCircle weight="duotone" :size="28" />
            <p>还没有体检记录，点击「开始体检」验证当前知识库</p>
          </div>
        </template>

        <!-- ── FAQ 问答 Tab ── -->
        <template v-else-if="kbTab === 'faq'">
          <!-- 工具栏 -->
          <div class="card mb16">
            <div class="kb-toolbar">
              <div class="cat-tabs">
                <button v-for="c in faqCats" :key="c"
                  :class="['cat-btn', { active: faqCatFilter === c }]"
                  @click="faqCatFilter = c">
                  <span v-if="c !== '全部'" class="cat-dot" :style="{ background: catColor(c) }" />{{ c }}
                </button>
              </div>
              <div class="kb-toolbar-right">
                <div class="search-wrap">
                  <PhMagnifyingGlass weight="duotone" :size="13" class="search-ico" aria-hidden="true" />
                  <input v-model="faqSearchQ" class="search-input" placeholder="搜索问答…" aria-label="搜索问答" />
                </div>
                <button class="primary-btn" @click="startAddFaq">
                  <PhPlus weight="duotone" :size="13" />新增问答
                </button>
              </div>
            </div>
          </div>

          <!-- 新增表单 -->
          <div v-if="faqAdding" class="card mb16 edit-form-card">
            <div class="card-title"><PhPlus weight="duotone" :size="14" />新增问答</div>
            <div class="edit-form">
              <div class="edit-row">
                <label>问题</label>
                <input v-model="faqAddForm.q" class="edit-input" placeholder="输入游客常见问题…" />
              </div>
              <div class="edit-row edit-row-grow">
                <label>答案</label>
                <el-input v-model="faqAddForm.a" type="textarea" :rows="3" placeholder="输入详细答案…" />
              </div>
              <div class="edit-row">
                <label>分类</label>
                <el-select v-model="faqAddForm.cat" size="small" style="width:150px">
                  <el-option v-for="c in faqCats.slice(1)" :key="c" :label="c" :value="c">
                  <span class="cat-opt"><span class="cat-dot" :style="{ background: catColor(c) }" />{{ c }}</span>
                </el-option>
                </el-select>
              </div>
            </div>
            <div class="edit-actions">
              <button class="ghost-btn" @click="faqAdding = false"><PhX weight="duotone" :size="13" />取消</button>
              <button class="primary-btn" @click="saveAddFaq"><PhCheck weight="duotone" :size="13" />保存</button>
            </div>
          </div>

          <!-- FAQ 列表 -->
          <div class="card">
            <div v-if="filteredFaq.length === 0" class="empty-state">
              <PhQuestion weight="duotone" :size="28" />
              <p>暂无问答，点击「新增问答」开始添加</p>
            </div>
            <div v-else class="faq-list">
              <div v-for="(item, idx) in filteredFaq" :key="item.id"
                :class="['faq-item', { editing: faqEditId === item.id, last: idx === filteredFaq.length-1 }]">

                <!-- 查看态 -->
                <template v-if="faqEditId !== item.id">
                  <div class="faq-view">
                    <div class="faq-q"><PhQuestion weight="duotone" :size="12" class="faq-ico" />{{ item.q }}</div>
                    <div class="faq-a">{{ item.a }}</div>
                    <div class="faq-foot">
                      <span class="cat-badge tinted" :style="{ color: catColor(item.cat), borderColor: catColor(item.cat)+'55', background: catColor(item.cat)+'14' }">
                        <span class="cat-dot" :style="{ background: catColor(item.cat) }" />{{ item.cat }}
                      </span>
                      <span class="prio-pill" title="管理员录入的问答，游客相同提问将以最高优先级作答">
                        <PhStar weight="fill" :size="10" />最高优先级
                      </span>
                      <span class="item-date">{{ item.updated }}</span>
                      <div class="item-ops">
                        <button class="link-btn" @click="startEditFaq(item)">编辑</button>
                        <button class="link-btn danger" @click="deleteFaqItem(item)">删除</button>
                      </div>
                    </div>
                  </div>
                </template>

                <!-- 编辑态 -->
                <template v-else>
                  <div class="edit-form">
                    <div class="edit-row">
                      <label>问题</label>
                      <input v-model="faqEditForm.q" class="edit-input" />
                    </div>
                    <div class="edit-row edit-row-grow">
                      <label>答案</label>
                      <el-input v-model="faqEditForm.a" type="textarea" :rows="3" />
                    </div>
                    <div class="edit-row">
                      <label>分类</label>
                      <el-select v-model="faqEditForm.cat" size="small" style="width:150px">
                        <el-option v-for="c in faqCats.slice(1)" :key="c" :label="c" :value="c">
                  <span class="cat-opt"><span class="cat-dot" :style="{ background: catColor(c) }" />{{ c }}</span>
                </el-option>
                      </el-select>
                    </div>
                  </div>
                  <div class="edit-actions">
                    <button class="ghost-btn" @click="faqEditId = null"><PhX weight="duotone" :size="13" />取消</button>
                    <button class="primary-btn" @click="saveEditFaq(item)"><PhCheck weight="duotone" :size="13" />保存</button>
                  </div>
                </template>
              </div>
            </div>
            <div class="kb-summary">共 {{ faqItems.length }} 条问答</div>
          </div>
        </template>

        <!-- ── 文本段落 Tab ── -->
        <template v-else-if="kbTab === 'text'">
          <!-- 工具栏 -->
          <div class="card mb16">
            <div class="kb-toolbar">
              <div class="cat-tabs">
                <button v-for="c in ['全部', ...textCats]" :key="c"
                  :class="['cat-btn', { active: textCatFilter === c }]"
                  @click="textCatFilter = c">
                  <span v-if="c !== '全部'" class="cat-dot" :style="{ background: catColor(c) }" />{{ c }}
                </button>
              </div>
              <div class="kb-toolbar-right">
                <div class="search-wrap">
                  <PhMagnifyingGlass weight="duotone" :size="13" class="search-ico" aria-hidden="true" />
                  <input v-model="textSearchQ" class="search-input" placeholder="搜索段落…" aria-label="搜索段落" />
                </div>
                <button class="primary-btn" @click="startAddText">
                  <PhPlus weight="duotone" :size="13" />新增段落
                </button>
              </div>
            </div>
          </div>

          <!-- 新增表单 -->
          <div v-if="textAdding" class="card mb16 edit-form-card">
            <div class="card-title"><PhPlus weight="duotone" :size="14" />新增文本段落</div>
            <div class="edit-form">
              <div class="edit-row-double">
                <div class="edit-row" style="flex:1">
                  <label>标题</label>
                  <input v-model="textAddForm.title" class="edit-input" placeholder="段落标题…" />
                </div>
                <div class="edit-row">
                  <label>分类</label>
                  <el-select v-model="textAddForm.cat" size="small" style="width:150px">
                    <el-option v-for="c in textCats" :key="c" :label="c" :value="c">
                      <span class="cat-opt"><span class="cat-dot" :style="{ background: catColor(c) }" />{{ c }}</span>
                    </el-option>
                  </el-select>
                </div>
              </div>
              <div class="edit-row edit-row-grow">
                <label>内容</label>
                <div style="flex:1">
                  <el-input v-model="textAddForm.content" type="textarea" :rows="6" placeholder="输入知识内容…" />
                  <div class="char-count">{{ textAddForm.content.length }} 字</div>
                </div>
              </div>
            </div>
            <div class="edit-actions">
              <button class="ghost-btn" @click="textAdding = false"><PhX weight="duotone" :size="13" />取消</button>
              <button class="primary-btn" @click="saveAddText"><PhCheck weight="duotone" :size="13" />保存</button>
            </div>
          </div>

          <!-- 文本列表 -->
          <div v-if="filteredText.length === 0" class="card empty-state">
            <PhPencilLine weight="duotone" :size="28" />
            <p>暂无文本段落，点击「新增段落」开始添加</p>
          </div>
          <div v-else class="text-grid">
            <div v-for="item in filteredText" :key="item.id" class="card text-card">
              <!-- 查看态 -->
              <template v-if="textEditId !== item.id">
                <div class="text-view-header">
                  <span class="text-title">{{ item.title }}</span>
                  <span class="cat-badge tinted" :style="{ color: catColor(item.cat), borderColor: catColor(item.cat)+'55', background: catColor(item.cat)+'14' }">
                    <span class="cat-dot" :style="{ background: catColor(item.cat) }" />{{ item.cat }}
                  </span>
                </div>
                <p class="text-preview">{{ item.content }}</p>
                <div class="faq-foot">
                  <span class="item-date">{{ item.updated }}</span>
                  <span class="char-hint">{{ item.content.length }} 字</span>
                  <div class="item-ops">
                    <button class="link-btn" @click="startEditText(item)">编辑</button>
                    <button class="link-btn danger" @click="deleteTextItem(item)">删除</button>
                  </div>
                </div>
              </template>

              <!-- 编辑态 -->
              <template v-else>
                <div class="edit-form">
                  <div class="edit-row-double">
                    <div class="edit-row" style="flex:1">
                      <label>标题</label>
                      <input v-model="textEditForm.title" class="edit-input" />
                    </div>
                    <div class="edit-row">
                      <label>分类</label>
                      <el-select v-model="textEditForm.cat" size="small" style="width:150px">
                        <el-option v-for="c in textCats" :key="c" :label="c" :value="c">
                      <span class="cat-opt"><span class="cat-dot" :style="{ background: catColor(c) }" />{{ c }}</span>
                    </el-option>
                      </el-select>
                    </div>
                  </div>
                  <div class="edit-row edit-row-grow">
                    <label>内容</label>
                    <div style="flex:1">
                      <el-input v-model="textEditForm.content" type="textarea" :rows="6" />
                      <div class="char-count">{{ textEditForm.content.length }} 字</div>
                    </div>
                  </div>
                </div>
                <div class="edit-actions">
                  <button class="ghost-btn" @click="textEditId = null"><PhX weight="duotone" :size="13" />取消</button>
                  <button class="primary-btn" @click="saveEditText(item)"><PhCheck weight="duotone" :size="13" />保存</button>
                </div>
              </template>
            </div>
          </div>
        </template>
      </div>

      <!-- ═══ 数据大屏 = 全屏显示模式：进入即全屏（Teleport + Fullscreen API），退出回上一页面 ═══ -->
      <Teleport to="body" :disabled="!dashFull">
      <div v-show="activeTab === 'dashboard'" class="tab-dashboard-screen">

        <!-- 顶部标题栏 -->
        <header class="dsh-hd">
          <div class="dsh-hd-l">
            <span class="dsh-scenic">{{ sceneStore.scenicName || '景区智能服务' }}</span>
            <div class="dsh-ranges">
              <button v-for="r in ranges" :key="r.val"
                :class="['dsh-rb', { active: dashRange === r.val }]"
                @click="dashRange=r.val; refreshDashboard()">{{ r.label }}</button>
            </div>
          </div>
          <div class="dsh-hd-c">
            <span class="dsh-deco-line"></span>
            景区智能服务数据大屏
            <span class="dsh-deco-line dsh-deco-r"></span>
          </div>
          <div class="dsh-hd-r">
            <span class="dsh-hdate">{{ dashDate }}</span>
            <span class="dsh-htime">{{ dashClock }}</span>
            <button class="dsh-hbtn" @click="toggleDanmaku" :title="danmakuOn ? '关闭弹幕' : '开启弹幕'">
              <component :is="danmakuOn ? IconMessages : IconMessageOff" :size="12" />
            </button>
            <button class="dsh-hbtn" @click="refreshDashboard" :disabled="dashLoading" title="刷新">
              <PhArrowsCounterClockwise weight="duotone" :size="12" :class="{ spin: dashLoading }" />
            </button>
            <button class="dsh-hbtn dsh-exit" @click="exitDashboard" title="退出大屏（Esc）">
              <PhX weight="duotone" :size="12" />
              <span class="dsh-exit-txt">退出大屏</span>
            </button>
          </div>
        </header>

        <!-- 实时弹幕带「游客正在问」：3 轨暗玻璃胶囊，横贯全屏（头部正下方） -->
        <DanmakuFlow v-if="danmakuOn" :key="'dsh-' + sceneStore.scenicId + '-' + dmkLanes"
          :scenic-id="sceneStore.scenicId || 'lingshan'" :lanes="dmkLanes" variant="dark" :speed="92" class="dsh-dmk" />

        <!-- 错误提示 -->
        <div v-if="dashError" class="dsh-error-bar">
          <PhWarningCircle weight="duotone" :size="13" />&nbsp;数据加载失败，请检查网络连接
          <button @click="dashError=false; loadDashboard()">重试</button>
        </div>

        <!-- 主体布局 -->
        <div class="dsh-body" :key="chartAnimKey">

          <!-- 左列 -->
          <div class="dsh-col">
            <!-- KPI -->
            <div class="dsh-panel">
              <div class="dsh-phd">核心指标</div>
              <div class="dsh-kpi-grid">
                <div class="dsh-kpi" v-for="k in kpiList" :key="k.label">
                  <div class="dsh-kpi-ico" :style="{ color: k.color }">
                    <component :is="k.icon" :size="18" />
                  </div>
                  <div class="dsh-kpi-body">
                    <div class="dsh-kpi-val" :style="{ color: k.color }">{{ k.value }}</div>
                    <div class="dsh-kpi-lbl">{{ k.label }}</div>
                  </div>
                </div>
              </div>
            </div>
            <!-- 功能使用率 -->
            <div class="dsh-panel dsh-pf f-lg">
              <div class="dsh-phd">功能使用率
                <span class="dsh-pmeta">活跃会话 {{ featureData.active_sessions ?? '--' }}</span>
              </div>
              <div ref="ecFeatures" class="dsh-ec dsh-ec-sm"></div>
            </div>
            <!-- 客群画像 -->
            <div class="dsh-panel dsh-pf f-xl">
              <div class="dsh-phd">客群画像</div>
              <div ref="ecProfile" class="dsh-ec dsh-ec-sm"></div>
            </div>
          </div>

          <!-- 中列 -->
          <div class="dsh-col dsh-col-c">
            <!-- 趋势主图 -->
            <div class="dsh-panel dsh-pm">
              <div class="dsh-phd">近7日交互趋势
                <span v-if="trendBackfilled" class="dsh-pmeta">冷启动 · 空档日按周节律推演补全（空心点）</span>
              </div>
              <div ref="ecLine" class="dsh-ec dsh-ec-main"></div>
            </div>
            <!-- 情感 + 满意度 -->
            <div class="dsh-r2">
              <div class="dsh-panel dsh-pf">
                <div class="dsh-phd">情感分布</div>
                <div ref="ecDonut" class="dsh-ec dsh-ec-md"></div>
              </div>
              <div class="dsh-panel dsh-pf">
                <div class="dsh-phd">游客满意度
                  <span class="dsh-sat-n">{{ avgSatisfaction || '--' }}<small v-if="avgSatisfaction"> /5</small></span>
                </div>
                <div ref="ecSat" class="dsh-ec dsh-ec-md"></div>
              </div>
            </div>
          </div>

          <!-- 右列 -->
          <div class="dsh-col">
            <div class="dsh-panel dsh-pf f-lg">
              <div class="dsh-phd">热门话题 Top 5</div>
              <div ref="ecTopics" class="dsh-ec dsh-ec-lg"></div>
            </div>
            <div class="dsh-panel dsh-pf">
              <div class="dsh-phd">实时客流压力
                <span class="dsh-pmeta" v-if="crowdMeta">{{ crowdMeta }}</span>
              </div>
              <div ref="ecSpots" class="dsh-ec dsh-ec-lg"></div>
            </div>
            <div class="dsh-panel dsh-pf f-xs">
              <div class="dsh-phd">时段热度<span class="dsh-pmeta">今日 · 推演</span></div>
              <div ref="ecHours" class="dsh-ec dsh-ec-sm"></div>
            </div>
          </div>

        </div>

        <!-- 底部决策数据带（xlsx 行为数据，本景区口径：收入结构 / 客群结构 / 同行规模） -->
        <div class="dsh-strip">
          <div class="dsh-panel dsh-pf">
            <div class="dsh-phd">消费结构
              <span class="dsh-pmeta" v-if="spendAvg">客单价 ¥{{ spendAvg }}</span>
            </div>
            <div ref="ecSpend" class="dsh-ec dsh-ec-sm"></div>
          </div>
          <div class="dsh-panel dsh-pf">
            <div class="dsh-phd">客群年龄结构
              <span class="dsh-pmeta" v-if="genderMeta">{{ genderMeta }}</span>
            </div>
            <div ref="ecAge" class="dsh-ec dsh-ec-sm"></div>
          </div>
          <div class="dsh-panel dsh-pf">
            <div class="dsh-phd">同行规模分布
              <span class="dsh-pmeta" v-if="groupMeta">{{ groupMeta }}</span>
            </div>
            <div ref="ecGroup" class="dsh-ec dsh-ec-sm"></div>
          </div>
          <div class="dsh-panel dsh-pf">
            <div class="dsh-phd">客单价分层 · 营收贡献
              <span class="dsh-pmeta" v-if="tiersMeta">{{ tiersMeta }}</span>
            </div>
            <div ref="ecTiers" class="dsh-ec dsh-ec-sm"></div>
          </div>
        </div>
      </div>
      </Teleport>

      <!-- 文件上传弹窗（F1）：选择文件 → 开始上传 -->
      <el-dialog v-model="uploadDialogVisible" title="上传知识库文档" width="520px" :close-on-click-modal="!uploadingKb">
        <p class="config-hint" style="margin-top:0">选择一个或多个文档加入本景区知识库；上传后自动分块向量化，游客问答立即可用。</p>
        <el-upload class="uploader-dialog" drag multiple :auto-upload="false"
          v-model:file-list="uploadFileList" :before-upload="beforeUpload"
          accept=".txt,.pdf,.docx,.md" :on-exceed="onUploadExceedHint">
          <div class="upload-zone">
            <PhCloudArrowUp weight="duotone" :size="30" class="upload-ico" />
            <p class="upload-main">拖拽文件到此，或<em>点击选择文件</em></p>
            <p class="upload-hint">支持 .txt / .pdf / .docx / .md，单文件 ≤ 20MB</p>
          </div>
        </el-upload>
        <label class="kb-replace-row">
          <el-switch v-model="kbReplace" size="small" :disabled="uploadingKb" />
          <span>整库替换模式：上传前清空本景区旧知识库（换季更新/整套换库时使用，请谨慎开启）</span>
        </label>
        <template #footer>
          <button class="ghost-btn" @click="uploadDialogVisible = false" :disabled="uploadingKb">取消</button>
          <button class="primary-btn" @click="startKbUpload" :disabled="uploadingKb || !uploadFileList.length">
            <PhCloudArrowUp weight="duotone" :size="13" /> {{ uploadingKb ? '上传中…' : `开始上传${uploadFileList.length ? ' ('+uploadFileList.length+')' : ''}` }}
          </button>
        </template>
      </el-dialog>

      <!-- ═══ 应急广播（F5：侧栏·日常运营）═══ -->
      <div v-show="activeTab === 'broadcast'" class="tab-content">
        <div class="page-header">
          <h2>应急广播</h2>
          <span class="page-sub">让现场数字人立即语音播报公告，并可同步在大屏推送上屏字幕横幅</span>
        </div>

        <!-- 状态条：目标屏在线 + 当前播报 + 会话统计（轮询真信号） -->
        <div class="bc-status-strip">
          <div class="bc-stat">
            <span class="bc-stat-ico" :class="bcLive.portrait ? 'on' : 'off'"><PhMonitorPlay weight="duotone" :size="19" /></span>
            <div class="bc-stat-body">
              <span class="bc-stat-label">景区立屏</span>
              <span class="bc-stat-val" :class="bcLive.portrait ? 'on' : 'off'"><i class="bc-stat-dot" />{{ bcLive.portrait ? '在线' : '未连接' }}</span>
            </div>
          </div>
          <div class="bc-stat">
            <span class="bc-stat-ico" :class="bcLive.main ? 'on' : 'off'"><PhUserCircle weight="duotone" :size="19" /></span>
            <div class="bc-stat-body">
              <span class="bc-stat-label">游客手机端</span>
              <span class="bc-stat-val" :class="bcLive.main ? 'on' : 'off'"><i class="bc-stat-dot" />{{ bcLive.main ? '在线' : '未连接' }}</span>
            </div>
          </div>
          <div class="bc-stat wide">
            <span class="bc-stat-ico" :class="{ live: bcNow.speaking }">
              <PhWaveform v-if="bcNow.speaking" weight="duotone" :size="19" />
              <PhSpeakerHigh v-else weight="duotone" :size="19" />
            </span>
            <div class="bc-stat-body">
              <span class="bc-stat-label">当前播报</span>
              <span class="bc-stat-now" :class="{ speaking: bcNow.speaking }">{{ bcNow.speaking ? bcNow.text : '空闲中' }}</span>
            </div>
          </div>
          <div class="bc-stat">
            <span class="bc-stat-ico"><PhBroadcast weight="duotone" :size="19" /></span>
            <div class="bc-stat-body">
              <span class="bc-stat-label">本次会话广播</span>
              <span class="bc-stat-val"><b>{{ bcHistory.length }}</b> 条</span>
            </div>
          </div>
        </div>

        <div class="bc-layout">
          <!-- 左：编辑区 -->
          <div class="card bc-compose">
            <div class="card-title"><PhBroadcast weight="duotone" :size="14" />广播内容</div>

            <!-- 广播级别 -->
            <div class="bc-field-label">广播级别</div>
            <div class="bc-levels">
              <button v-for="lv in bcLevels" :key="lv.key" class="bc-level" :class="[lv.key, { active: bcLevel === lv.key }]" @click="applyBcLevel(lv)">
                <component :is="lv.icon" weight="duotone" :size="16" /><span>{{ lv.label }}</span>
              </button>
            </div>

            <!-- 模板（按类别彩点分组） -->
            <div class="bc-field-label">应急模板</div>
            <div class="bc-tpl-groups">
              <div v-for="g in bcTemplateGroups" :key="g.label" class="bc-tpl-group">
                <span class="bc-tpl-gl"><i class="cat-dot" :style="{ background: g.color }" />{{ g.label }}</span>
                <div class="bc-templates">
                  <button v-for="t in g.items" :key="t.label" class="bc-tpl-btn" @click="applyBcTemplate(t)">
                    <component :is="t.icon" weight="duotone" :size="14" /><span>{{ t.label }}</span>
                  </button>
                </div>
              </div>
            </div>

            <div class="bc-field-label">广播文案</div>
            <el-input v-model="bcText" type="textarea" :rows="4" maxlength="140" show-word-limit
              placeholder="输入广播内容，或点击上方模板快速填充…" />
            <div class="bc-est"><PhClock weight="duotone" :size="13" />预计播报约 <b>{{ bcEstSec }}</b> 秒 · {{ bcText.trim().length }} 字</div>

            <div class="bc-row">
              <span class="bc-row-label">播报屏幕</span>
              <el-checkbox v-model="bcToPortrait" :disabled="bcSending">景区立屏（竖屏）</el-checkbox>
              <el-checkbox v-model="bcToMain" :disabled="bcSending">游客手机端（横屏）</el-checkbox>
            </div>
            <div class="bc-row">
              <span class="bc-row-label">播报语气</span>
              <el-radio-group v-model="bcEmotion" size="small">
                <el-radio-button value="concerned">关切</el-radio-button>
                <el-radio-button value="neutral">平静</el-radio-button>
                <el-radio-button value="happy">愉悦</el-radio-button>
              </el-radio-group>
            </div>
            <div class="bc-row">
              <span class="bc-row-label">上屏字幕</span>
              <el-switch v-model="bcSubtitle" />
              <template v-if="bcSubtitle">
                <el-radio-group v-model="bcStyle" size="small" style="margin-left:6px">
                  <el-radio-button value="alert">警示（红）</el-radio-button>
                  <el-radio-button value="info">通知（蓝）</el-radio-button>
                </el-radio-group>
                <span class="bc-dur">停留
                  <el-input-number v-model="bcDuration" :min="5" :max="120" :step="5" size="small" controls-position="right" style="width:96px" />
                  秒
                </span>
              </template>
            </div>
            <div class="bc-row">
              <span class="bc-row-label">定时循环</span>
              <el-switch v-model="bcRepeat" :disabled="bcSending" />
              <template v-if="bcRepeat">
                <span class="bc-dur">每
                  <el-input-number v-model="bcRepeatMin" :min="1" :max="60" :step="1" size="small" controls-position="right" style="width:88px" />
                  分钟重播
                </span>
                <span v-if="bcRepeatOn" class="bc-repeat-live"><PhTimer weight="duotone" :size="13" />下次 {{ bcRepeatLeft }}s</span>
              </template>
            </div>
            <p v-if="bcRepeat" class="config-hint">循环播报仅在本页开启期间生效；离开或关闭页面即自动停止。</p>

            <div class="edit-actions" style="justify-content:flex-start">
              <button class="primary-btn lg" @click="sendBroadcast" :disabled="bcSending || !bcText.trim()">
                <PhBroadcast weight="duotone" :size="15" /> {{ bcSending ? '播报中…' : '立即播报' }}
              </button>
              <button v-if="bcRepeatOn" class="ghost-btn danger" @click="stopRepeat"><PhStopCircle weight="duotone" :size="14" />停止循环</button>
              <button class="ghost-btn" @click="clearSubtitle" title="撤下当前大屏字幕">撤下字幕</button>
            </div>
          </div>

          <!-- 右：现场预览 + 历史 -->
          <div class="bc-side">
            <div class="card">
              <div class="card-title">
                <PhEye weight="duotone" :size="14" />现场预览
                <div class="bc-prev-switch">
                  <button :class="{ active: bcPreviewScreen === 'portrait' }" @click="switchPreview('portrait')">立屏</button>
                  <button :class="{ active: bcPreviewScreen === 'main' }" @click="switchPreview('main')">手机端</button>
                </div>
              </div>
              <div class="bc-preview-stage" :class="bcPreviewScreen">
                <video ref="bcPreviewVideoEl" class="bc-preview-video" muted autoplay playsinline />
                <div v-show="!bcPreviewReady" class="bc-preview-ph">
                  <PhMonitorPlay weight="duotone" :size="34" /><span>正在连接现场直播…</span>
                </div>
                <span v-if="bcPreviewReady" class="bc-live-badge"><i />LIVE</span>
                <span v-if="bcNow.speaking" class="bc-speaking-badge"><PhWaveform weight="duotone" :size="12" />播报中</span>
                <div v-if="bcSubtitle && bcText.trim()" class="bc-preview-sub" :class="bcStyle">{{ bcText }}</div>
              </div>
              <p class="config-hint" style="margin:8px 0 0">现场预览为只读监看，不影响游客端讲解流畅性；播报会打断当前讲解，字幕约 {{ bcDuration }} 秒后自动撤下。</p>
            </div>
            <div class="card">
              <div class="card-title"><PhClock weight="duotone" :size="14" />本次会话已发</div>
              <div v-if="!bcHistory.length" class="empty-state sm"><p>暂无广播记录</p></div>
              <div v-else class="bc-history">
                <div v-for="(h, i) in bcHistory" :key="i" class="bc-hist-item">
                  <span class="bc-hist-dot" :class="h.ok ? 'ok' : 'fail'" />
                  <div class="bc-hist-body">
                    <p class="bc-hist-text">{{ h.text }}</p>
                    <p class="bc-hist-meta">
                      <span class="bc-hist-lv" :class="h.level">{{ bcLevelLabel(h.level) }}</span>
                      {{ h.time }} · {{ h.screens.map(s => s==='portrait'?'立屏':'手机').join('/') }}<template v-if="h.subtitle"> · 含字幕</template>
                    </p>
                  </div>
                  <button class="bc-hist-resend" @click="resendBroadcast(h)" title="重新播报"><PhArrowClockwise weight="duotone" :size="14" /></button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
      <!-- ═══ 感受度报告 ═══ -->
      <div v-show="activeTab === 'report'" class="tab-content">
        <div class="page-header">
          <h2>感受度报告</h2>
          <div class="header-actions">
            <button class="ghost-btn sm" @click="refreshReport" :disabled="reportLoading">
              <IconRefresh :size="13" :class="{ spin: reportLoading }" />刷新
            </button>
          </div>
        </div>

        <!-- loading 遮罩 -->
        <div v-if="reportLoading" class="report-loading">
          <IconLoader2 :size="22" class="spin" />
          <span>数据加载中…</span>
        </div>
        <div v-else-if="reportError" class="dash-error-banner">
          <IconAlertCircle :size="14" />
          数据加载失败，请检查网络连接或后端服务
          <button class="ghost-btn sm" style="margin-left:auto" @click="reportError=false; loadReport()">重试</button>
        </div>
        <template v-else>

        <!-- KPI 摘要条：图标方块 + 标签 + 大数字（参考主流 BI 首页范式） -->
        <div class="rpt-kpi-card">
          <div class="rpt-kpi">
            <span class="rpt-kpi-ico k0"><IconMoodSmile :size="22" :stroke-width="1.7" /></span>
            <div class="rpt-kpi-body">
              <span class="rpt-kpi-label">正面情感占比</span>
              <span class="rpt-kpi-num">{{ rptKpi.pos }}<i class="rpt-unit">%</i></span>
            </div>
          </div>
          <i class="rpt-kpi-div" />
          <div class="rpt-kpi">
            <span class="rpt-kpi-ico k1"><IconMessages :size="22" :stroke-width="1.7" /></span>
            <div class="rpt-kpi-body">
              <span class="rpt-kpi-label">近7日互动总量</span>
              <span class="rpt-kpi-num">{{ rptKpi.total }}<i class="rpt-unit">条</i></span>
            </div>
          </div>
          <i class="rpt-kpi-div" />
          <div class="rpt-kpi">
            <span class="rpt-kpi-ico k2"><IconStar :size="22" :stroke-width="1.7" /></span>
            <div class="rpt-kpi-body">
              <span class="rpt-kpi-label">平均满意度</span>
              <span class="rpt-kpi-num">{{ rptKpi.sat }}<i class="rpt-unit">分</i></span>
            </div>
          </div>
          <i class="rpt-kpi-div" />
          <div class="rpt-kpi">
            <span class="rpt-kpi-ico k3"><IconListDetails :size="22" :stroke-width="1.7" /></span>
            <div class="rpt-kpi-body">
              <span class="rpt-kpi-label">待补知识点</span>
              <span class="rpt-kpi-num">{{ rptKpi.gaps }}<i class="rpt-unit">个</i></span>
            </div>
          </div>
        </div>

        <!-- 主图：近7日情感趋势（平滑面积图） -->
        <div class="card mt16">
          <div class="rpt-card-hd">
            <span class="rpt-card-title">近7日情感趋势</span>
            <span class="rpt-hd-legend"><i class="rpt-dot pos" />积极占比<i class="rpt-dot neg" />消极占比<i class="rpt-dot vol" />互动量</span>
          </div>
          <div ref="rptTrendEl" class="rpt-ec-main"></div>
        </div>

        <div class="two-col mt16">
          <!-- 游客关注点（表格） -->
          <div class="card">
            <div class="rpt-card-hd">
              <span class="rpt-card-title">游客关注点</span>
              <span class="rpt-hd-sub">近30日 · 按提问量</span>
            </div>
            <table v-if="topicRows.length" class="rpt-table">
              <thead><tr><th style="width:44px">排名</th><th>话题</th><th style="width:60px">提问量</th><th style="width:104px">热度</th></tr></thead>
              <tbody>
                <tr v-for="(t,i) in topicRows" :key="t.name">
                  <td><span class="rpt-rank" :class="{ top: i < 3 }">{{ i+1 }}</span></td>
                  <td class="rpt-td-name">{{ t.name }}</td>
                  <td class="rpt-td-num">{{ t.count }}</td>
                  <td><div class="rpt-track"><div class="rpt-fill" :style="{ width: t.pct+'%' }" /></div></td>
                </tr>
              </tbody>
            </table>
            <div v-else class="empty-state"><IconListSearch :size="24" /><p>暂无话题数据</p></div>
          </div>

          <!-- 情感构成（环图） -->
          <div class="card">
            <div class="rpt-card-hd"><span class="rpt-card-title">情感构成</span></div>
            <div ref="rptEmoEl" class="rpt-ec-donut"></div>
          </div>
        </div>

        <!-- 待改进项：来自真实未解答提问，直连知识库补充 -->
        <div class="card mt16">
          <div class="rpt-card-hd">
            <span class="rpt-card-title">待改进项</span>
            <span class="rpt-hd-sub">未有效解答的真实提问</span>
          </div>
          <table v-if="gapRows.length" class="rpt-table">
            <thead><tr><th>游客提问</th><th style="width:76px">被问次数</th><th style="width:88px">操作</th></tr></thead>
            <tbody>
              <tr v-for="(g,i) in gapRows" :key="i">
                <td class="rpt-td-name">{{ g.question }}</td>
                <td class="rpt-td-num">{{ g.frequency }}</td>
                <td><button class="rpt-link" @click="activeTab='knowledge'">去补充</button></td>
              </tr>
            </tbody>
          </table>
          <div v-else class="empty-state"><IconClipboardCheck :size="24" /><p>近期提问均得到有效解答，暂无待补盲区</p></div>
        </div>

        <!-- 文字报告（后端基于近7日真实交互记录生成） -->
        <div class="card mt16">
          <div class="rpt-card-hd">
            <span class="rpt-card-title">本周文字报告</span>
            <span v-if="aiReportAt" class="rpt-hd-sub">生成于 {{ aiReportAt }}</span>
            <button class="primary-btn sm rpt-hd-btn" @click="genAiReport" :disabled="aiReportLoading">
              <IconLoader2 v-if="aiReportLoading" :size="12" class="spin" />
              <IconFileAnalytics v-else :size="12" />
              {{ aiReportLoading ? '生成中…' : (aiReportText ? '重新生成' : '生成报告') }}
            </button>
          </div>
          <div v-if="aiReportLoading" class="report-loading" style="padding:18px 0">
            <IconLoader2 :size="18" class="spin" />
            <span>正在分析近7日交互记录…</span>
          </div>
          <div v-else-if="aiReportText" class="rpt-doc" v-html="renderedReport"></div>
          <div v-else class="empty-state"><IconFileText :size="24" /><p>点击「生成报告」，基于近7日真实对话生成运营文字报告</p></div>
        </div>

        <!-- 对话摘录 -->
        <div class="card mt16">
          <div class="rpt-card-hd"><span class="rpt-card-title">典型对话摘录</span></div>
          <div v-if="dialogueSamples.length" class="dialogue-list">
            <div v-for="(d,i) in dialogueSamples" :key="i" class="dialogue-item">
              <div class="dlg-meta">
                <span class="dlg-time">{{ d.time }}</span>
                <span class="sentiment-tag" :class="d.sentiment">
                  {{ { positive:'积极', negative:'消极', neutral:'中性' }[d.sentiment] }}
                </span>
              </div>
              <div class="dlg-q">{{ d.question }}</div>
              <div class="dlg-a">{{ d.answer }}</div>
            </div>
          </div>
          <div v-else class="empty-state">
            <IconMessage2 :size="24" />
            <p>暂无对话记录</p>
          </div>
        </div>
        </template>
      </div>

      <!-- ═══ 消费分析（经营分析·营销决策；数据源=赛题《景点景区旅游数据行为分析数据》真实样本）═══ -->
      <div v-show="activeTab === 'consumption'" class="tab-content">
        <div class="page-header">
          <h2>消费分析</h2>
          <div class="header-actions">
            <span class="cons-src-badge" v-if="consSource">
              <PhFileText weight="duotone" :size="12" />数据来源：{{ consSource }}
            </span>
            <button class="ghost-btn sm" @click="refreshConsumption" :disabled="consLoading">
              <IconRefresh :size="13" :class="{ spin: consLoading }" />刷新
            </button>
          </div>
        </div>

        <div v-if="consLoading" class="report-loading">
          <IconLoader2 :size="22" class="spin" /><span>消费数据加载中…</span>
        </div>
        <div v-else-if="consError" class="dash-error-banner">
          <IconAlertCircle :size="14" />消费数据加载失败，请检查网络连接或后端服务
          <button class="ghost-btn sm" style="margin-left:auto" @click="consError=false; loadConsumption()">重试</button>
        </div>
        <template v-else>

        <!-- KPI 摘要条 -->
        <div class="rpt-kpi-card">
          <div class="rpt-kpi">
            <span class="rpt-kpi-ico k0"><PhCurrencyCny :size="22" weight="duotone" /></span>
            <div class="rpt-kpi-body">
              <span class="rpt-kpi-label">客单价</span>
              <span class="rpt-kpi-num"><i class="rpt-unit">¥</i>{{ consKpi.arpu }}</span>
            </div>
          </div>
          <i class="rpt-kpi-div" />
          <div class="rpt-kpi">
            <span class="rpt-kpi-ico k1"><PhCoins :size="22" weight="duotone" /></span>
            <div class="rpt-kpi-body">
              <span class="rpt-kpi-label">样本总营收</span>
              <span class="rpt-kpi-num"><i class="rpt-unit">¥</i>{{ consKpi.revenue }}</span>
            </div>
          </div>
          <i class="rpt-kpi-div" />
          <div class="rpt-kpi">
            <span class="rpt-kpi-ico k2"><PhCrown :size="22" weight="duotone" /></span>
            <div class="rpt-kpi-body">
              <span class="rpt-kpi-label">高价值客群营收占比</span>
              <span class="rpt-kpi-num">{{ consKpi.hiShare }}<i class="rpt-unit">%</i></span>
            </div>
          </div>
          <i class="rpt-kpi-div" />
          <div class="rpt-kpi">
            <span class="rpt-kpi-ico k3"><PhUsersThree :size="22" weight="duotone" /></span>
            <div class="rpt-kpi-body">
              <span class="rpt-kpi-label">真实样本量</span>
              <span class="rpt-kpi-num">{{ consKpi.sample }}<i class="rpt-unit">条</i></span>
            </div>
          </div>
        </div>

        <!-- 主图：消费与客流趋势 -->
        <div class="card mt16">
          <div class="rpt-card-hd">
            <span class="rpt-card-title">消费与客流趋势</span>
            <span class="rpt-hd-legend"><i class="rpt-dot pos" />客单价<i class="rpt-dot vol" />客流量</span>
          </div>
          <div ref="consTrendEl" class="rpt-ec-main"></div>
        </div>

        <div class="two-col mt16">
          <div class="card">
            <div class="rpt-card-hd">
              <span class="rpt-card-title">消费结构</span>
              <span class="rpt-hd-sub">人均各项支出占比</span>
            </div>
            <div ref="consStructEl" class="rpt-ec-donut"></div>
          </div>
          <div class="card">
            <div class="rpt-card-hd">
              <span class="rpt-card-title">客单价分层与营收贡献</span>
              <span class="rpt-hd-sub">人数占比 vs 营收占比</span>
            </div>
            <div ref="consTiersEl" class="rpt-ec-donut"></div>
          </div>
        </div>

        <div class="two-col mt16">
          <div class="card">
            <div class="rpt-card-hd">
              <span class="rpt-card-title">消费驱动因子</span>
              <span class="rpt-hd-sub">停留时长 / 同行规模 × 客单价</span>
            </div>
            <div ref="consDriversEl" class="rpt-ec-donut"></div>
          </div>
          <div class="card">
            <div class="rpt-card-hd">
              <span class="rpt-card-title">满意度 × 消费四象限</span>
              <span class="rpt-hd-sub">定位「高消费·低满意」营收风险区</span>
            </div>
            <div ref="consQuadEl" class="rpt-ec-donut"></div>
          </div>
        </div>

        <!-- 营销决策建议 -->
        <div class="card mt16">
          <div class="rpt-card-hd">
            <span class="rpt-card-title">营销决策建议</span>
            <span class="rpt-hd-sub">基于真实消费数据 · 洞察 → 建议 → 预期</span>
          </div>
          <div v-if="consAdvice.length" class="cons-advice-list">
            <div v-for="(a,i) in consAdvice" :key="i" class="cons-advice">
              <span class="cons-adv-idx"><PhLightbulb weight="duotone" :size="15" /></span>
              <div class="cons-adv-body">
                <div class="cons-adv-insight">{{ a.insight }}</div>
                <div class="cons-adv-row"><span class="cons-adv-tag act">建议</span><span>{{ a.action }}</span></div>
                <div class="cons-adv-row"><span class="cons-adv-tag exp">预期</span><span>{{ a.expected }}</span></div>
              </div>
              <button class="cons-adv-do" @click="adoptAdvice(a)" title="采纳建议（复制到运营计划）">
                <PhCheck weight="bold" :size="13" />采纳
              </button>
            </div>
          </div>
          <div v-else class="empty-state"><PhLightbulb :size="24" /><p>暂无可生成的营销建议</p></div>
        </div>

        </template>
      </div>

    </main>

    <!-- ── AI 分析助手面板 ── -->
    <aside class="ai-panel" :class="{ collapsed: !aiPanelOpen }">
      <div class="ai-panel-header">
        <button class="ai-toggle-btn" @click="aiPanelOpen = !aiPanelOpen" :title="aiPanelOpen ? '收起助手' : '展开助手'">
          <PhCaretRight weight="duotone" :size="13" :class="{ flipped: !aiPanelOpen }" />
        </button>
        <PhSparkle weight="duotone" :size="13" class="ai-header-ico" aria-hidden="true" />
        <span class="ai-header-title">运营智能代理</span>
        <span class="ai-online-dot" aria-hidden="true" />
      </div>

      <div class="ai-messages" ref="aiChatEl">
        <div v-if="aiMessages.length === 0" class="ai-welcome">
          <div class="ai-bot-icon"><PhRobot weight="duotone" :size="22" aria-hidden="true" /></div>
          <p class="ai-welcome-title">景区运营智能代理</p>
          <p class="ai-welcome-sub">实时调取运营数据，解读趋势并主动建议可执行动作（起草广播 / 补充 FAQ）</p>
          <div class="ai-quick-list">
            <button v-for="q in aiQuickQuestions" :key="q" class="ai-quick-chip" @click="sendQuickQuestion(q)">{{ q }}</button>
          </div>
        </div>

        <template v-else>
          <div v-for="msg in aiMessages" :key="msg.id" :class="['ai-msg-row', msg.role]">
            <div v-if="msg.role === 'assistant'" class="ai-msg-icon">
              <PhRobot weight="duotone" :size="12" />
            </div>
            <div class="ai-msg-col">
              <div :class="['ai-bubble', msg.role, { error: msg.error }]">
                <span v-if="msg.loading && msg.status" class="ai-tool-status">
                  <PhCircleNotch weight="bold" :size="12" class="spin" />{{ msg.status }}
                </span>
                <span v-else-if="msg.loading" class="ai-typing-dots"><i /><i /><i /></span>
                <div v-else-if="msg.role === 'assistant' && !msg.error" class="ai-md" v-html="mdToHtml(msg.content)" />
                <span v-else>{{ msg.content }}</span>
              </div>
              <!-- 建议动作卡（F6）：确认后才执行 -->
              <div v-if="msg.actions && msg.actions.length" class="ai-actions">
                <div v-for="(act, ai) in msg.actions" :key="ai" class="ai-action-card">
                  <template v-if="act.type === 'broadcast'">
                    <div class="ai-action-hd"><PhBroadcast weight="duotone" :size="14" />建议应急广播</div>
                    <p class="ai-action-body">{{ act.text }}</p>
                    <button class="ai-action-btn" :disabled="act.done" @click="goBroadcastWith(act)">
                      <PhBroadcast weight="duotone" :size="12" />{{ act.done ? '已填入广播页' : '去播报' }}
                    </button>
                  </template>
                  <template v-else-if="act.type === 'add_faq'">
                    <div class="ai-action-hd"><PhQuestion weight="duotone" :size="14" />建议新增 FAQ（{{ act.items.length }}）</div>
                    <div v-for="(it, ii) in act.items" :key="ii" class="ai-faq-sug">
                      <div class="ai-faq-q">Q：{{ it.question }}</div>
                      <div class="ai-faq-a">A：{{ it.answer }}</div>
                      <button class="ai-action-btn sm" :disabled="it._added" @click="confirmAddFaqAction(act, it, ii)">
                        <PhPlus weight="duotone" :size="11" />{{ it._added ? '已加入' : '加入知识库' }}
                      </button>
                    </div>
                  </template>
                </div>
              </div>
            </div>
          </div>
        </template>
      </div>

      <div class="ai-input-wrap">
        <textarea
          v-model="aiInput"
          ref="aiTextareaEl"
          class="ai-input"
          placeholder="向AI助手提问…"
          aria-label="向AI助手提问"
          rows="1"
          :disabled="aiLoading"
          @keydown.enter.exact.prevent="sendAiMessage"
          @input="autoResizeTextarea"
        />
        <button
          class="ai-send"
          :class="{ active: aiInput.trim() && !aiLoading }"
          :disabled="!aiInput.trim() || aiLoading"
          aria-label="发送"
          @click="sendAiMessage"
        >
          <PhPaperPlaneRight weight="duotone" :size="13" aria-hidden="true" />
        </button>
      </div>
    </aside>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted, nextTick, watch } from 'vue'
import * as echarts from 'echarts'
import { useSceneStore } from '@/stores/scene'
import { useAuthStore } from '@/stores/auth'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import axios from 'axios'
import PhBroadcast from '@phosphor-icons/vue/dist/icons/PhBroadcast.vue.mjs'
import PhUserFocus from '@phosphor-icons/vue/dist/icons/PhUserFocus.vue.mjs'
import PhCloudRain from '@phosphor-icons/vue/dist/icons/PhCloudRain.vue.mjs'
import PhHouse from '@phosphor-icons/vue/dist/icons/PhHouse.vue.mjs'
import PhBuildings from '@phosphor-icons/vue/dist/icons/PhBuildings.vue.mjs'
import PhMapPin from '@phosphor-icons/vue/dist/icons/PhMapPin.vue.mjs'
import PhMagicWand from '@phosphor-icons/vue/dist/icons/PhMagicWand.vue.mjs'
import PhEye from '@phosphor-icons/vue/dist/icons/PhEye.vue.mjs'
import PhEyeSlash from '@phosphor-icons/vue/dist/icons/PhEyeSlash.vue.mjs'
import PhUsers from '@phosphor-icons/vue/dist/icons/PhUsers.vue.mjs'
import PhUserCircle from '@phosphor-icons/vue/dist/icons/PhUserCircle.vue.mjs'
import PhUserMinus from '@phosphor-icons/vue/dist/icons/PhUserMinus.vue.mjs'
import PhUpload from '@phosphor-icons/vue/dist/icons/PhUpload.vue.mjs'
import PhCloudArrowUp from '@phosphor-icons/vue/dist/icons/PhCloudArrowUp.vue.mjs'
import PhFileText from '@phosphor-icons/vue/dist/icons/PhFileText.vue.mjs'
import PhMagnifyingGlass from '@phosphor-icons/vue/dist/icons/PhMagnifyingGlass.vue.mjs'
import PhGear from '@phosphor-icons/vue/dist/icons/PhGear.vue.mjs'
import PhArrowsCounterClockwise from '@phosphor-icons/vue/dist/icons/PhArrowsCounterClockwise.vue.mjs'
import PhArrowClockwise from '@phosphor-icons/vue/dist/icons/PhArrowClockwise.vue.mjs'
import PhWaveform from '@phosphor-icons/vue/dist/icons/PhWaveform.vue.mjs'
import PhTimer from '@phosphor-icons/vue/dist/icons/PhTimer.vue.mjs'
import PhFirstAidKit from '@phosphor-icons/vue/dist/icons/PhFirstAidKit.vue.mjs'
import PhSiren from '@phosphor-icons/vue/dist/icons/PhSiren.vue.mjs'
import PhWarningOctagon from '@phosphor-icons/vue/dist/icons/PhWarningOctagon.vue.mjs'
import PhInfo from '@phosphor-icons/vue/dist/icons/PhInfo.vue.mjs'
import PhStopCircle from '@phosphor-icons/vue/dist/icons/PhStopCircle.vue.mjs'
import PhPackage from '@phosphor-icons/vue/dist/icons/PhPackage.vue.mjs'
import PhBellRinging from '@phosphor-icons/vue/dist/icons/PhBellRinging.vue.mjs'
import PhChartBar from '@phosphor-icons/vue/dist/icons/PhChartBar.vue.mjs'
import PhMonitorPlay from '@phosphor-icons/vue/dist/icons/PhMonitorPlay.vue.mjs'
import PhChatText from '@phosphor-icons/vue/dist/icons/PhChatText.vue.mjs'
import PhStar from '@phosphor-icons/vue/dist/icons/PhStar.vue.mjs'
import PhTrendUp from '@phosphor-icons/vue/dist/icons/PhTrendUp.vue.mjs'
import PhTrendDown from '@phosphor-icons/vue/dist/icons/PhTrendDown.vue.mjs'
import PhPulse from '@phosphor-icons/vue/dist/icons/PhPulse.vue.mjs'
import PhCheck from '@phosphor-icons/vue/dist/icons/PhCheck.vue.mjs'
import PhSignOut from '@phosphor-icons/vue/dist/icons/PhSignOut.vue.mjs'
import PhCheckCircle from '@phosphor-icons/vue/dist/icons/PhCheckCircle.vue.mjs'
import PhSparkle from '@phosphor-icons/vue/dist/icons/PhSparkle.vue.mjs'
import PhCircleNotch from '@phosphor-icons/vue/dist/icons/PhCircleNotch.vue.mjs'
import PhWarningCircle from '@phosphor-icons/vue/dist/icons/PhWarningCircle.vue.mjs'
import PhQuestion from '@phosphor-icons/vue/dist/icons/PhQuestion.vue.mjs'
import PhPencilLine from '@phosphor-icons/vue/dist/icons/PhPencilLine.vue.mjs'
import PhPlus from '@phosphor-icons/vue/dist/icons/PhPlus.vue.mjs'
import PhX from '@phosphor-icons/vue/dist/icons/PhX.vue.mjs'
import PhRobot from '@phosphor-icons/vue/dist/icons/PhRobot.vue.mjs'
import PhPaperPlaneRight from '@phosphor-icons/vue/dist/icons/PhPaperPlaneRight.vue.mjs'
import PhClock from '@phosphor-icons/vue/dist/icons/PhClock.vue.mjs'
import PhCaretRight from '@phosphor-icons/vue/dist/icons/PhCaretRight.vue.mjs'
import PhTShirt from '@phosphor-icons/vue/dist/icons/PhTShirt.vue.mjs'
import PhSpeakerHigh from '@phosphor-icons/vue/dist/icons/PhSpeakerHigh.vue.mjs'
import PhFloppyDisk from '@phosphor-icons/vue/dist/icons/PhFloppyDisk.vue.mjs'
import PhSun from '@phosphor-icons/vue/dist/icons/PhSun.vue.mjs'
import PhMoon from '@phosphor-icons/vue/dist/icons/PhMoon.vue.mjs'
import PhSlidersHorizontal from '@phosphor-icons/vue/dist/icons/PhSlidersHorizontal.vue.mjs'
import PhTag from '@phosphor-icons/vue/dist/icons/PhTag.vue.mjs'
import PhSmiley from '@phosphor-icons/vue/dist/icons/PhSmiley.vue.mjs'
import PhCoins from '@phosphor-icons/vue/dist/icons/PhCoins.vue.mjs'
import PhChartPieSlice from '@phosphor-icons/vue/dist/icons/PhChartPieSlice.vue.mjs'
import PhChartLineUp from '@phosphor-icons/vue/dist/icons/PhChartLineUp.vue.mjs'
import PhTarget from '@phosphor-icons/vue/dist/icons/PhTarget.vue.mjs'
import PhLightbulb from '@phosphor-icons/vue/dist/icons/PhLightbulb.vue.mjs'
import PhUsersThree from '@phosphor-icons/vue/dist/icons/PhUsersThree.vue.mjs'
import PhCrown from '@phosphor-icons/vue/dist/icons/PhCrown.vue.mjs'
import PhCurrencyCny from '@phosphor-icons/vue/dist/icons/PhCurrencyCny.vue.mjs'
// 感受度报告页图标（Tabler：2px 线性描边，参考主流 BI 风格；其余 tab 暂保留 Phosphor）
import {
  IconRefresh, IconLoader2, IconAlertCircle,
  IconMoodSmile, IconMessages, IconStar, IconListDetails,
  IconListSearch, IconClipboardCheck, IconFileAnalytics, IconFileText, IconMessage2,
  IconMessageOff,
} from '@tabler/icons-vue'
import DanmakuFlow from '@/components/DanmakuFlow.vue'
import {
  getDigitalHumanPresets, getDigitalHumanConfig, saveDigitalHumanConfig,
  liveSetAvatar, generateAvatarAI, PORTRAIT_FLV,
  putAvatarMeta, putAvatarPublish, platePreviewUrl, liveSetLip, liveSetEmotion,
  generateCandidates, listCandidates, candidatePreviewUrl, adoptCandidate,
} from '@/api/index'

const sceneStore = useSceneStore()
const authStore  = useAuthStore()
const router     = useRouter()

const ADMIN_TABS = ['avatar', 'knowledge', 'broadcast', 'dashboard', 'report', 'consumption']
const savedTab = localStorage.getItem('adminTab')
// 大屏是全屏显示模式而非常驻 tab：刷新后无用户手势无法自动进全屏，落回知识库
const activeTab = ref(ADMIN_TABS.includes(savedTab) && savedTab !== 'dashboard' ? savedTab : 'knowledge')

// ── 实时弹幕「游客正在问」（顶栏迷你条 + 大屏弹幕带共用开关）──
const danmakuOn = ref(localStorage.getItem('admin-danmaku') !== 'off')
function toggleDanmaku() {
  danmakuOn.value = !danmakuOn.value
  localStorage.setItem('admin-danmaku', danmakuOn.value ? 'on' : 'off')
}
// 大屏弹幕带轨道数自适应：矮视口降 2 轨，把高度还给图表
const dmkLanes = ref(window.innerHeight < 1024 ? 2 : 3)
window.addEventListener('resize', () => { dmkLanes.value = window.innerHeight < 1024 ? 2 : 3 })
const chartAnimKey = ref(0)
watch(activeTab, async (tab) => {
  if (tab !== 'dashboard') localStorage.setItem('adminTab', tab)
  if (tab === 'dashboard') {
    chartAnimKey.value++          // key++ 销毁旧 DOM，先清 ECharts 实例
    Object.values(_ec).forEach(c => c?.dispose())
    _ec = {}
    if (!dashLoaded.value) {
      loadDashboard()
    } else {
      await nextTick()            // 等新 DOM 就绪后重绘
      _ecUpdate()
    }
  }
  if (tab === 'report' && !reportLoaded.value) loadReport()
  if (tab === 'consumption' && !consLoaded.value) loadConsumption()
  // 报告图表初始化统一走下方 flush:'post' 的 watcher（保证容器已渲染，防直刷落在报告页时 nextTick 抢跑）
  if (tab === 'avatar') {
    await loadAvatarTab()
  } else {
    destroyPreview()
    monitorOpen.value = false
  }
  // 应急广播页：进入时起现场预览 + 状态轮询；离开时全部收起（含循环播报）
  if (tab === 'broadcast') {
    startBcStatus()
    await nextTick()
    startBcPreview()
  } else {
    stopBcStatus()
    destroyBcPreview()
    stopRepeat()
  }
})

// 大屏不再是页面 tab（是全屏投放模式，入口=侧栏底部启动卡）；
// 剩余三个页面按职能分组，避免单列三项显得空荡
const navGroups = [
  { label: '日常运营', items: [
    { key:'knowledge', label:'知识库',     icon: PhFileText },
    { key:'broadcast', label:'应急广播',   icon: PhBroadcast },
    { key:'report',    label:'感受度报告', icon: PhPulse },
  ]},
  { label: '经营分析', items: [
    { key:'consumption', label:'消费分析', icon: PhCoins },
  ]},
  { label: '数字人', items: [
    { key:'avatar',    label:'形象管理',   icon: PhMagicWand },
  ]},
]

// ── 分类彩色标签（F7）：各分类配柔和主色系色板，前置圆点/胶囊以示区分 ──────
const CAT_COLORS = {
  // FAQ 分类
  '基础信息': '#4F5BE0', '景点介绍': '#2E9E7B', '票务信息': '#E0785A',
  '交通停车': '#3E8FD0', '餐饮服务': '#D98A2B', '历史文化': '#9B5BC7',
  // 文本段落分类
  '景区概况': '#4F5BE0', '景点讲解': '#2E9E7B', '服务信息': '#3E8FD0', '活动介绍': '#D98A2B',
}
const _CAT_FALLBACK = ['#4F5BE0', '#2E9E7B', '#E0785A', '#3E8FD0', '#D98A2B', '#9B5BC7', '#C7566F']
function catColor(cat) {
  if (CAT_COLORS[cat]) return CAT_COLORS[cat]
  let h = 0
  for (const ch of (cat || '')) h = (h * 31 + ch.charCodeAt(0)) >>> 0
  return _CAT_FALLBACK[h % _CAT_FALLBACK.length]
}

function handleLogout() { authStore.logout(router) }

// ── 形象管理（生产者视角：形象库 + 发布 + 离线参数工作台 + 应用到大屏）──────────
// 设计原则：预览一律离线（platePreviewUrl 取底板 JPEG），不碰直播流 → 多用户零串扰；
// 只有显式「应用到大屏」才 POST /live/avatar（last-writer-wins，UI 明示）。
const AV_STYLES = ['推荐', '现代', '古风', '民族']
const SWEET_BASE = 'female_sweet'
const SWEET_OUTFITS = ['outfit_qipao', 'outfit_hanfu', 'outfit_blazer', 'outfit_ethnic', 'outfit_vest', 'outfit_coat']
const EMO_LABELS = { neutral: '平静', happy: '愉悦', concerned: '关切' }

const avatars = ref([]); const voices = ref([]); const backgrounds = ref([])
const avStyle = ref('推荐'); const avGender = ref('all')
const applying = ref(false)
const setAsDefault = ref(false)
const monitorOpen = ref(false)
const previewVideoEl = ref(null); let flvPlayer = null
const lipEnabled = ref(true)    // Phase E 引擎补丁已上线（DITTO_LIP_SCALE 逐帧读）

// 工作台草稿：所有调参只落这里，即时刷新离线预览，不触碰直播流
const draft = reactive({
  avatarId: '', voiceId: '', bgId: '',
  stageName: '', welcome: '', emotion: 'neutral', lipScale: 0.68,
})
const plateUrl = ref('')       // 离线预览底板 URL
const plateNote = ref('')      // 变体缺失黄条提示

const identities = computed(() => avatars.value.filter(a => !SWEET_OUTFITS.includes(a.id)))
const shownAvatars = computed(() => identities.value.filter(a =>
  (avStyle.value === '推荐' ? a.recommended : a.style === avStyle.value) &&
  (avGender.value === 'all' || a.gender === avGender.value)))
const outfits = computed(() => {
  if (draft.avatarId !== SWEET_BASE && !SWEET_OUTFITS.includes(draft.avatarId)) return []
  const byId = new Map(avatars.value.map(a => [a.id, a]))
  return [SWEET_BASE, ...SWEET_OUTFITS].map(id => byId.get(id)).filter(Boolean)
})
const selVoiceName = computed(() => voices.value.find(v => v.id === draft.voiceId)?.name || '')

// KPI 概览
const kpiTotal = computed(() => identities.value.length)
const kpiPublished = computed(() => avatars.value.filter(a => a.published).length)
const kpiReady = computed(() => avatars.value.filter(a => !a.coming_soon).length)
const kpiCustom = computed(() => avatars.value.filter(a => (a.id || '').startsWith('custom_')).length)

const emoLabel = (e) => EMO_LABELS[e] || e
// 试听：音色样本 manifest 里有才可播（约定同游客端：/voice_samples/manifest.json 数组列出可用样音）
const voiceManifest = ref(null)
const VOICE_BASE = `${import.meta.env.BASE_URL || '/'}voice_samples/`   // 随 vite base（/admin/）解析
async function loadVoiceManifest() {
  try {
    const res = await fetch(`${VOICE_BASE}manifest.json`, { cache: 'no-cache' })
    voiceManifest.value = res.ok ? await res.json() : null
  } catch { voiceManifest.value = null }
}
function voiceSampleUrl(id) {
  const m = voiceManifest.value
  if (!m) return null
  const has = Array.isArray(m) ? m.includes(id) : !!m[id]
  if (!has) return null
  const file = Array.isArray(m) ? `${id}.mp3` : (typeof m[id] === 'string' ? m[id] : `${id}.mp3`)
  return `${VOICE_BASE}${file}`
}
const canPlayVoice = (id) => !!voiceSampleUrl(id)

async function loadAvatarTab() {
  try {
    // 管理端=生产者视角：拉全量 + published 标注
    const p = await getDigitalHumanPresets(sceneStore.scenicId, 'admin')
    avatars.value = (p.avatars || []).filter(a => !a.legacy)
    voices.value = p.voices || []
    backgrounds.value = p.backgrounds || []
    if (voiceManifest.value === null) loadVoiceManifest()
    const cfg = await getDigitalHumanConfig(sceneStore.scenicId)
    const first = avatars.value.find(a => a.id === cfg.avatar_id) || avatars.value.find(a => !a.coming_soon) || avatars.value[0]
    if (first) selectAvatar(first, { silent: true, voiceId: cfg.voice_id, bgId: cfg.background_id })
    pollCandidates()
  } catch { ElMessage.error('加载形象库失败') }
}

// 选形象 = 只改草稿 + 刷新离线预览，绝不热切直播（串扰修复核心）
function selectAvatar(a, opts = {}) {
  if (a.coming_soon) { ElMessage.info('该形象底板烘录中，暂不可用'); return }
  draft.avatarId = a.id
  draft.stageName = a.stage_name || a.name || ''
  draft.welcome = a.welcome_text || ''
  if (opts.voiceId !== undefined) draft.voiceId = opts.voiceId || draft.voiceId || 'voice_gentle_f'
  if (!draft.voiceId) draft.voiceId = 'voice_gentle_f'
  if (opts.bgId !== undefined) draft.bgId = opts.bgId || ''
  refreshPlate()
}

// 刷新离线预览底板（参数变即换图，破缓存靠 platePreviewUrl 内 _t）
function refreshPlate() {
  if (!draft.avatarId) { plateUrl.value = ''; return }
  plateNote.value = ''
  plateUrl.value = platePreviewUrl(draft.avatarId, sceneStore.scenicId, 'portrait', draft.bgId)
  if (draft.bgId) {
    const bgScenic = draft.bgId.replace(/^bg_/, '')
    // 底板变体是否已烘无法在前端预判，交给 onPlateError/onload 头，简单提示
    plateNote.value = ''
  }
}

// 发布开关：写该景区可见性（游客端消费）
async function togglePublish(a, val) {
  try {
    await putAvatarPublish({ scenic_id: sceneStore.scenicId, avatar_id: a.id, enabled: val ? 1 : 0 })
    ElMessage.success(val ? `「${a.stage_name || a.name}」已对游客发布` : `已下架「${a.stage_name || a.name}」`)
  } catch { a.published = !val; ElMessage.error('发布状态更新失败') }
}

// 存艺名（全局 meta）
async function saveStageName() {
  const name = (draft.stageName || '').trim()
  if (!draft.avatarId || !name) return
  const cur = avatars.value.find(a => a.id === draft.avatarId)
  if (cur && cur.stage_name === name) return
  try {
    await putAvatarMeta({ avatar_id: draft.avatarId, stage_name: name })
    if (cur) cur.stage_name = name
    ElMessage.success('艺名已更新')
  } catch { ElMessage.error('艺名更新失败（需 1-8 字、非纯符号）') }
}

// 存欢迎语（全局 meta）
async function saveWelcome() {
  if (!draft.avatarId) return
  const cur = avatars.value.find(a => a.id === draft.avatarId)
  if (cur && (cur.welcome_text || '') === draft.welcome) return
  try {
    await putAvatarMeta({ avatar_id: draft.avatarId, welcome_text: draft.welcome })
    if (cur) cur.welcome_text = draft.welcome
    ElMessage.success('欢迎语已保存')
  } catch { ElMessage.error('欢迎语保存失败') }
}

// 试听音色（离线，本地播样本）
let _voiceAudio = null
function tryVoice(id) {
  const url = voiceSampleUrl(id)
  if (!url) return
  try {
    if (_voiceAudio) { _voiceAudio.pause() }
    _voiceAudio = new Audio(url)
    _voiceAudio.play().catch(() => ElMessage.warning('样本播放失败'))
  } catch { ElMessage.warning('样本播放失败') }
}

// 背景收起态只显「·」前的地名主体（去括号说明），短而整齐
function bgLabel(name) {
  if (!name) return ''
  return name.split('·')[0].replace(/（.*?）/g, '').trim()
}

// 应用到大屏 = 唯一会改变现场画面的显式动作（确认弹窗 → 逐步）
async function applyToScreen() {
  if (!draft.avatarId) return
  try {
    await ElMessageBox.confirm(
      '将立即改变现场大屏画面（每屏一路直播，应用者生效）。确认应用当前形象与参数？',
      '应用到大屏', { confirmButtonText: '应用', cancelButtonText: '取消', type: 'warning' })
  } catch { return }
  applying.value = true
  try {
    // 1) 先落艺名/欢迎语（若草稿有改动，saveStageName/saveWelcome 内部自判）
    await saveStageName(); await saveWelcome()
    // 2) 热切形象 + 背景
    const r = await liveSetAvatar(draft.avatarId, sceneStore.scenicId, 'portrait', draft.bgId)
    if (!r || !r.ok) { ElMessage.warning('大屏热切失败（直播流可能未就绪）'); return }
    if (draft.bgId) {
      const bgScenic = draft.bgId.replace(/^bg_/, '')
      if (bgScenic && !(r.resolved || '').includes(bgScenic))
        ElMessage.info(`「${bgLabel(backgrounds.value.find(b=>b.id===draft.bgId)?.name||'')}」暂未烘出该形象底板，先显示默认背景`)
    }
    // 3) 情绪基调热切
    await liveSetEmotion(draft.emotion, 'portrait')
    // 4) 嘴幅缩放（DITTO_LIP_SCALE，1=原始，越小越含蓄）
    if (lipEnabled.value) await liveSetLip(draft.lipScale, 'both')
    // 5) 可选设为景区默认
    if (setAsDefault.value) {
      const av = avatars.value.find(a => a.id === draft.avatarId)
      const vc = voices.value.find(v => v.id === draft.voiceId)
      const bg = backgrounds.value.find(b => b.id === draft.bgId)
      await saveDigitalHumanConfig({
        scenic_id: sceneStore.scenicId,
        avatar_id: draft.avatarId, avatar_name: av?.name || draft.avatarId,
        voice_id: draft.voiceId, voice_name: vc?.name || '',
        background_id: draft.bgId || '', background_name: bg?.name || '',
      })
    }
    ElMessage.success(setAsDefault.value ? '已应用到大屏并设为本景区默认' : '已应用到大屏')
  } catch { ElMessage.error('应用失败') }
  finally { applying.value = false }
}

// 大屏实况（仅监看，看流无副作用）
function toggleMonitor() {
  monitorOpen.value = !monitorOpen.value
  if (monitorOpen.value) nextTick(startPreview)
  else destroyPreview()
}
async function startPreview() {
  if (!previewVideoEl.value) return
  destroyPreview()
  try {
    const mod = await import('mpegts.js')
    const mpegts = mod.default || mod
    if (!mpegts?.isSupported?.()) return
    flvPlayer = mpegts.createPlayer(
      { type: 'flv', isLive: true, url: PORTRAIT_FLV },
      { liveSync: true, liveSyncMaxLatency: 3.0, liveSyncTargetLatency: 1.2, liveSyncPlaybackRate: 1.12 })
    flvPlayer.attachMediaElement(previewVideoEl.value)
    flvPlayer.load()
    flvPlayer.play().catch(() => {})
  } catch (e) {
    console.warn('[admin] portrait preview disabled:', e)
  }
}
function destroyPreview() { if (flvPlayer) { try { flvPlayer.destroy() } catch {} flvPlayer = null } }

// AI 生成专属向导（通义万相）→ 后端全真链路：生成 → 落 ditto_avatars 双比例 → 入库可热切
const customPrompt = ref('')
const genElapsed   = ref(0)
let progressTimer = null
async function handleGenerate() {
  genElapsed.value = 0
  progressTimer = setInterval(() => { genElapsed.value++ }, 1000)
  try {
    const r = await generateAvatarAI({
      prompt: customPrompt.value || '',
      scenic_id: sceneStore.scenicId,
      gender: avGender.value === 'male' ? 'male' : 'female',
      style: avStyle.value === '推荐' ? '现代' : avStyle.value,
    })
    if (r && r.ok && r.avatar) {
      await loadAvatarTab()
      const a = avatars.value.find(x => x.id === r.avatar.id) || r.avatar
      selectAvatar(a)
      customPrompt.value = ''
      ElMessage.success('专属形象已生成并加入形象库，可在工作台调参后应用到大屏')
    } else {
      ElMessage.error((r && r.detail) || '生成失败')
    }
  } catch { ElMessage.error('生成失败，请检查 DashScope 余额/Key') }
  finally { clearInterval(progressTimer) }
}

// ── 甜美女性默认候选批（生成 → 挑选 → 采用 → 体检后设默认）──────────────
const candidates = ref([])
const candRunning = ref(false)
const candDone = ref(0)
const candTarget = ref(0)
const candSel = ref('')
const candStageName = ref('')
const candAdopting = ref(false)
let candTimer = null
const candSelCentered = computed(() => {
  const c = candidates.value.find(x => x.cand_id === candSel.value)
  return c ? c.centered : false
})
const candPreview = (c) => candidatePreviewUrl(c.cand_id)

async function pollCandidates() {
  try {
    const d = await listCandidates()
    candidates.value = d.candidates || []
    const p = d.progress || {}
    candRunning.value = !!p.running
    candDone.value = p.done || 0
    candTarget.value = p.target || 0
    if (!p.running && candTimer) { clearInterval(candTimer); candTimer = null; if ((p.done||0) > 0) ElMessage.success(`已生成 ${p.done} 张候选，请挑选`) }
  } catch {}
}
async function genCandidates() {
  try {
    const r = await generateCandidates(sceneStore.scenicId, 6, '')
    if (!r || !r.ok) { ElMessage.error((r && r.detail) || '启动生成失败'); return }
    candRunning.value = true; candTarget.value = r.target || 6; candDone.value = 0
    if (candTimer) clearInterval(candTimer)
    candTimer = setInterval(pollCandidates, 5000)
    ElMessage.info('已开始生成 6 张甜美候选，约 3 分钟')
  } catch { ElMessage.error('启动生成失败') }
}
async function adoptCandidate_() {
  if (!candSel.value || !candSelCentered.value) return
  candAdopting.value = true
  try {
    const r = await adoptCandidate(candSel.value, { name: '甜美导览专员', stage_name: candStageName.value || '' })
    if (r && r.ok) {
      await loadAvatarTab()
      const a = avatars.value.find(x => x.id === r.avatar?.id)
      if (a) selectAvatar(a)
      candSel.value = ''; candStageName.value = ''
      ElMessage.success('候选已采用，请在 GPU 机过体检后「应用/设默认」')
    } else { ElMessage.error((r && r.detail) || '采用失败') }
  } catch { ElMessage.error('采用失败') }
  finally { candAdopting.value = false }
}

// ── 知识库管理 ─────────────────────────────────
const kbSearch = ref('')
const kbReplace = ref(false)
const kbConfig = ref({ strategy:'hybrid', topK:5, threshold:0.35 })
const kbConfigured    = ref(false)
const kbConfigDirty   = ref(false)
const kbConfigSaving  = ref(false)

const knowledgeDocs = ref([])

const statusMap = { indexed:'已索引', indexing:'索引中', unsupported:'不支持', '已上传':'已上传' }
function fmtDoc(d) {
  const ext = (d.filename || '').split('.').pop().toLowerCase()
  const bytes = d.size_bytes || 0
  const size = bytes < 1024 ? `${bytes}B` : bytes < 1024**2 ? `${(bytes/1024).toFixed(1)}KB` : `${(bytes/1024**2).toFixed(1)}MB`
  return {
    id: d.id,
    name: d.filename || d.name,
    type: ext,
    chunks: d.chunks ?? '-',
    uploadTime: (d.created_at || d.uploadTime || '').slice(0, 16).replace('T', ' '),
    size,
    sizeBytes: bytes,
    status: statusMap[d.status] || d.status,
  }
}

async function loadKnowledgeDocs() {
  try {
    const params = sceneStore.scenicId ? { scenic_id: sceneStore.scenicId } : {}
    const res = await axios.get('/api/knowledge/docs', { params })
    if (res.data.code === 0) knowledgeDocs.value = (res.data.data?.docs || []).map(fmtDoc)
  } catch { /* 后端未启动时静默 */ }
}

const filteredDocs = computed(() =>
  kbSearch.value ? knowledgeDocs.value.filter(d => d.name.includes(kbSearch.value) || d.type.includes(kbSearch.value))
                 : knowledgeDocs.value
)

const totalSize = computed(() => {
  const bytes = knowledgeDocs.value.reduce((a, d) => a + (d.sizeBytes || 0), 0)
  if (bytes < 1024) return `${bytes}B`
  if (bytes < 1024 ** 2) return `${(bytes / 1024).toFixed(1)}KB`
  return `${(bytes / 1024 ** 2).toFixed(1)}MB`
})

function beforeUpload(file) {
  if (file.size / 1024 / 1024 > 20) { ElMessage.error('文件不能超过 20MB'); return false }
  return true
}

async function handleKnowledgeUpload({ file }) {
  let doReplace = false
  if (kbReplace.value) {
    try {
      await ElMessageBox.confirm(
        '整库替换已开启：将先清空本景区全部旧知识再入库新文档，此操作不可撤销。批量选择多文件时仅首个文件触发清空。',
        '确认整库替换', { type:'warning', confirmButtonText:'清空并替换', cancelButtonText:'取消' })
      doReplace = true
      kbReplace.value = false   // 立即关闭开关：同批其余文件走普通追加，避免相互清库
    } catch { return }
  }
  const formData = new FormData()
  formData.append('files', file)
  formData.append('scenic_id', sceneStore.scenicId || 'lingshan')
  formData.append('replace', doReplace ? 'true' : 'false')
  try {
    const res = await axios.post('/api/knowledge/upload', formData)
    if (res.data.code === 0) {
      await loadKnowledgeDocs()
      const items = res.data.data?.items || []
      const unsupported = items.filter(i => i.status === 'unsupported')
      if (unsupported.length) ElMessage.warning(`${unsupported.map(i=>i.filename).join('、')} 无文本层，未入库`)
      else ElMessage.success(`上传成功，共 ${items.reduce((a,i)=>a+(i.chunks||0),0)} 个片段已索引`)
    }
  } catch (e) {
    ElMessage.error('上传失败：' + (e.response?.data?.detail || e.message))
  }
}

// ── 上传弹窗（F1）：点「上传文档」→ 弹窗 → 「选择文件」开文件夹 → 「开始上传」──
const uploadDialogVisible = ref(false)
const uploadFileList = ref([])     // el-upload 收集的文件（auto-upload=false）
const uploadingKb = ref(false)
function openUploadDialog() { uploadFileList.value = []; uploadDialogVisible.value = true }
function onUploadExceedHint() { ElMessage.info('可一次选择多个文件') }
async function startKbUpload() {
  const files = uploadFileList.value.map(f => f.raw).filter(Boolean)
  if (!files.length) { ElMessage.error('请先选择文件'); return }
  let doReplace = false
  if (kbReplace.value) {
    try {
      await ElMessageBox.confirm(
        '整库替换已开启：将先清空本景区全部旧知识再入库新文档，此操作不可撤销。',
        '确认整库替换', { type:'warning', confirmButtonText:'清空并替换', cancelButtonText:'取消' })
      doReplace = true
    } catch { return }
  }
  uploadingKb.value = true
  let totalChunks = 0, failed = []
  try {
    for (let i = 0; i < files.length; i++) {
      const fd = new FormData()
      fd.append('files', files[i])
      fd.append('scenic_id', sceneStore.scenicId || 'lingshan')
      fd.append('replace', (doReplace && i === 0) ? 'true' : 'false')  // 仅首个触发清库
      try {
        const res = await axios.post('/api/knowledge/upload', fd)
        const items = res.data?.data?.items || []
        const bad = items.filter(it => it.status === 'unsupported')
        if (bad.length) failed.push(...bad.map(b => b.filename))
        totalChunks += items.reduce((a, it) => a + (it.chunks || 0), 0)
      } catch (e) { failed.push(files[i].name) }
    }
    await loadKnowledgeDocs()
    if (failed.length) ElMessage.warning(`部分文件未入库：${failed.join('、')}`)
    else ElMessage.success(`上传成功，共 ${totalChunks} 个片段已索引`)
    kbReplace.value = false
    uploadDialogVisible.value = false
    uploadFileList.value = []
  } finally {
    uploadingKb.value = false
  }
}

const docDeletePending = ref(null)
let _docDeleteTimer = null

async function deleteDoc(row) {
  await ElMessageBox.confirm(
    `「${row.name}」删除后无法恢复。`,
    '删除文档', { type:'warning', confirmButtonText:'删除', cancelButtonText:'取消' }
  )
  knowledgeDocs.value = knowledgeDocs.value.filter(d => d.id !== row.id)
  docDeletePending.value = row
  clearTimeout(_docDeleteTimer)
  _docDeleteTimer = setTimeout(async () => {
    if (!docDeletePending.value) return
    try { await axios.delete(`/api/knowledge/docs/${docDeletePending.value.id}`) }
    catch { await loadKnowledgeDocs(); ElMessage.error('删除失败，文档已恢复') }
    docDeletePending.value = null
  }, 5000)
}

function undoDeleteDoc() {
  clearTimeout(_docDeleteTimer)
  if (docDeletePending.value) {
    knowledgeDocs.value = [docDeletePending.value, ...knowledgeDocs.value]
    docDeletePending.value = null
    ElMessage.success('已撤销')
  }
}

async function reindexDoc(row) {
  row.status = '索引中'
  try {
    const res = await axios.post(`${ANALYTICS_BASE}/kb/docs/${row.id}/reindex`, null, { timeout: 120000 })
    const d = res.data || {}
    await loadKnowledgeDocs()
    ElMessage.success(`「${row.name}」已重建：${d.chunks} 个片段重新入库`)
  } catch (e) {
    await loadKnowledgeDocs()
    const detail = e.response?.data?.detail || e.message
    ElMessage.error(`重建失败：${detail}`)
  }
}

// ── 检索设置（真实读写 /kb/retrieval-config，按景区生效）──
async function loadKbConfig() {
  try {
    const res = await axios.get(`${ANALYTICS_BASE}/kb/retrieval-config`, {
      params: { scenic_id: sceneStore.scenicId || 'lingshan' } })
    const d = res.data || {}
    kbConfig.value = { strategy: d.strategy || 'hybrid', topK: d.top_k ?? 5, threshold: d.threshold ?? 0.35 }
    kbConfigured.value = !!d.configured
    kbConfigDirty.value = false
  } catch { /* 加载失败保持当前显示 */ }
}

async function saveKbConfig() {
  kbConfigSaving.value = true
  try {
    await axios.put(`${ANALYTICS_BASE}/kb/retrieval-config`, {
      scenic_id: sceneStore.scenicId || 'lingshan',
      strategy: kbConfig.value.strategy,
      top_k: kbConfig.value.topK,
      threshold: kbConfig.value.threshold,
    })
    kbConfigured.value = true
    kbConfigDirty.value = false
    ElMessage.success('检索配置已保存，即刻对本景区问答生效')
  } catch (e) {
    ElMessage.error('保存失败：' + (e.response?.data?.detail || e.message))
  } finally { kbConfigSaving.value = false }
}

async function resetKbConfig() {
  try {
    await axios.delete(`${ANALYTICS_BASE}/kb/retrieval-config`, {
      params: { scenic_id: sceneStore.scenicId || 'lingshan' } })
    await loadKbConfig()
    ElMessage.success('已恢复系统默认检索参数')
  } catch (e) { ElMessage.error('操作失败：' + (e.response?.data?.detail || e.message)) }
}

// ── 知识库体检（/kb/self-test：自动出题→RAG答题→关键词评分）──
const stSample  = ref(5)
const stLoading = ref(false)
const stElapsed = ref(0)
const stResult  = ref(null)
let _stTimer = null
async function runSelfTest() {
  stLoading.value = true
  stElapsed.value = 0
  _stTimer = setInterval(() => { stElapsed.value++ }, 1000)
  try {
    const res = await axios.post(`${ANALYTICS_BASE}/kb/self-test`, {
      scenic_id: sceneStore.scenicId || 'lingshan',
      sample: stSample.value,
    }, { timeout: 300000 })
    stResult.value = res.data
    const acc = res.data?.accuracy ?? 0
    if (acc >= 90) ElMessage.success(`体检完成：准确率 ${acc}%，达到 90% 交付标准`)
    else ElMessage.warning(`体检完成：准确率 ${acc}%，建议查看未过题目补充对应知识`)
  } catch (e) {
    ElMessage.error('体检失败：' + (e.response?.data?.detail || e.message))
  } finally {
    clearInterval(_stTimer)
    stLoading.value = false
  }
}

// ── 知识库子 Tab ──────────────────────────────
const kbTab = ref('upload')
watch(kbTab, (t) => { if (t === 'config') loadKbConfig() })

// ── FAQ 问答 ──────────────────────────────────
const faqCats    = ['全部', '基础信息', '景点介绍', '票务信息', '交通停车', '餐饮服务', '历史文化']
const faqCatFilter = ref('全部')
const faqSearchQ   = ref('')

const faqItems = ref([])

async function loadFaq() {
  try {
    const params = sceneStore.scenicId ? { scenic_id: sceneStore.scenicId } : {}
    const res = await axios.get('/api/knowledge/faq', { params })
    if (res.data.code === 0) {
      faqItems.value = (res.data.data?.items || []).map(f => ({
        id: f.id, q: f.question, a: f.answer, cat: f.category, updated: f.updated_at?.slice(0,10) || ''
      }))
    }
  } catch { /* 静默 */ }
}

const filteredFaq = computed(() => {
  let list = faqItems.value
  if (faqCatFilter.value !== '全部') list = list.filter(f => f.cat === faqCatFilter.value)
  if (faqSearchQ.value) {
    const q = faqSearchQ.value
    list = list.filter(f => f.q.includes(q) || f.a.includes(q))
  }
  return list
})

const faqAdding  = ref(false)
const faqAddForm = ref({ q:'', a:'', cat:'基础信息' })
const faqEditId  = ref(null)
const faqEditForm = ref({ q:'', a:'', cat:'基础信息' })

function startAddFaq() { faqAdding.value = true; faqAddForm.value = { q:'', a:'', cat:'基础信息' } }
async function saveAddFaq() {
  if (!faqAddForm.value.q.trim() || !faqAddForm.value.a.trim()) { ElMessage.error('问题和答案不能为空'); return }
  try {
    await axios.post('/api/knowledge/faq', {
      scenic_id: sceneStore.scenicId || 'lingshan',
      question: faqAddForm.value.q,
      answer: faqAddForm.value.a,
      category: faqAddForm.value.cat,
    })
    faqAdding.value = false
    await loadFaq()
    ElMessage.success('已添加，已同步游客端，相同提问将以最高优先级作答')
  } catch (e) { ElMessage.error('添加失败：' + (e.response?.data?.detail || e.message)) }
}
function startEditFaq(item) {
  faqEditId.value = item.id
  faqEditForm.value = { q: item.q, a: item.a, cat: item.cat }
}
async function saveEditFaq(item) {
  if (!faqEditForm.value.q.trim() || !faqEditForm.value.a.trim()) { ElMessage.error('问题和答案不能为空'); return }
  try {
    await axios.put(`/api/knowledge/faq/${item.id}`, {
      scenic_id: sceneStore.scenicId || 'lingshan',
      question: faqEditForm.value.q,
      answer: faqEditForm.value.a,
      category: faqEditForm.value.cat,
    })
    faqEditId.value = null
    await loadFaq()
    ElMessage.success('已保存')
  } catch (e) { ElMessage.error('保存失败：' + (e.response?.data?.detail || e.message)) }
}
async function deleteFaqItem(item) {
  await ElMessageBox.confirm(`「${item.q}」删除后无法恢复。`, '删除问答', { type:'warning', confirmButtonText:'删除', cancelButtonText:'取消' })
  try {
    await axios.delete(`/api/knowledge/faq/${item.id}`)
    faqItems.value = faqItems.value.filter(f => f.id !== item.id)
    ElMessage.success('已删除')
  } catch (e) { ElMessage.error('删除失败：' + (e.response?.data?.detail || e.message)) }
}

// ── 文本段落 ──────────────────────────────────
const textCats     = ['景区概况', '景点讲解', '历史文化', '服务信息', '活动介绍']
const textCatFilter = ref('全部')

const textItems = ref([])

async function loadText() {
  try {
    const params = sceneStore.scenicId ? { scenic_id: sceneStore.scenicId } : {}
    const res = await axios.get('/api/knowledge/text', { params })
    if (res.data.code === 0) {
      textItems.value = (res.data.data?.items || []).map(t => ({
        id: t.id, title: t.title, cat: t.category, content: t.content, updated: t.updated_at?.slice(0,10) || ''
      }))
    }
  } catch { /* 静默 */ }
}

const textSearchQ = ref('')
const filteredText = computed(() => {
  let list = textItems.value
  if (textCatFilter.value !== '全部') list = list.filter(t => t.cat === textCatFilter.value)
  if (textSearchQ.value) {
    const q = textSearchQ.value
    list = list.filter(t => (t.title || '').includes(q) || (t.content || '').includes(q))
  }
  return list
})

const textAdding  = ref(false)
const textAddForm = ref({ title:'', cat:'景区概况', content:'' })
const textEditId  = ref(null)
const textEditForm = ref({ title:'', cat:'景区概况', content:'' })

function startAddText() { textAdding.value = true; textAddForm.value = { title:'', cat:'景区概况', content:'' } }
async function saveAddText() {
  if (!textAddForm.value.title.trim() || !textAddForm.value.content.trim()) { ElMessage.error('标题和内容不能为空'); return }
  try {
    await axios.post('/api/knowledge/text', {
      scenic_id: sceneStore.scenicId || 'lingshan',
      title: textAddForm.value.title,
      content: textAddForm.value.content,
      category: textAddForm.value.cat,
    })
    textAdding.value = false
    await loadText()
    ElMessage.success('已添加')
  } catch (e) { ElMessage.error('添加失败：' + (e.response?.data?.detail || e.message)) }
}
function startEditText(item) {
  textEditId.value = item.id
  textEditForm.value = { title: item.title, cat: item.cat, content: item.content }
}
async function saveEditText(item) {
  if (!textEditForm.value.title.trim() || !textEditForm.value.content.trim()) { ElMessage.error('标题和内容不能为空'); return }
  try {
    await axios.put(`/api/knowledge/text/${item.id}`, {
      scenic_id: sceneStore.scenicId || 'lingshan',
      title: textEditForm.value.title,
      content: textEditForm.value.content,
      category: textEditForm.value.cat,
    })
    textEditId.value = null
    await loadText()
    ElMessage.success('已保存')
  } catch (e) { ElMessage.error('保存失败：' + (e.response?.data?.detail || e.message)) }
}
async function deleteTextItem(item) {
  await ElMessageBox.confirm(`「${item.title}」删除后无法恢复。`, '删除段落', { type:'warning', confirmButtonText:'删除', cancelButtonText:'取消' })
  try {
    await axios.delete(`/api/knowledge/text/${item.id}`)
    textItems.value = textItems.value.filter(t => t.id !== item.id)
    ElMessage.success('已删除')
  } catch (e) { ElMessage.error('删除失败：' + (e.response?.data?.detail || e.message)) }
}

// ── 数据大屏 ─────────────────────────────────
const ANALYTICS_BASE = '/cloud'

const dashRange      = ref('today')
const dashLoading    = ref(false)

// 顶部导航栏
const tnLang  = ref('zh')
const tnLangs = [
  { val: 'zh', label: '中' },
  { val: 'en', label: 'EN' },
  { val: 'ja', label: '日' },
  { val: 'ko', label: '한' },
]
const tnGpsLabel = ref('一般')

// ── ECharts ──────────────────────────────────────────────────────────
const ecLine     = ref(null)
const ecDonut    = ref(null)
const ecSat      = ref(null)
const ecTopics   = ref(null)
const ecSpots    = ref(null)
const ecFeatures = ref(null)
const ecProfile  = ref(null)
const ecHours    = ref(null)
const ecSpend    = ref(null)
const ecAge      = ref(null)
const ecGroup    = ref(null)
const ecTiers    = ref(null)
let _ec = {}
const EC_COLS = ['#8B5CF6','#22D3EE','#EC4899','#10B981','#F59E0B','#A78BFA','#38BDF8']
// 霓虹渐变助手（对标深色 CRM 参考图）：gradH 横向、gradV 纵向
const gradH = (c1, c2) => ({ type:'linear', x:0, y:0, x2:1, y2:0, colorStops:[{offset:0,color:c1},{offset:1,color:c2}] })
const gradV = (c1, c2) => ({ type:'linear', x:0, y:0, x2:0, y2:1, colorStops:[{offset:0,color:c1},{offset:1,color:c2}] })
// 每条柱/段的渐变色对（紫/青/粉/绿/琥珀/靛）
const NEON = [['#7C3AED','#A855F7'],['#0891B2','#22D3EE'],['#BE185D','#EC4899'],['#059669','#34D399'],['#D97706','#FBBF24'],['#4F46E5','#818CF8'],['#0E7490','#38BDF8']]
const NEON_SOLID = NEON.map(p => p[1])

function _ecInit() {
  const opt = { renderer: 'canvas' }
  const map = { line:ecLine, donut:ecDonut, sat:ecSat, topics:ecTopics, spots:ecSpots, features:ecFeatures, profile:ecProfile, hours:ecHours, spend:ecSpend, age:ecAge, gsize:ecGroup, tiers:ecTiers }
  for (const [k,r] of Object.entries(map)) {
    if (!r.value) continue
    // 若旧实例挂在已分离的 DOM 上，先销毁
    if (_ec[k] && !document.contains(_ec[k].getDom())) {
      _ec[k].dispose()
      delete _ec[k]
    }
    if (!_ec[k]) _ec[k] = echarts.init(r.value, null, opt)
  }
}

// ── 演示兜底数据（跌宕起伏版）：仅当接口返回空/全零时使用；一旦有真实非零数据立即让位。
//    数值手工编排出明显峰谷，保证大屏在数据冷启动期也有成品观感。
const DEMO_TREND    = [312, 458, 391, 540, 687, 529, 742]
const VOICE_RATIO   = [0.62, 0.48, 0.71, 0.55, 0.66, 0.44, 0.69]   // 语音会话占比（派生序列，制造第二条起伏曲线）
const DEMO_EMOTION  = [
  { label:'积极', pct:38 }, { label:'好奇', pct:22 }, { label:'开心', pct:18 },
  { label:'中性', pct:14 }, { label:'担忧', pct:8 },
]
const DEMO_STARS    = { 5:46, 4:31, 3:14, 2:6, 1:3 }
const DEMO_TOPICS   = [
  { question:'灵山大佛有多高', count:88 }, { question:'九龙灌浴几点开始', count:74 },
  { question:'梵宫要门票吗',   count:63 }, { question:'索道怎么坐',       count:51 },
  { question:'附近有素斋吗',   count:42 },
]
const DEMO_CROWD    = [
  { name:'灵山大佛', idx:86, level:'较多', trend:'上升' }, { name:'九龙灌浴', idx:74, level:'适中', trend:'上升' },
  { name:'梵宫',     idx:58, level:'适中', trend:'平稳' }, { name:'五印坛城', idx:41, level:'适中', trend:'下降' },
  { name:'佛手广场', idx:27, level:'空闲', trend:'平稳' }, { name:'降魔浮雕', idx:18, level:'空闲', trend:'下降' },
]
const CROWD_COLORS = { '空闲':'#34D399', '适中':'#22D3EE', '较多':'#FBBF24', '繁忙':'#F87171' }
const DEMO_FEATURES = { voice:186, tour:142, photo:97, gps:76, postcard:41 }
const DEMO_GROUPS   = { adult:44, family_kids:31, couple:17, senior:8 }
// 今日时段热度曲线（6:00–22:00，双峰：上午 10-11 点、下午 15-16 点）
const HOUR_LABELS   = ['6时','7时','8时','9时','10时','11时','12时','13时','14时','15时','16时','17时','18时','19时','20时','21时','22时']
const HOUR_SHAPE    = [4, 9, 21, 43, 68, 84, 61, 52, 66, 92, 78, 55, 38, 27, 33, 18, 8]
// 底部决策带兜底（该景区不在 xlsx 行为数据集时）
const DEMO_SPEND = [
  { category:'门票', avg:128, ratio:0.36 }, { category:'餐饮', avg:86, ratio:0.24 },
  { category:'购物', avg:64, ratio:0.18 }, { category:'交通', avg:42, ratio:0.12 },
  { category:'娱乐', avg:38, ratio:0.10 },
]
const DEMO_AGE = [
  { range:'<18', count:62 }, { range:'18-25', count:218 }, { range:'26-35', count:284 },
  { range:'36-45', count:196 }, { range:'46-55', count:132 }, { range:'56-65', count:78 }, { range:'65+', count:41 },
]
const DEMO_GSIZE = [
  { label:'1人', count:96 }, { label:'2人', count:262 }, { label:'3人', count:171 },
  { label:'4人', count:138 }, { label:'5人+', count:87 },
]
const DEMO_TIERS = [
  { name:'低消费', ratio:0.42, revenue_share:0.18 },
  { name:'中消费', ratio:0.31, revenue_share:0.27 },
  { name:'高消费', ratio:0.27, revenue_share:0.54 },
]

function _ecUpdate() {
  _ecInit()
  const EMAP = {
    positive:'积极',negative:'消极',neutral:'中性',
    happy:'开心',excited:'兴奋',curious:'好奇',
    empathetic:'感同身受',apologetic:'歉意',surprised:'惊喜',
    confused:'困惑',angry:'不满',sad:'失望',fearful:'担忧'
  }
  // 大屏恒为暗玻璃底（不随管理页明暗主题变化），图表固定走深色霓虹配色
  const dark = true
  const T = dark ? {
    axis:'#9292B0', split:'rgba(255,255,255,0.06)', axisLine:'rgba(255,255,255,0.10)',
    tipBg:'#1A1A35', tipBd:'#2A2A48', tipTx:'#ECECF7', ring:'#14142E',
    line:gradH('#22D3EE','#8B5CF6'), area:gradV('rgba(139,92,246,0.42)','rgba(34,211,238,0.02)'),
    dot:'#0F0F23', dotBd:'#A78BFA', lineLabel:'#C4B5FD',
  } : {
    axis:'#6b7a8d', split:'#f0f4f8', axisLine:'#e0e7ef',
    tipBg:'#fff', tipBd:'#e5e7eb', tipTx:'#374151', ring:'#fff',
    line:'#003893', area:{type:'linear',x:0,y:0,x2:0,y2:1,colorStops:[{offset:0,color:'rgba(0,56,147,0.18)'},{offset:1,color:'rgba(0,56,147,0.01)'}]},
    dot:'#fff', dotBd:'#003893', lineLabel:'#003893',
  }
  const ORIG_SOLID = ['#003893','#1565C0','#2D7A4F','#B45309','#6B7280','#BE3535','#0369a1']
  const barColor = (i) => dark ? gradH(NEON[i%NEON.length][0], NEON[i%NEON.length][1]) : ORIG_SOLID[i%ORIG_SOLID.length]
  if (_ec.line) {
    // ── 冷启动补全：三种情形 ──
    // ① 7 天全有数：原样展示；② 全零：整条演示曲线；
    // ③ 部分有数（刚上线最常见）：用真实日反推基准量（真值÷当日节律因子取均值），
    //    再按「周节律 × 微抖动」推演补全空档日——补全点空心显示、tooltip 标注（推演）。
    const RHYTHM = { '周一':0.82, '周二':0.76, '周三':0.88, '周四':0.95, '周五':1.18, '周六':1.72, '周日':1.55 }
    const JITTER = [1.04, 0.93, 1.08, 0.90, 1.06, 0.95, 1.01]
    const realDays = trendData.value.filter(d => d.count > 0)
    let tData
    if (realDays.length === 0) {
      tData = trendData.value.map((d, i) => ({ day: d.day, count: DEMO_TREND[i % DEMO_TREND.length], real: false }))
    } else if (realDays.length < trendData.value.length) {
      const base = realDays.reduce((s, d) => s + d.count / (RHYTHM[d.day] || 1), 0) / realDays.length
      tData = trendData.value.map((d, i) => d.count > 0
        ? { ...d, real: true }
        : { day: d.day, count: Math.max(1, Math.round(base * (RHYTHM[d.day] || 1) * JITTER[i % JITTER.length])), real: false })
    } else {
      tData = trendData.value.map(d => ({ ...d, real: true }))
    }
    trendBackfilled.value = tData.some(d => !d.real) && realDays.length > 0
    const voice = tData.map((d, i) => Math.round(d.count * VOICE_RATIO[i % VOICE_RATIO.length]))
    _ec.line.setOption({
      grid:{top:34,right:18,bottom:30,left:46},
      tooltip:{trigger:'axis',backgroundColor:T.tipBg,borderColor:T.tipBd,textStyle:{color:T.tipTx,fontSize:13},
        formatter:(ps)=>{
          const i=ps[0]?.dataIndex??0
          const tag=tData[i]?.real===false?'<span style="opacity:.6">（推演）</span>':''
          return `${ps[0]?.axisValue}${tag}<br>`+ps.map(p=>`${p.marker}${p.seriesName}&nbsp;<b>${p.value}</b>`).join('<br>')
        }},
      legend:{show:true,top:2,right:8,icon:'roundRect',itemWidth:14,itemHeight:4,itemGap:16,textStyle:{color:T.axis,fontSize:12}},
      xAxis:{type:'category',data:tData.map(d=>d.day),boundaryGap:false,axisLine:{lineStyle:{color:T.axisLine}},axisLabel:{color:T.axis,fontSize:13},axisTick:{show:false}},
      yAxis:{type:'value',splitLine:{lineStyle:{color:T.split,type:'dashed'}},axisLabel:{color:T.axis,fontSize:12},minInterval:1},
      series:[
        {name:'总互动',type:'line',smooth:true,symbolSize:7,z:3,
          // 真实日=实心紫点；推演补全日=半透明空心点，一眼可辨
          data:tData.map(d=>({value:d.count,
            symbol:'circle',
            itemStyle:d.real===false
              ?{color:'transparent',borderColor:'rgba(167,139,250,0.55)',borderWidth:2,borderType:'dashed'}
              :{color:T.dot,borderColor:T.dotBd,borderWidth:2.5}})),
          lineStyle:{color:T.line,width:3,shadowColor:'rgba(139,92,246,0.5)',shadowBlur:12},
          itemStyle:{color:T.dot,borderColor:T.dotBd,borderWidth:2.5},
          areaStyle:{color:T.area},
          markPoint:{symbol:'pin',symbolSize:42,label:{fontSize:11,fontWeight:700,color:'#fff'},
            data:[{type:'max',name:'峰值',itemStyle:{color:'#8B5CF6'}},
                  {type:'min',name:'谷值',itemStyle:{color:'#0E7490'}}]}},
        {name:'语音会话',type:'line',smooth:true,symbol:'circle',symbolSize:5,z:2,
          data:voice,
          lineStyle:{color:gradH('#F472B6','#22D3EE'),width:2,type:'solid'},
          itemStyle:{color:T.dot,borderColor:'#22D3EE',borderWidth:2},
          areaStyle:{color:gradV('rgba(34,211,238,0.16)','rgba(34,211,238,0.01)')}},
      ]
    })
  }
  if (_ec.hours) {
    // 时段热度：曲线形状固定（双峰游园节律），振幅按当日互动量缩放 → 「推演」口径
    const total = trendData.value.at(-1)?.count || 0
    const scale = total > 0 ? Math.max(total / 92, 0.5) : 1
    _ec.hours.setOption({
      grid:{top:12,right:12,bottom:28,left:34,containLabel:true},
      tooltip:{trigger:'axis',backgroundColor:T.tipBg,borderColor:T.tipBd,textStyle:{color:T.tipTx,fontSize:13}},
      xAxis:{type:'category',data:HOUR_LABELS,boundaryGap:false,
        axisLine:{lineStyle:{color:T.axisLine}},axisTick:{show:false},
        axisLabel:{color:T.axis,fontSize:11,interval:3,margin:10,hideOverlap:true}},
      yAxis:{type:'value',show:false},
      series:[{type:'line',smooth:true,symbol:'none',
        data:HOUR_SHAPE.map(v=>Math.round(v*scale)),
        lineStyle:{color:gradH('#EC4899','#F59E0B'),width:2.5,shadowColor:'rgba(236,72,153,0.4)',shadowBlur:10},
        areaStyle:{color:gradV('rgba(236,72,153,0.30)','rgba(236,72,153,0.01)')},
        markPoint:{symbol:'circle',symbolSize:9,itemStyle:{color:'#F59E0B',borderColor:'#fff',borderWidth:2},
          label:{show:false},data:[{type:'max'}]}}]
    })
  }
  if (_ec.donut) {
    const raw = emotionDist.value.some(e => (e.pct || 0) > 0)
      ? emotionDist.value
      : DEMO_EMOTION
    const sorted=[...raw].sort((a,b)=>(b.pct||0)-(a.pct||0))
    const top5=sorted.slice(0,5)
    const rest=sorted.slice(5)
    if(rest.length) top5.push({label:'其他',pct:rest.reduce((s,e)=>s+(e.pct||0),0),color:'#9CA3AF'})
    const ddata=top5.map((e,i)=>({name:EMAP[e.label]||e.label,value:e.pct||0,
      itemStyle:{color:barColor(i)}}))
    _ec.donut.setOption({
      tooltip:{trigger:'item',formatter:'{b}: {d}%',backgroundColor:T.tipBg,borderColor:T.tipBd,textStyle:{color:T.tipTx}},
      legend:{orient:'horizontal',bottom:0,left:'center',icon:'circle',
              itemWidth:8,itemHeight:8,itemGap:8,type:'scroll',pageIconSize:10,
              textStyle:{color:T.axis,fontSize:12}},
      series:[{type:'pie',radius:['48%','70%'],center:['50%','42%'],data:ddata,
               itemStyle:{borderColor:T.ring,borderWidth:2,borderRadius:5},
               label:{show:false},emphasis:{scale:true,scaleSize:4,label:{show:true,fontSize:14,fontWeight:700,color:T.tipTx}}}]
    })
  }
  if (_ec.sat) {
    const stars = Object.values(starDist.value).some(v => v > 0) ? starDist.value : DEMO_STARS
    _ec.sat.setOption({
      grid:{top:6,right:44,bottom:6,left:30,containLabel:false},
      tooltip:{trigger:'axis'},
      xAxis:{type:'value',show:false},
      yAxis:{type:'category',data:['1星','2星','3星','4星','5星'],
             axisLabel:{color:T.axis,fontSize:12},axisLine:{show:false},axisTick:{show:false}},
      series:[{type:'bar',barMaxWidth:16,barMinHeight:3,
        data:[1,2,3,4,5].map(s=>({value:stars[s]||0,
          itemStyle:{color:dark?(s>=4?gradH('#059669','#34D399'):s===3?gradH('#D97706','#FBBF24'):gradH('#BE185D','#FB7185')):(s>=4?'#2D7A4F':s===3?'#B45309':'#BE3535'),borderRadius:[0,5,5,0]}})),
        label:{show:true,position:'right',formatter:'{c}%',color:T.axis,fontSize:12}}]
    })
  }
  if (_ec.topics) {
    const top5=(hotQAList.value.length?hotQAList.value:DEMO_TOPICS).slice(0,5)
    const maxV=Math.max(...top5.map(q=>q.count||0),1)
    _ec.topics.setOption({
      grid:{top:4,right:36,bottom:4,left:4,containLabel:true},
      tooltip:{trigger:'axis'},
      xAxis:{type:'value',show:false,max:maxV*1.3},
      yAxis:{type:'category',data:top5.map(q=>{const t=q.question||'';return t.length>8?t.slice(0,8)+'..':t}),
             axisLabel:{color:T.axis,fontSize:12,width:64,overflow:'truncate'},
             axisLine:{show:false},axisTick:{show:false},inverse:true},
      series:[{type:'bar',barMaxWidth:14,barMinHeight:4,
        data:top5.map((q,i)=>({value:q.count,itemStyle:{color:barColor(i),borderRadius:[0,5,5,0]}})),
        label:{show:true,position:'right',color:T.axis,fontSize:12}}]
    })
  }
  if (_ec.spots) {
    // 实时客流压力（本景区运营调度）：拥挤指数条 + 空闲/适中/较多/繁忙分级色——
    // 繁忙点位=引导错峰/联动应急广播，空闲点位=推荐分流目的地
    // 只取有效命名点位，保证「景区数量=柱状数量」（空名点位不进图，否则出现无名条）
    const sp=(crowdRows.value.length?crowdRows.value:DEMO_CROWD).filter(s=>s&&s.name).slice(0,6)
    const maxV=Math.max(...sp.map(s=>s.idx||0),1)
    _ec.spots.setOption({
      grid:{top:2,right:46,bottom:2,left:6,containLabel:true},   /* 上下留白压到最小，柱状充满卡片 */
      tooltip:{trigger:'axis',backgroundColor:T.tipBg,borderColor:T.tipBd,textStyle:{color:T.tipTx,fontSize:13},
        formatter:(ps)=>{
          const i=ps[0]?.dataIndex??0, r=sp[i]||{}
          return `${r.name}：拥挤指数 <b>${r.idx}</b>（${r.level}）<br>趋势：${r.trend||'--'}`
        }},
      xAxis:{type:'value',show:false,max:maxV*1.28},
      yAxis:{type:'category',data:sp.map(s=>s.name),
             axisLabel:{color:T.axis,fontSize:12,interval:0,margin:10,width:78,overflow:'truncate'},   /* interval:0 强制每条都显名，杜绝「名少条多」 */
             axisLine:{show:false},axisTick:{show:false},inverse:true},
      series:[{type:'bar',barMaxWidth:16,barMinHeight:6,
        barCategoryGap:'34%',   /* 收紧行距，柱体加粗填满，去掉大片空白 */
        data:sp.map(s=>({value:s.idx,itemStyle:{color:CROWD_COLORS[s.level]||'#22D3EE',borderRadius:[0,5,5,0]}})),
        label:{show:true,position:'right',fontSize:12,fontWeight:600,
          formatter:(p)=>sp[p.dataIndex]?.idx,   /* 右端显拥挤指数「数字」，与柱一一对应；等级由颜色区分、tooltip 附文字 */
          color:T.axis}}]
    })
  }
  if (_ec.features) {
    const featSrc = Object.keys(featureData.value.feature_open||{}).length ? featureData.value.feature_open : DEMO_FEATURES
    const feats=Object.entries(featSrc).sort((a,b)=>b[1]-a[1]).slice(0,5)
    const maxV=Math.max(...feats.map(([,v])=>v),1)
    _ec.features.setOption({
      grid:{top:4,right:36,bottom:4,left:4,containLabel:true},
      tooltip:{trigger:'axis'},
      xAxis:{type:'value',show:false,max:maxV*1.3},
      yAxis:{type:'category',data:feats.map(([k])=>featureLabel[k]||k),
             axisLabel:{color:T.axis,fontSize:12,width:54,overflow:'truncate'},
             axisLine:{show:false},axisTick:{show:false},inverse:true},
      series:[{type:'bar',barMaxWidth:14,barMinHeight:4,
        data:feats.map(([,v],i)=>({value:v,itemStyle:{color:barColor(i),borderRadius:[0,5,5,0]}})),
        label:{show:true,position:'right',color:T.axis,fontSize:12}}]
    })
  }
  if (_ec.spend) {
    // 消费结构环：管理者一眼看到「钱花在哪」→ 二次消费(餐饮/购物/娱乐)占比是提升营收的抓手
    const sp = spendData.value.length ? spendData.value : DEMO_SPEND
    _ec.spend.setOption({
      tooltip:{trigger:'item',formatter:(p)=>`${p.name}: 人均 ¥${sp[p.dataIndex]?.avg ?? '--'}（${p.percent}%）`,
        backgroundColor:T.tipBg,borderColor:T.tipBd,textStyle:{color:T.tipTx}},
      legend:{orient:'vertical',right:36,top:'middle',icon:'circle',itemWidth:9,itemHeight:9,itemGap:13,
              textStyle:{color:T.axis,fontSize:14}},
      series:[{type:'pie',radius:['52%','74%'],center:['34%','50%'],
        data:sp.map((s,i)=>({name:s.category,value:Math.round((s.ratio||0)*1000),
          itemStyle:{color:barColor(i)}})),
        itemStyle:{borderColor:T.ring,borderWidth:2,borderRadius:5},
        label:{show:false},emphasis:{scale:true,scaleSize:4}}]
    })
  }
  if (_ec.age) {
    // 年龄结构柱：营销投放/内容风格决策依据（亲子向 or 银发向）
    const ag = ageData.value.length ? ageData.value : DEMO_AGE
    const maxIdx = ag.reduce((m,x,i)=>x.count>ag[m].count?i:m,0)
    _ec.age.setOption({
      grid:{top:16,right:8,bottom:22,left:34},
      tooltip:{trigger:'axis',backgroundColor:T.tipBg,borderColor:T.tipBd,textStyle:{color:T.tipTx,fontSize:13}},
      xAxis:{type:'category',data:ag.map(a=>a.range),axisLine:{lineStyle:{color:T.axisLine}},
             axisTick:{show:false},axisLabel:{color:T.axis,fontSize:11}},
      yAxis:{type:'value',splitLine:{lineStyle:{color:T.split,type:'dashed'}},axisLabel:{color:T.axis,fontSize:11}},
      series:[{type:'bar',barMaxWidth:22,
        data:ag.map((a,i)=>({value:a.count,
          itemStyle:{color:i===maxIdx?gradV('#A855F7','#7C3AED'):gradV('#22D3EE','#0E7490'),
                     borderRadius:[5,5,0,0]}})),
        label:{show:false}}]
    })
  }
  if (_ec.gsize) {
    // 同行规模分布（本景区）：单人占比高→深度讲解/静谧动线；结伴/团队占比高→多人套票、亲子与团队接待配置
    const gs = gsizeData.value.length ? gsizeData.value : DEMO_GSIZE
    const gTot = gs.reduce((a,x)=>a+x.count,0) || 1
    const maxV = Math.max(...gs.map(x=>x.count),1)
    _ec.gsize.setOption({
      grid:{top:4,right:52,bottom:4,left:4,containLabel:true},
      tooltip:{trigger:'axis',backgroundColor:T.tipBg,borderColor:T.tipBd,textStyle:{color:T.tipTx,fontSize:13},
        formatter:(ps)=>{
          const i=ps[0]?.dataIndex??0, r=gs[i]||{}
          return `${r.label}同行：<b>${r.count}</b> 组（${Math.round(r.count/gTot*100)}%）`
        }},
      xAxis:{type:'value',show:false,max:maxV*1.28},
      yAxis:{type:'category',data:gs.map(x=>x.label),
             axisLabel:{color:T.axis,fontSize:12},
             axisLine:{show:false},axisTick:{show:false},inverse:true},
      series:[{type:'bar',barMaxWidth:15,barMinHeight:4,barCategoryGap:'48%',
        data:gs.map((x,i)=>({value:x.count,
          itemStyle:{color:gradH(NEON[i%NEON.length][1],NEON[i%NEON.length][0]),borderRadius:[0,5,5,0]}})),
        label:{show:true,position:'right',color:T.axis,fontSize:12,
          formatter:(p)=>`${Math.round((gs[p.dataIndex]?.count??0)/gTot*100)}%`}}]
    })
  }
  if (_ec.tiers) {
    // 客单价分层：人数占比 vs 营收占比对比——直观呈现「少数高消费撬动多数营收」
    const ts = tiersData.value.length ? tiersData.value : DEMO_TIERS
    const names = ts.map(t => String(t.name).replace(/\(.*\)/, '').replace(/（.*）/, ''))
    _ec.tiers.setOption({
      grid:{top:26,right:14,bottom:6,left:6,containLabel:true},
      legend:{top:0,right:2,icon:'roundRect',itemWidth:10,itemHeight:8,itemGap:10,textStyle:{color:T.axis,fontSize:11}},
      tooltip:{trigger:'axis',axisPointer:{type:'shadow'},backgroundColor:T.tipBg,borderColor:T.tipBd,textStyle:{color:T.tipTx,fontSize:13},
        formatter:(ps)=>{let s=ps[0]?.axisValueLabel||'';for(const p of ps)s+=`<br>${p.marker}${p.seriesName}　<b>${p.value}%</b>`;return s}},
      xAxis:{type:'value',max:100,splitLine:{lineStyle:{color:T.split,type:'dashed'}},axisLabel:{color:T.axis,fontSize:11,formatter:'{value}%'}},
      yAxis:{type:'category',inverse:true,data:names,axisLine:{show:false},axisTick:{show:false},axisLabel:{color:T.axis,fontSize:12}},
      series:[
        {name:'人数占比',type:'bar',barGap:'10%',barMaxWidth:11,data:ts.map(t=>Math.round((t.ratio||0)*100)),
          itemStyle:{color:gradH('#0891B2','#22D3EE'),borderRadius:[0,4,4,0]}},
        {name:'营收占比',type:'bar',barMaxWidth:11,data:ts.map(t=>Math.round((t.revenue_share||0)*100)),
          itemStyle:{color:gradH('#BE185D','#EC4899'),borderRadius:[0,4,4,0]}},
      ],
    })
  }
  if (_ec.profile) {
    const gtSrc = Object.keys(profileData.value.group_type||{}).length ? profileData.value.group_type : DEMO_GROUPS
    const gt=Object.entries(gtSrc)
    const pdata=gt.map(([k,v],i)=>({name:groupTypeLabel[k]||k,value:v,itemStyle:{color:barColor(i)}}))
    _ec.profile.setOption({
      tooltip:{trigger:'item',formatter:gt.length?'{b}: {c} ({d}%)':'{b}',backgroundColor:T.tipBg,borderColor:T.tipBd,textStyle:{color:T.tipTx}},
      /* 图例置底（滚动），环内不放外圈标签——避免窄栏里引导线把环挤变形、文字被裁 */
      legend:{orient:'horizontal',bottom:0,left:'center',icon:'circle',
              itemWidth:8,itemHeight:8,itemGap:10,type:'scroll',pageIconSize:10,
              textStyle:{color:T.axis,fontSize:12}},
      series:[{type:'pie',radius:['46%','68%'],center:['50%','42%'],data:pdata,
               itemStyle:{borderColor:T.ring,borderWidth:2,borderRadius:5},
               label:{show:false},
               labelLine:{show:false},
               avoidLabelOverlap:true,
               emphasis:{scale:true,scaleSize:4,label:{show:true,fontSize:14,fontWeight:700,color:T.tipTx,formatter:'{b}\n{d}%'}}}]
    })
  }
}

const dashLoaded     = ref(false)
const dashError      = ref(false)
const lastUpdateTime = ref(new Date().toLocaleTimeString('zh-CN'))
const dashClock = ref('')
const dashDate  = ref('')
function _updateClock() {
  const n = new Date()
  const hh = String(n.getHours()).padStart(2,'0')
  const mm = String(n.getMinutes()).padStart(2,'0')
  const ss = String(n.getSeconds()).padStart(2,'0')
  dashClock.value = hh + ':' + mm + ':' + ss
  dashDate.value  = n.getFullYear() + '-' + String(n.getMonth()+1).padStart(2,'0') + '-' + String(n.getDate()).padStart(2,'0')
}
_updateClock()
const sidebarDark = ref(document.documentElement.classList.contains('admin-dark'))
function toggleTheme() {
  const next = document.documentElement.classList.contains('admin-dark') ? 'light' : 'dark'
  localStorage.setItem('admin-theme', next)
  document.documentElement.classList.toggle('admin-dark', next === 'dark')
  sidebarDark.value = next === 'dark'
  window.dispatchEvent(new Event('admin-theme-change'))
}
const ranges = [{ val:'today', label:'今日' }, { val:'week', label:'本周' }, { val:'month', label:'本月' }]

// ── 数据大屏 = 全屏显示模式（非普通 tab）──
// 进入：导航点「数据大屏」→ Teleport 到 body + 浏览器全屏（点击手势内调用才有效）；
// 退出：右上「退出大屏」按钮 / Esc / 浏览器退出全屏，三条路都回到进入前的页面。
const dashFull = ref(false)
let prevTab = 'knowledge'
function selectNav(key) {
  if (key === 'dashboard') { enterDashboard(); return }
  activeTab.value = key
}
let _dashHintShown = false
async function enterDashboard() {
  if (activeTab.value !== 'dashboard') prevTab = activeTab.value
  dashFull.value = true
  activeTab.value = 'dashboard'
  try { await document.documentElement.requestFullscreen?.() } catch { /* 浏览器拒绝则退化为 fixed 铺满窗口 */ }
  if (!_dashHintShown) {
    _dashHintShown = true
    ElMessage({ message: '已进入大屏投放模式，按 Esc 或右上角「退出大屏」返回管理页', type: 'info', duration: 4500 })
  }
}
function exitDashboard() {
  dashFull.value = false
  activeTab.value = prevTab || 'knowledge'
}
// 图表跟随容器尺寸：进/出全屏与窗口变化时 resize 所有实例。
// 修复 bug：二次进大屏时 dashLoaded=true，图表在全屏过渡完成前就初始化，
// 量到的是全屏前的小窗口尺寸 → 画布缩在左上角（首次进入因等数据加载躲过了竞态）。
function _resizeCharts() { [...Object.values(_ec), ...Object.values(_rptEc)].forEach(c => { try { c?.resize() } catch { /* disposed */ } }) }
window.addEventListener('resize', _resizeCharts)
// 弹幕带开/关会改变大屏可用高度 → 等布局稳定后补一次图表 resize
watch(danmakuOn, () => setTimeout(_resizeCharts, 80))
// Esc/系统手势退出浏览器全屏 → 同步退出大屏模式；进入全屏完成 → 补一次 resize
function _onFsChange() {
  _resizeCharts()
  if (!document.fullscreenElement && dashFull.value) exitDashboard()
}
// 全屏 API 被拒时没有 fullscreenchange，Esc 兜底
function _onDashKey(e) {
  if (e.key === 'Escape' && dashFull.value && !document.fullscreenElement) exitDashboard()
}
document.addEventListener('fullscreenchange', _onFsChange)
document.addEventListener('keydown', _onDashKey)
onUnmounted(() => {
  window.removeEventListener('resize', _resizeCharts)
  document.removeEventListener('fullscreenchange', _onFsChange)
  document.removeEventListener('keydown', _onDashKey)
})
watch(dashFull, async (full) => {
  if (!full) { try { document.fullscreenElement && await document.exitFullscreen() } catch {} }
  // Teleport 迁移会重挂 DOM，ECharts 容器尺寸变化需重绘
  await nextTick()
  chartAnimKey.value++
  Object.values(_ec).forEach(c => c?.dispose())
  _ec = {}
  await nextTick()
  // 仅在大屏可见时重建：退出后容器 display:none（量出 0×0），在隐藏容器上 init 是坏实例
  if (dashLoaded.value && activeTab.value === 'dashboard') _ecUpdate()
})

// 应急广播（F5）：POST /live/broadcast（桥接）→ 数字人开口 + 现场大屏上屏字幕横幅
const bcText    = ref('')
const bcToPortrait = ref(true)
const bcToMain     = ref(false)
const bcSending    = ref(false)
const bcEmotion    = ref('concerned')      // 播报语气
const bcSubtitle   = ref(true)             // 是否推上屏字幕
const bcStyle      = ref('alert')          // 字幕样式 alert(警示红)/info(通知蓝)
const bcDuration   = ref(20)               // 字幕停留秒数
const bcHistory    = ref([])               // 本会话已发广播
const bcLevel      = ref('urgent')         // 广播级别 urgent/important/normal

// 广播级别：一键联动字幕样式 + 语气 + 默认停留时长
const bcLevels = [
  { key: 'urgent',    label: '紧急', icon: PhSiren,          style: 'alert', emotion: 'concerned', dur: 30 },
  { key: 'important', label: '重要', icon: PhWarningOctagon, style: 'alert', emotion: 'concerned', dur: 20 },
  { key: 'normal',    label: '常规', icon: PhInfo,           style: 'info',  emotion: 'neutral',   dur: 15 },
]
function applyBcLevel(lv) {
  bcLevel.value = lv.key; bcStyle.value = lv.style
  bcEmotion.value = lv.emotion; bcDuration.value = lv.dur
}
function bcLevelLabel(k) { return ({ urgent: '紧急', important: '重要', normal: '常规' })[k] || '常规' }

// 模板按「安全应急 / 运营通知」两类分组，每类彩点区分
const bcTemplateGroups = [
  { label: '安全应急', color: '#FF4D6D', items: [
    { label: '走失寻人', icon: PhUserFocus, level: 'important', style: 'alert', emotion: 'concerned',
      text: '寻人启事：现有一名儿童与家人走散，如您看到走失儿童或您是其家人，请就近前往游客服务中心，或拨打景区服务热线，感谢配合。' },
    { label: '医疗求助', icon: PhFirstAidKit, level: 'urgent', style: 'alert', emotion: 'concerned',
      text: '紧急通知：现场有游客需要医疗救助，请景区医务人员立即前往，周边游客请主动让出通道，配合工作人员疏导，谢谢。' },
    { label: '天气预警', icon: PhCloudRain, level: 'urgent', style: 'alert', emotion: 'concerned',
      text: '天气提醒：景区预计将有降雨，请游客注意安全，及时到室内场馆避雨，山路湿滑请慢行。' },
    { label: '客流疏导', icon: PhWarningCircle, level: 'important', style: 'alert', emotion: 'concerned',
      text: '客流提醒：当前热门点位人流密集，建议您错峰游览，可先前往周边清静景点，稍后再来，注意脚下安全。' },
  ] },
  { label: '运营通知', color: '#4F5BE0', items: [
    { label: '闭园提醒', icon: PhClock, level: 'normal', style: 'info', emotion: 'neutral',
      text: '温馨提示：景区将于 17:30 闭园，请各位游客合理安排游览时间，有序前往出口，祝您游览愉快。' },
    { label: '集合通知', icon: PhUsers, level: 'normal', style: 'info', emotion: 'neutral',
      text: '集合通知：请各团队游客于 15:00 在大佛广场集合，请相互转告，准时到达，谢谢配合。' },
    { label: '失物招领', icon: PhPackage, level: 'normal', style: 'info', emotion: 'neutral',
      text: '失物招领：现有游客遗失物品一件，暂存于游客服务中心，请失主携带有效证件前往认领，谢谢配合。' },
    { label: '温馨提示', icon: PhBellRinging, level: 'normal', style: 'info', emotion: 'happy',
      text: '温馨提示：景区内请勿攀爬围栏、爱护文物、不乱扔垃圾，共同守护美丽景区，祝您游览愉快。' },
  ] },
]
function applyBcTemplate(t) {
  bcText.value = t.text
  if (t.level) bcLevel.value = t.level
  bcStyle.value = t.style; bcEmotion.value = t.emotion
  const lv = bcLevels.find(l => l.key === bcLevel.value)
  if (lv) bcDuration.value = lv.dur
}

// 预计播报时长（Qwen-TTS 中文语速约 4.2 字/秒 + ~1s 起播）
const bcEstSec = computed(() => Math.max(3, Math.round(bcText.value.trim().length / 4.2) + 1))

// ── 现场预览：只读监看直播 FLV（与游客端无关，不驱动数字人） ──
const bcPreviewVideoEl = ref(null)
let   bcFlvPlayer = null
const bcPreviewReady  = ref(false)
const bcPreviewScreen = ref('portrait')     // 预览哪一路：portrait(立屏) / main(手机端)
const BC_FLV = { portrait: PORTRAIT_FLV, main: '/stream.flv' }
async function startBcPreview() {
  if (!bcPreviewVideoEl.value) return
  destroyBcPreview()
  bcPreviewReady.value = false
  try {
    const mod = await import('mpegts.js')
    const mpegts = mod.default || mod
    if (!mpegts?.isSupported?.()) return
    bcFlvPlayer = mpegts.createPlayer(
      { type: 'flv', isLive: true, url: BC_FLV[bcPreviewScreen.value] },
      { liveSync: true, liveSyncMaxLatency: 3.0, liveSyncTargetLatency: 1.2, liveSyncPlaybackRate: 1.12 })
    bcFlvPlayer.attachMediaElement(bcPreviewVideoEl.value)
    bcFlvPlayer.load()
    bcFlvPlayer.play().catch(() => {})
    bcPreviewVideoEl.value.onplaying = () => { bcPreviewReady.value = true }
  } catch (e) { console.warn('[admin] broadcast preview disabled:', e) }
}
function destroyBcPreview() {
  if (bcFlvPlayer) { try { bcFlvPlayer.destroy() } catch {} bcFlvPlayer = null }
  bcPreviewReady.value = false
}
function switchPreview(s) {
  if (bcPreviewScreen.value === s) return
  bcPreviewScreen.value = s
  nextTick(startBcPreview)
}

// ── 目标屏在线 + 当前播报真信号（纯只读探测，不驱动数字人） ──
const bcLive = reactive({ portrait: false, main: false })
const bcNow  = reactive({ speaking: false, text: '' })
let bcNowTimer = null, bcProbeTimer = null
// 探测某路直播流是否在推流：拉响应头即判定，随即中断不下载流体（零副作用）
async function probeStream(url) {
  try {
    const ctrl = new AbortController()
    const to = setTimeout(() => { try { ctrl.abort() } catch {} }, 3500)
    const res = await fetch(url, { signal: ctrl.signal })
    clearTimeout(to)
    const ok = res.ok
    try { ctrl.abort() } catch {}
    return ok
  } catch { return false }
}
async function probeBcOnline() {
  const [p, m] = await Promise.all([probeStream(BC_FLV.portrait), probeStream(BC_FLV.main)])
  bcLive.portrait = p; bcLive.main = m
}
async function pollBcNow() {
  try {
    const [p, m] = await Promise.all([
      fetch('/live/now-playing?screen=portrait').then(r => r.json()).catch(() => null),
      fetch('/live/now-playing?screen=main').then(r => r.json()).catch(() => null),
    ])
    const cur   = bcPreviewScreen.value === 'main' ? m : p
    const other = bcPreviewScreen.value === 'main' ? p : m
    const act = (cur && cur.speaking) ? cur : ((other && other.speaking) ? other : null)
    bcNow.speaking = !!(act && act.speaking)
    bcNow.text = act ? act.text : ''
  } catch {}
}
function startBcStatus() {
  stopBcStatus()
  probeBcOnline(); pollBcNow()
  bcProbeTimer = setInterval(probeBcOnline, 6000)   // 在线状态：每 6s 轻探
  bcNowTimer   = setInterval(pollBcNow, 2000)       // 播报内容：每 2s 取真信号
}
function stopBcStatus() {
  if (bcProbeTimer) { clearInterval(bcProbeTimer); bcProbeTimer = null }
  if (bcNowTimer)   { clearInterval(bcNowTimer);   bcNowTimer = null }
}

// ── 定时循环播报（前端计时，仅本页开启期间生效） ──
const bcRepeat    = ref(false)
const bcRepeatMin = ref(10)
const bcRepeatOn  = ref(false)
const bcRepeatLeft = ref(0)
let bcRepeatIntervalId = null, bcRepeatTickId = null
function startRepeat() {
  stopRepeat()
  bcRepeatOn.value = true
  const period = Math.max(1, bcRepeatMin.value) * 60
  bcRepeatLeft.value = period
  bcRepeatTickId = setInterval(() => { bcRepeatLeft.value = Math.max(0, bcRepeatLeft.value - 1) }, 1000)
  bcRepeatIntervalId = setInterval(() => { bcRepeatLeft.value = period; _doBroadcast({ silent: true }) }, period * 1000)
}
function stopRepeat() {
  if (bcRepeatIntervalId) { clearInterval(bcRepeatIntervalId); bcRepeatIntervalId = null }
  if (bcRepeatTickId) { clearInterval(bcRepeatTickId); bcRepeatTickId = null }
  bcRepeatOn.value = false; bcRepeatLeft.value = 0
}
watch(bcRepeat, (v) => { if (!v) stopRepeat() })

// ── 播报核心：手动 / 循环 / 重发 共用 ──
async function _doBroadcast({ silent = false } = {}) {
  const text = bcText.value.trim()
  if (!text) { if (!silent) ElMessage.error('请输入广播内容'); return false }
  const screens = []
  if (bcToPortrait.value) screens.push('portrait')
  if (bcToMain.value)     screens.push('main')
  if (!screens.length) { if (!silent) ElMessage.error('请至少选择一个播报屏幕'); return false }
  bcSending.value = true
  let ok = false
  try {
    const r = await fetch('/live/broadcast', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        text, screens, scenic_id: sceneStore.scenicId || 'lingshan',
        emotion: bcEmotion.value, subtitle: bcSubtitle.value,
        duration_s: bcDuration.value, style: bcStyle.value,
      }),
    })
    const d = await r.json().catch(() => ({}))
    const okCount = Object.values(d.spoken || {}).filter(Boolean).length
    ok = r.ok && okCount > 0
    if (!silent) {
      if (r.ok && okCount === screens.length) {
        ElMessage.success('广播已下发，数字人正在现场播报' + (bcSubtitle.value ? '，字幕已上屏' : ''))
      } else if (ok) {
        ElMessage.warning('部分屏幕播报失败（对应数字人服务可能未在线）')
      } else {
        ElMessage.error('播报失败：数字人直播服务未就绪')
      }
    }
    bcHistory.value.unshift({
      text, screens: screens.slice(), style: bcStyle.value, level: bcLevel.value,
      subtitle: bcSubtitle.value, ok,
      time: new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }),
    })
    if (bcHistory.value.length > 12) bcHistory.value.pop()
  } catch (e) {
    if (!silent) ElMessage.error('播报失败：' + (e.message || '网络错误'))
  } finally {
    bcSending.value = false
  }
  return ok
}
async function sendBroadcast() {
  const ok = await _doBroadcast({})
  if (ok && bcRepeat.value && !bcRepeatOn.value) {
    startRepeat()
    ElMessage.info(`已开启循环播报，每 ${bcRepeatMin.value} 分钟自动重播一次`)
  }
}
async function resendBroadcast(h) {
  bcText.value = h.text
  bcStyle.value = h.style; bcLevel.value = h.level || 'normal'
  bcToPortrait.value = h.screens.includes('portrait')
  bcToMain.value = h.screens.includes('main')
  bcSubtitle.value = !!h.subtitle
  await _doBroadcast({})
}
function clearSubtitle() {
  fetch('/live/subtitle', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text: '', screen: 'both' }),
  }).then(() => ElMessage.success('已撤下现场字幕')).catch(() => ElMessage.error('撤下失败'))
}

// 图标色 = 暗玻璃底上的高亮度霓虹系（大屏恒为深底）
const kpiList = ref([
  { icon: PhUsers,    label:'服务游客人次', value:'--', trend:0, color:'#34D399' },
  { icon: PhChatText, label:'对话轮次',     value:'--', trend:0, color:'#22D3EE' },
  { icon: PhStar,     label:'平均满意度',   value:'--', trend:0, color:'#FBBF24' },
  { icon: PhClock,    label:'平均停留时长', value:'--', trend:0, color:'#A78BFA' },
  { icon: PhSparkle,  label:'推荐曝光',     value:'--', trend:0, color:'#F472B6' },
  { icon: PhTrendUp,  label:'推荐点击率',   value:'--', trend:0, color:'#38BDF8' },
])

const trendData  = ref([])
const trendBackfilled = ref(false)   // 近7日存在推演补全点时，面板头亮出口径标签
const maxTrend = computed(() => Math.max(...trendData.value.map(d => d.count), 1))

const hotQAList = ref([])

const avgSatisfaction = ref(0)
const starDist = ref({ 5:0, 4:0, 3:0, 2:0, 1:0 })
function starColor(s) { return { 5:'#2D7A4F', 4:'#52A875', 3:'#004098', 2:'#B45309', 1:'#BE3535' }[s] }

const crowdRows = ref([])        // [{name, idx, level, trend}] 实时客流压力（idx=拥挤指数×100）
const crowdMeta = ref('')        // 「平季 · 下一场 14:30 九龙灌浴」
const profileData   = ref({ group_type:{}, lang:{}, interests:{} })
const featureData   = ref({ feature_open:{}, avg_rating:null, active_sessions:0 })
// 底部决策数据带（xlsx 行为数据）
const spendData  = ref([])       // [{category, avg, ratio}]
const spendAvg   = ref(0)        // 客单价
const ageData    = ref([])       // [{range, count}]
const genderMeta = ref('')       // 「男 52% · 女 48%」
const gsizeData  = ref([])       // [{label, count}] 同行规模分桶（5人及以上并入 5人+）
const groupMeta  = ref('')       // 「人均同行 3.2 人」
const tiersData  = ref([])       // [{name, ratio, revenue_share}] 客单价分层·营收贡献
const tiersMeta  = ref('')       // 「高消费客群 27% 人数 → 54% 营收」

const groupTypeLabel = { adult:'通用成人', family_kids:'亲子家庭', senior:'老年长辈', couple:'情侣出游' }
const featureLabel   = { tour:'路线讲解', voice:'语音', photo:'拍照', gps:'导航', facility:'设施', trace:'游记', postcard:'明信片', avatar:'形象切换', chat:'对话咨询' }

function getScenicId() {
  // 单一数据源：一律用 sceneStore.scenicId（已由 spotToScenicId 映射成后端支持的枚举）。
  // 此前大屏/报告直接用 user.scenic_spot_id（原始 spot id），绑定非枚举景区时会查空数据。
  return sceneStore.scenicId || 'lingshan'
}

const DAY_MAP = ['日','一','二','三','四','五','六']

const safeFetch = (url, ms = 10000) => {
  const ctrl = new AbortController()
  const t = setTimeout(() => ctrl.abort(), ms)
  return fetch(url, { signal: ctrl.signal })
    .then(r => r.ok ? r.json() : {})
    .catch(() => ({}))
    .finally(() => clearTimeout(t))
}

async function loadDashboard() {
  dashLoading.value = true
  dashError.value = false
  const sid = getScenicId()
  try {
    const [overview, dash, topics, sentTrend, crowd, profile, features, reco, spend, demog, tiers] = await Promise.all([
      safeFetch(`${ANALYTICS_BASE}/analytics/bi/overview?scenic_id=${sid}`),
      safeFetch(`${ANALYTICS_BASE}/analytics/dashboard?scenic_id=${sid}&days=7`),
      safeFetch(`${ANALYTICS_BASE}/analytics/topic-intents?scenic_id=${sid}&days=30&limit=8`),
      safeFetch(`${ANALYTICS_BASE}/analytics/sentiment-trend?scenic_id=${sid}`),
      safeFetch(`${ANALYTICS_BASE}/analytics/crowd?scenic_id=${sid}`),
      safeFetch(`${ANALYTICS_BASE}/analytics/profile?scenic_id=${sid}&days=7`),
      safeFetch(`${ANALYTICS_BASE}/analytics/feature-usage?scenic_id=${sid}&days=7`),
      safeFetch(`${ANALYTICS_BASE}/analytics/reco-performance?scenic_id=${sid}&days=7`),
      safeFetch(`${ANALYTICS_BASE}/analytics/bi/spending?scenic_id=${sid}`),
      safeFetch(`${ANALYTICS_BASE}/analytics/bi/demographics?scenic_id=${sid}`),
      safeFetch(`${ANALYTICS_BASE}/analytics/bi/spend-tiers?scenic_id=${sid}`),
    ])

    // 底部决策数据带
    if (Array.isArray(spend.structure) && spend.structure.length) {
      spendData.value = spend.structure
      spendAvg.value  = Math.round(spend.avg_total || 0)
    }
    if (Array.isArray(demog.age) && demog.age.length) {
      ageData.value = demog.age
      const g = Object.fromEntries((demog.gender || []).map(x => [x.gender, x.count]))
      const gTot = Object.values(g).reduce((a, b) => a + b, 0)
      if (gTot) genderMeta.value = ['男', '女'].filter(k => g[k])
        .map(k => `${k} ${Math.round(g[k] / gTot * 100)}%`).join(' · ')
    }
    // 同行规模：≥5 人并入「5人+」桶，保持 5 档可读
    if (Array.isArray(demog.group_size) && demog.group_size.length) {
      const buckets = { 1:0, 2:0, 3:0, 4:0, 5:0 }
      let wSum = 0, wTot = 0
      for (const x of demog.group_size) {
        buckets[Math.min(x.size, 5)] += x.count
        wSum += x.size * x.count; wTot += x.count
      }
      gsizeData.value = Object.entries(buckets)
        .filter(([,c]) => c > 0)
        .map(([s, c]) => ({ label: s === '5' ? '5人+' : `${s}人`, count: c }))
      if (wTot) groupMeta.value = `人均同行 ${(wSum / wTot).toFixed(1)} 人`
    }
    if (!groupMeta.value && overview.avg_group_size) groupMeta.value = `人均同行 ${overview.avg_group_size.toFixed(1)} 人`

    // 客单价分层·营收贡献：少数高消费客群撬动多数营收（营销决策的核心洞察）
    if (Array.isArray(tiers?.tiers) && tiers.tiers.length) {
      tiersData.value = tiers.tiers
      const hi = tiers.tiers.find(t => String(t.name).startsWith('高消费'))
      if (hi && hi.ratio != null && hi.revenue_share != null) {
        tiersMeta.value = `高消费 ${Math.round(hi.ratio * 100)}% 人数 → ${Math.round(hi.revenue_share * 100)}% 营收`
      }
    }

    // KPI
    kpiList.value[0].value = overview.visitors?.toLocaleString() ?? '--'
    kpiList.value[1].value = dash.total_conversations?.toLocaleString() ?? '--'
    const sat = overview.avg_satisfaction ?? sentTrend?.overall_satisfaction ?? 0
    kpiList.value[2].value = sat ? sat.toFixed(1) + '分' : '--'
    kpiList.value[3].value = overview.avg_stay_hours ? overview.avg_stay_hours.toFixed(1) + 'h' : '--'
    kpiList.value[4].value = (reco.impressions ?? 0).toLocaleString()
    kpiList.value[5].value = reco.ctr != null ? Math.round(reco.ctr * 100) + '%' : '--'

    // 较昨日：从 daily_stats 中取今日/昨日数据算涨跌幅
    if (Array.isArray(dash.daily_stats)) {
      const todayKey = new Date().toLocaleDateString('sv')
      const yestKey  = new Date(Date.now() - 86400000).toLocaleDateString('sv')
      const todayD = dash.daily_stats.find(d => d.date?.slice(0,10) === todayKey)
      const yestD  = dash.daily_stats.find(d => d.date?.slice(0,10) === yestKey)
      const pct = (cur, prev) => prev > 0 ? Math.round((cur - prev) / prev * 100) : null
      if (todayD && yestD) {
        kpiList.value[0].trend = pct(todayD.sessions      ?? 0, yestD.sessions      ?? 0)
        kpiList.value[1].trend = pct(todayD.conversations ?? 0, yestD.conversations ?? 0)
      }
    }
    // 满意度昨日对比：sentTrend.trend 最近两天
    if (Array.isArray(sentTrend?.trend) && sentTrend.trend.length >= 2) {
      const sorted = [...sentTrend.trend].sort((a,b) => new Date(a.date) - new Date(b.date))
      const last = sorted.at(-1), prev = sorted.at(-2)
      if (prev?.happy_ratio && last?.happy_ratio)
        kpiList.value[2].trend = Math.round((last.happy_ratio - prev.happy_ratio) / prev.happy_ratio * 100)
    }

    // 趋势图（近7日）— 补全缺失天，保证连续7天
    {
      const dataMap = {}
      if (Array.isArray(dash.daily_stats)) {
        for (const d of dash.daily_stats) {
          const key = d.date?.slice(0, 10)
          if (key) dataMap[key] = d.conversations ?? d.sessions ?? 0
        }
      }
      const today = new Date()
      trendData.value = Array.from({ length: 7 }, (_, i) => {
        const date = new Date(today)
        date.setDate(today.getDate() - 6 + i)
        const key = date.toLocaleDateString('sv') // YYYY-MM-DD in local tz
        return { day: '周' + DAY_MAP[date.getDay()], count: dataMap[key] ?? 0 }
      })
    }

    // 话题意图（topic-intents 返回 [{intent, count}]）
    if (Array.isArray(topics.topics) && topics.topics.length) {
      hotQAList.value = topics.topics.map(q => ({
        question: typeof q === 'string' ? q : (q.intent || q.question || q),
        count:    typeof q === 'object' ? (q.count ?? 1) : 1,
      }))
    }

    // 客群画像
    if (profile.group_type) profileData.value = profile

    // 功能使用
    if (features.feature_open) featureData.value = features

    // 满意度
    avgSatisfaction.value = sat ? parseFloat(sat.toFixed(1)) : 0
    if (Array.isArray(sentTrend?.trend) && sentTrend.trend.length) {
      const happyRatios = sentTrend.trend.map(t => t.happy_ratio ?? 0)
      const avgHappy = happyRatios.reduce((a, b) => a + b, 0) / happyRatios.length
      starDist.value = {
        5: Math.round(avgHappy * 100),
        4: Math.round((1 - avgHappy) * 60),
        3: Math.round((1 - avgHappy) * 25),
        2: Math.round((1 - avgHappy) * 10),
        1: Math.round((1 - avgHappy) * 5),
      }
    }

    // 景点关注度
    if (Array.isArray(crowd.attractions) && crowd.attractions.length) {
      crowdRows.value = [...crowd.attractions]
        .sort((a, b) => (b.crowd_index ?? 0) - (a.crowd_index ?? 0))
        .slice(0, 6)
        .map(a => ({
          name:  a.attraction,
          idx:   Math.round((a.crowd_index ?? 0) * 100),
          level: a.crowd_level || '空闲',
          trend: a.trend || '',
        }))
      const metaBits = []
      if (crowd.season) metaBits.push(crowd.season)
      if (crowd.next_show?.at) metaBits.push(`下一场 ${crowd.next_show.at} ${crowd.next_show.poi}`)
      crowdMeta.value = metaBits.join(' · ')
    }

    lastUpdateTime.value = new Date().toLocaleTimeString('zh-CN')
    if (kpiList.value.every(k => k.value === '--')) dashError.value = true
    else {
      dashLoaded.value = true
      await nextTick()
      _ecUpdate()
      if (!reportLoaded.value) loadReport()  // 大屏加载完后台预取报告
    }
  } catch {
    dashError.value = true
  } finally {
    dashLoading.value = false
  }
}

async function refreshDashboard() {
  dashLoaded.value = false
  await loadDashboard()
  ElMessage.success('数据已刷新')
}

// ── 感受度报告 ─────────────────────────────────
const reportLoading = ref(false)
const reportError   = ref(false)
const reportLoaded  = ref(false)
const rptKpi = ref({ pos:'--', total:'--', sat:'--', gaps:'--' })
const emotionDist = ref([])                       // 大屏情感环图也复用，勿删
const rptTrend  = ref({ days:[], pos:[], neg:[], vol:[] }) // 近7日积极/消极占比曲线 + 每日互动量
const topicRows = ref([])                          // [{name, count, pct}]
const gapRows   = ref([])                          // [{question, frequency}]
const EMOTION_LABEL   = { happy:'开心', excited:'兴奋', calm:'平静', curious:'好奇', sad:'难过', angry:'不满', neutral:'中性', disgust:'反感', fear:'担忧', empathetic:'共情', apologetic:'歉意', surprised:'惊喜', confused:'困惑' }
const EMOTION_COLOR   = { happy:'#2D7A4F', excited:'#004098', calm:'#6B7280', curious:'#1A5BAE', sad:'#BE3535', angry:'#BE3535', neutral:'#6B7280', disgust:'#BE3535', fear:'#B45309', empathetic:'#1A5BAE', apologetic:'#B45309', surprised:'#2D7A4F', confused:'#6B7280' }
const NEG_EMOTIONS    = new Set(['sad','angry','disgust','fear'])
const EMOTION_SENTIMENT = { happy:'positive', excited:'positive', calm:'neutral', curious:'neutral', neutral:'neutral', sad:'negative', angry:'negative', disgust:'negative', fear:'negative' }

const dialogueSamples = ref([])

function fmtDialogueTime(createdAt) {
  if (!createdAt) return ''
  const d = new Date(createdAt.replace(' ', 'T'))
  const now = new Date()
  const hm = d.toTimeString().slice(0, 5)
  return d.toDateString() === now.toDateString() ? `今日 ${hm}` : `${createdAt.slice(5, 10)} ${hm}`
}

async function loadReport() {
  reportLoading.value = true
  reportError.value = false
  const sid = getScenicId()
  try {
    const [sentTrend, topics, gaps, convs, biov] = await Promise.all([
      safeFetch(`${ANALYTICS_BASE}/analytics/sentiment-trend?scenic_id=${sid}`),
      safeFetch(`${ANALYTICS_BASE}/analytics/topic-intents?scenic_id=${sid}&days=30&limit=8`),
      safeFetch(`${ANALYTICS_BASE}/analytics/knowledge-gaps?scenic_id=${sid}`),
      safeFetch(`${ANALYTICS_BASE}/analytics/conversations?scenic_id=${sid}&limit=10`),
      safeFetch(`${ANALYTICS_BASE}/analytics/bi/overview?scenic_id=${sid}`),   // 5分制满意度（行为数据）
    ])

    const trend = (sentTrend || {}).trend || []

    // 聚合所有天的 emotion_counts
    const totalEmotions = {}
    let totalCount = 0
    for (const d of trend) {
      for (const [k, v] of Object.entries(d.emotion_counts || {})) {
        totalEmotions[k] = (totalEmotions[k] || 0) + v
        totalCount += v
      }
    }

    // 整体正/中/负占比
    const avgHappy = trend.length
      ? trend.reduce((s, d) => s + (d.happy_ratio || 0), 0) / trend.length
      : (sentTrend?.overall_satisfaction || 0)
    const posPct = Math.round(avgHappy * 100)
    const negRaw = totalCount
      ? Object.entries(totalEmotions).filter(([k]) => NEG_EMOTIONS.has(k)).reduce((s, [, v]) => s + v, 0) / totalCount
      : Math.max(0, (1 - avgHappy) * 0.25)
    const negPct = Math.round(negRaw * 100)
    const neuPct = Math.max(0, 100 - posPct - negPct)

    // 满意度：优先 bi/overview 的 5 分制真值；sentiment-trend 的 overall_satisfaction 是 0-1 比率，勿直接当分数
    const totalConvs = trend.reduce((s, d) => s + (d.total || 0), 0) || totalCount
    const satRaw = biov?.avg_satisfaction
    rptKpi.value = {
      pos:   posPct,
      total: totalConvs,
      sat:   satRaw != null && satRaw > 0 ? Number(satRaw).toFixed(1) : '--',
      gaps:  ((gaps || {}).gaps || []).length,
    }

    // 情感分布
    emotionDist.value = totalCount > 0
      ? Object.entries(totalEmotions)
          .map(([k, v]) => ({ label: EMOTION_LABEL[k] || k, pct: Math.round(v / totalCount * 100), color: EMOTION_COLOR[k] || '#6B7280' }))
          .sort((a, b) => b.pct - a.pct)
      : [
          { label:'积极', pct: posPct, color:'#2D7A4F' },
          { label:'中性', pct: neuPct, color:'#6B7280' },
          { label:'消极', pct: negPct, color:'#BE3535' },
        ]

    // 近7日趋势（积极/消极占比双曲线）
    const sorted7 = [...trend].sort((a, b) => new Date(a.date) - new Date(b.date)).slice(-7)
    rptTrend.value = {
      days: sorted7.map(d => (d.date || '').slice(5, 10) + ' 周' + DAY_MAP[new Date(d.date).getDay()]),
      pos:  sorted7.map(d => Math.round((d.happy_ratio || 0) * 100)),
      neg:  sorted7.map(d => {
        const r = d.total
          ? Object.entries(d.emotion_counts || {}).filter(([k]) => NEG_EMOTIONS.has(k)).reduce((s, [, v]) => s + v, 0) / d.total
          : 0
        return Math.round(r * 100)
      }),
      vol:  sorted7.map(d => d.total || 0),
    }

    // 游客关注点（表格，按提问量排序）
    const rawTopics = (topics || {}).topics || []
    const maxCount  = Math.max(...rawTopics.map(t => (typeof t === 'object' ? t.count : 1) || 0), 1)
    topicRows.value = rawTopics.slice(0, 8).map(t => ({
      name:  typeof t === 'string' ? t : t.intent,
      count: (typeof t === 'object' ? t.count : 1) || 0,
      pct:   Math.round(((typeof t === 'object' ? t.count : 1) || 0) / maxCount * 100),
    }))

    // 待改进项（真实未解答提问，按频次降序；不再编造"预期提升满意度"数字）
    gapRows.value = [...((gaps || {}).gaps || [])]
      .sort((a, b) => (b.frequency || 0) - (a.frequency || 0))
      .slice(0, 8)
      .map(g => ({ question: g.question, frequency: g.frequency || 1 }))

    // 典型对话摘录
    const convItems = (convs || {}).items || []
    dialogueSamples.value = convItems.map(c => ({
      time: fmtDialogueTime(c.created_at),
      sentiment: EMOTION_SENTIMENT[c.emotion] || 'neutral',
      question: c.user_message,
      answer: c.ai_reply,
    }))

    if (!trend.length && !rawTopics.length && !dialogueSamples.value.length) reportError.value = true
    else reportLoaded.value = true

  } catch (e) {
    console.error('报告数据加载失败', e)
    reportError.value = true
  } finally {
    reportLoading.value = false
  }
}

// ── 感受度报告图表（独立于大屏 _ec：报告页跟随管理端明暗主题，大屏恒为暗玻璃）──
const rptTrendEl = ref(null)
const rptEmoEl   = ref(null)
let _rptEc = {}

// 唯一初始化入口：flush:'post' 保证在 DOM 更新后执行。
// 坑：直刷落在报告页时，loading 分支不渲染图表容器 → 模板退订数据 refs → 写数据不排渲染队列，
// 裸 nextTick 会抢在重渲染前执行、容器不存在，图表永远空白。
watch([reportLoading, reportError, () => activeTab.value], () => {
  if (activeTab.value === 'report' && !reportLoading.value && !reportError.value && reportLoaded.value) _rptEcUpdate()
}, { flush: 'post' })

function _rptEcUpdate() {
  if (activeTab.value !== 'report') return
  const dark = document.documentElement.classList.contains('admin-dark')
  const T = dark
    ? { axis:'#8E93A6', split:'rgba(255,255,255,0.08)', tipBg:'#1B1D2E', tipBd:'rgba(255,255,255,0.12)', tipTx:'#E7E9F4', ring:'#14162A' }
    : { axis:'#7A8299', split:'#EDF0F5', tipBg:'#FFFFFF', tipBd:'#E5E9F2', tipTx:'#2B3346', ring:'#FFFFFF' }
  // 配色学参考截图：主曲线浅青绿、环图单色蓝阶梯、点缀天青蓝
  const POS = dark ? '#5EEAD4' : '#35C3B2'
  const NEG = dark ? '#F87171' : '#F5715D'
  const DONUT = dark
    ? ['#5B9CF8','#7DB5FA','#9FCBFB','#C2E0FD','#5EEAD4','#8E93A6']
    : ['#1D6FE8','#4D9AF0','#7FBCF5','#A9D2F8','#D5E9FB','#94A3B8']

  for (const [k, el] of [['trend', rptTrendEl], ['emo', rptEmoEl]]) {
    if (!el.value || !el.value.clientWidth) continue   // v-show 隐藏时不初始化（0×0 会成坏实例）
    if (_rptEc[k] && !document.contains(_rptEc[k].getDom())) { _rptEc[k].dispose(); delete _rptEc[k] }
    if (!_rptEc[k]) _rptEc[k] = echarts.init(el.value, null, { renderer:'canvas' })
  }

  if (_rptEc.trend) {
    _rptEc.trend.setOption({
      grid:{ top:18, right:20, bottom:26, left:40 },
      tooltip:{ trigger:'axis', backgroundColor:T.tipBg, borderColor:T.tipBd,
        textStyle:{ color:T.tipTx, fontSize:12 },
        formatter:(ps)=>{
          let s = ps[0]?.axisValueLabel || ''
          for (const p of ps) s += `<br>${p.marker}${p.seriesName}　<b>${p.value}${String(p.seriesName).includes('占比') ? '%' : ' 条'}</b>`
          return s
        },
        axisPointer:{ type:'line', lineStyle:{ type:'dashed', color:T.axis } } },
      xAxis:{ type:'category', boundaryGap:true, data:rptTrend.value.days,
        axisLine:{ lineStyle:{ color:T.split } }, axisTick:{ show:false },
        axisLabel:{ color:T.axis, fontSize:11 } },
      yAxis:[
        { type:'value', max:100, splitLine:{ lineStyle:{ color:T.split } },
          axisLabel:{ color:T.axis, fontSize:11, formatter:'{value}%' } },
        { type:'value', splitLine:{ show:false },
          axisLabel:{ color:T.axis, fontSize:11 } },
      ],
      series:[
        { name:'互动量', type:'bar', yAxisIndex:1, barMaxWidth:22, z:1,
          data:rptTrend.value.vol,
          itemStyle:{ color: dark ? 'rgba(91,156,248,0.22)' : 'rgba(79,154,240,0.18)',
                      borderRadius:[5,5,0,0] },
          emphasis:{ itemStyle:{ color: dark ? 'rgba(91,156,248,0.45)' : 'rgba(79,154,240,0.38)' } } },
        { name:'积极占比', type:'line', smooth:true, symbol:'circle', symbolSize:6, showSymbol:false, z:3,
          data:rptTrend.value.pos,
          lineStyle:{ color:POS, width:2.5 },
          itemStyle:{ color:POS, borderColor:T.ring, borderWidth:2 },
          areaStyle:{ color:{ type:'linear', x:0, y:0, x2:0, y2:1,
            colorStops:[{ offset:0, color:POS+'38' }, { offset:1, color:POS+'04' }] } },
          emphasis:{ focus:'series' } },
        { name:'消极占比', type:'line', smooth:true, symbol:'circle', symbolSize:6, showSymbol:false, z:3,
          data:rptTrend.value.neg,
          lineStyle:{ color:NEG, width:2 },
          itemStyle:{ color:NEG, borderColor:T.ring, borderWidth:2 },
          emphasis:{ focus:'series' } },
      ],
    })
  }

  if (_rptEc.emo) {
    const raw = emotionDist.value.filter(e => (e.pct || 0) > 0)
    const sorted = [...raw].sort((a, b) => (b.pct || 0) - (a.pct || 0))
    const top5 = sorted.slice(0, 5)
    const rest = sorted.slice(5)
    if (rest.length) top5.push({ label:'其他', pct: rest.reduce((s, e) => s + (e.pct || 0), 0) })
    _rptEc.emo.setOption({
      tooltip:{ trigger:'item', formatter:'{b}: {d}%', backgroundColor:T.tipBg,
        borderColor:T.tipBd, textStyle:{ color:T.tipTx } },
      title:{ text: String(rptKpi.value.total ?? '--'), subtext:'互动总量',
        left:'center', top:'37%', itemGap:4,
        textStyle:{ fontSize:22, fontWeight:700, color:T.tipTx },
        subtextStyle:{ fontSize:11, color:T.axis } },
      legend:{ orient:'horizontal', bottom:0, left:'center', icon:'circle',
        itemWidth:8, itemHeight:8, itemGap:10, type:'scroll', pageIconSize:10,
        textStyle:{ color:T.axis, fontSize:11 } },
      series:[{ type:'pie', radius:['50%','68%'], center:['50%','44%'],
        data: top5.map((e, i) => ({ name:e.label, value:e.pct || 0, itemStyle:{ color:DONUT[i % DONUT.length] } })),
        itemStyle:{ borderColor:T.ring, borderWidth:2, borderRadius:4 },
        label:{ show:true, position:'outside', fontSize:11, color:T.axis, formatter:'{d}%' },
        labelLine:{ length:10, length2:8, lineStyle:{ color:T.split } },
        emphasis:{ scale:true, scaleSize:4 } }],
    })
  }
}

onMounted(() => {
  setInterval(_updateClock, 1000)
  loadKnowledgeDocs()
  loadFaq()
  loadText()
if (authStore.user?.scenic_spot_id && !sceneStore.scenicName) {
    const spot = sceneStore.scenicSpots.find(s => s.id === authStore.user.scenic_spot_id)
    if (spot) sceneStore.selectSpot(spot)
  }
  if (activeTab.value === 'dashboard') loadDashboard()
  else if (activeTab.value === 'report') loadReport()
  else if (activeTab.value === 'consumption') loadConsumption()
  else setTimeout(() => { if (!reportLoaded.value) loadReport() }, 3000)
  if (activeTab.value === 'avatar') {
    loadAvatarTab()
  }
  if (activeTab.value === 'broadcast') {
    startBcStatus()
    nextTick(startBcPreview)
  }
  // 浅/深模式切换时，echarts 配置随主题变化，需重绘
  window.addEventListener('admin-theme-change', _onThemeChange)
})

function _onThemeChange() { nextTick(() => { _ecUpdate(); _rptEcUpdate(); _consEcUpdate() }) }

onUnmounted(() => {
  destroyPreview()
  destroyBcPreview(); stopBcStatus(); stopRepeat()
  window.removeEventListener('admin-theme-change', _onThemeChange)
})

async function refreshReport() {
  reportLoaded.value = false
  await loadReport()
  ElMessage.success('数据已刷新')
}

// ══ 消费分析（经营分析·营销决策；数据源=赛题行为数据 xlsx 真实样本，real_only 口径）══
const consLoading = ref(false)
const consError   = ref(false)
const consLoaded  = ref(false)
const consSource  = ref('')
const consKpi     = ref({ arpu:'--', revenue:'--', hiShare:'--', sample:'--' })
const consStruct  = ref([])   // [{category, avg, ratio}]
const consTiers   = ref([])   // [{name, ratio, revenue_share, ...}]
const consDrivers = ref({ stay:[], group:[] })
const consQuad    = ref({ scatter:[], median_spend:0, median_sat:0, quadrants:{} })
const consTrend   = ref([])   // [{period, visitors, avg_spend, revenue}]
const consAdvice  = ref([])

function _wan(n) {           // 大数字 → 万 简写
  const v = Number(n) || 0
  return v >= 10000 ? (v / 10000).toFixed(1) + '万' : Math.round(v).toLocaleString()
}

async function loadConsumption() {
  consLoading.value = true
  consError.value = false
  const sid = getScenicId()
  const B = `${ANALYTICS_BASE}/analytics/bi`
  try {
    const [ov, sp, tiers, drivers, quad, trend, advice] = await Promise.all([
      safeFetch(`${B}/overview?scenic_id=${sid}&real_only=true`),
      safeFetch(`${B}/spending?scenic_id=${sid}&real_only=true`),
      safeFetch(`${B}/spend-tiers?scenic_id=${sid}`),
      safeFetch(`${B}/spend-drivers?scenic_id=${sid}`),
      safeFetch(`${B}/satisfaction-value?scenic_id=${sid}`),
      safeFetch(`${B}/spend-trend?scenic_id=${sid}`),
      safeFetch(`${B}/marketing-advice?scenic_id=${sid}`),
    ])

    const sample = ov?.visitors || (tiers?.total) || 0
    const hi = (tiers?.tiers || []).find(t => String(t.name).startsWith('高消费'))
    consKpi.value = {
      arpu:    ov?.avg_spend_per_capita != null ? Math.round(ov.avg_spend_per_capita).toLocaleString() : '--',
      revenue: ov?.total_revenue != null ? _wan(ov.total_revenue) : '--',
      hiShare: hi?.revenue_share != null ? Math.round(hi.revenue_share * 100) : '--',
      sample:  sample || '--',
    }
    const srcName = sceneStore.scenicName || sid
    consSource.value = sample
      ? `《景点景区旅游数据行为分析数据》· ${srcName} ${sample} 条真实样本`
      : ''

    consStruct.value  = sp?.structure || []
    consTiers.value   = tiers?.tiers || []
    consDrivers.value = { stay: drivers?.stay || [], group: drivers?.group || [] }
    consQuad.value    = quad || { scatter:[], quadrants:{} }
    consTrend.value   = trend?.trend || []
    consAdvice.value  = advice?.advice || []

    if (!sample && !consStruct.value.length && !consAdvice.value.length) consError.value = true
    else consLoaded.value = true
  } catch (e) {
    console.error('消费分析加载失败', e)
    consError.value = true
  } finally {
    consLoading.value = false
  }
}

async function refreshConsumption() {
  consLoaded.value = false
  await loadConsumption()
  ElMessage.success('消费数据已刷新')
}

function adoptAdvice(a) {
  const txt = `【营销决策】${a.insight}\n建议：${a.action}\n预期：${a.expected}`
  try {
    navigator.clipboard?.writeText(txt)
    ElMessage.success('已采纳并复制建议，可纳入运营营销计划')
  } catch { ElMessage.success('已采纳该营销建议') }
}

// 消费分析图表（独立管理器，跟随管理端明暗主题；套用报告页 flush:'post' 范式）
const consTrendEl   = ref(null)
const consStructEl  = ref(null)
const consTiersEl   = ref(null)
const consDriversEl = ref(null)
const consQuadEl    = ref(null)
let _consEc = {}

watch([consLoading, consError, () => activeTab.value], () => {
  if (activeTab.value === 'consumption' && !consLoading.value && !consError.value && consLoaded.value) _consEcUpdate()
}, { flush: 'post' })

function _consEcUpdate() {
  if (activeTab.value !== 'consumption') return
  const dark = document.documentElement.classList.contains('admin-dark')
  const T = dark
    ? { axis:'#8E93A6', split:'rgba(255,255,255,0.08)', tipBg:'#1B1D2E', tipBd:'rgba(255,255,255,0.12)', tipTx:'#E7E9F4', ring:'#14162A' }
    : { axis:'#7A8299', split:'#EDF0F5', tipBg:'#FFFFFF', tipBd:'#E5E9F2', tipTx:'#2B3346', ring:'#FFFFFF' }
  const PRIMARY = dark ? '#7DB5FA' : '#1D6FE8'
  const CORAL   = dark ? '#F5A97F' : '#E0785A'
  const TEAL    = dark ? '#5EEAD4' : '#35C3B2'
  const PIE = dark
    ? ['#5B9CF8','#5EEAD4','#F5A97F','#B794F6','#7DB5FA','#8E93A6']
    : ['#1D6FE8','#35C3B2','#E0785A','#9B5BC7','#4D9AF0','#94A3B8']

  for (const [k, el] of [['trend', consTrendEl], ['struct', consStructEl], ['tiers', consTiersEl], ['drivers', consDriversEl], ['quad', consQuadEl]]) {
    if (!el.value || !el.value.clientWidth) continue
    if (_consEc[k] && !document.contains(_consEc[k].getDom())) { _consEc[k].dispose(); delete _consEc[k] }
    if (!_consEc[k]) _consEc[k] = echarts.init(el.value, null, { renderer:'canvas' })
  }

  // ① 消费与客流趋势（客单价折线 + 客流柱）
  if (_consEc.trend) {
    const tr = consTrend.value
    _consEc.trend.setOption({
      grid:{ top:18, right:24, bottom:26, left:48 },
      tooltip:{ trigger:'axis', backgroundColor:T.tipBg, borderColor:T.tipBd, textStyle:{ color:T.tipTx, fontSize:12 },
        formatter:(ps)=>{ let s = ps[0]?.axisValueLabel || ''
          for (const p of ps) s += `<br>${p.marker}${p.seriesName}　<b>${p.seriesName==='客单价' ? '¥'+p.value : p.value+' 人'}</b>`
          return s },
        axisPointer:{ type:'line', lineStyle:{ type:'dashed', color:T.axis } } },
      xAxis:{ type:'category', boundaryGap:true, data:tr.map(d=>d.period),
        axisLine:{ lineStyle:{ color:T.split } }, axisTick:{ show:false }, axisLabel:{ color:T.axis, fontSize:11 } },
      yAxis:[
        { type:'value', name:'¥', nameTextStyle:{ color:T.axis, fontSize:10 }, splitLine:{ lineStyle:{ color:T.split } }, axisLabel:{ color:T.axis, fontSize:11 } },
        { type:'value', splitLine:{ show:false }, axisLabel:{ color:T.axis, fontSize:11 } },
      ],
      series:[
        { name:'客流量', type:'bar', yAxisIndex:1, barMaxWidth:22, z:1, data:tr.map(d=>d.visitors),
          itemStyle:{ color: dark ? 'rgba(125,181,250,0.22)' : 'rgba(29,111,232,0.14)', borderRadius:[5,5,0,0] } },
        { name:'客单价', type:'line', smooth:true, symbol:'circle', symbolSize:6, showSymbol:false, z:3, data:tr.map(d=>d.avg_spend),
          lineStyle:{ color:PRIMARY, width:2.5 }, itemStyle:{ color:PRIMARY, borderColor:T.ring, borderWidth:2 },
          areaStyle:{ color:{ type:'linear', x:0, y:0, x2:0, y2:1, colorStops:[{ offset:0, color:PRIMARY+'34' }, { offset:1, color:PRIMARY+'04' }] } } },
      ],
    })
  }

  // ② 消费结构（环图）
  if (_consEc.struct) {
    _consEc.struct.setOption({
      tooltip:{ trigger:'item', formatter:(p)=>`${p.marker}${p.name}<br>人均 ¥${p.value}　占比 <b>${p.percent}%</b>`,
        backgroundColor:T.tipBg, borderColor:T.tipBd, textStyle:{ color:T.tipTx } },
      legend:{ orient:'horizontal', bottom:0, left:'center', icon:'circle', itemWidth:8, itemHeight:8, itemGap:10,
        type:'scroll', pageIconSize:10, textStyle:{ color:T.axis, fontSize:11 } },
      series:[{ type:'pie', radius:['48%','68%'], center:['50%','44%'],
        data: consStruct.value.map((e,i)=>({ name:e.category, value:Math.round(e.avg), itemStyle:{ color:PIE[i % PIE.length] } })),
        itemStyle:{ borderColor:T.ring, borderWidth:2, borderRadius:4 },
        label:{ show:true, position:'outside', fontSize:11, color:T.axis, formatter:'{d}%' },
        labelLine:{ length:10, length2:8, lineStyle:{ color:T.split } },
        emphasis:{ scale:true, scaleSize:4 } }],
    })
  }

  // ③ 客单价分层：人数占比 vs 营收占比（对比条）
  if (_consEc.tiers) {
    const ts = consTiers.value
    _consEc.tiers.setOption({
      grid:{ top:30, right:18, bottom:8, left:96 },
      legend:{ top:0, right:6, icon:'roundRect', itemWidth:11, itemHeight:8, itemGap:12, textStyle:{ color:T.axis, fontSize:11 } },
      tooltip:{ trigger:'axis', axisPointer:{ type:'shadow' }, backgroundColor:T.tipBg, borderColor:T.tipBd, textStyle:{ color:T.tipTx, fontSize:12 },
        formatter:(ps)=>{ let s = ps[0]?.axisValueLabel || ''; for (const p of ps) s += `<br>${p.marker}${p.seriesName}　<b>${p.value}%</b>`; return s } },
      xAxis:{ type:'value', max:100, splitLine:{ lineStyle:{ color:T.split } }, axisLabel:{ color:T.axis, fontSize:11, formatter:'{value}%' } },
      yAxis:{ type:'category', inverse:true, data: ts.map(t=>t.name),
        axisLine:{ lineStyle:{ color:T.split } }, axisTick:{ show:false }, axisLabel:{ color:T.axis, fontSize:11 } },
      series:[
        { name:'人数占比', type:'bar', barGap:'12%', barMaxWidth:13, data: ts.map(t=>Math.round((t.ratio||0)*100)),
          itemStyle:{ color:TEAL, borderRadius:[0,4,4,0] } },
        { name:'营收占比', type:'bar', barMaxWidth:13, data: ts.map(t=>Math.round((t.revenue_share||0)*100)),
          itemStyle:{ color:CORAL, borderRadius:[0,4,4,0] } },
      ],
    })
  }

  // ④ 消费驱动因子：停留时长(前4) + 同行规模(后4) × 客单价
  if (_consEc.drivers) {
    const st = consDrivers.value.stay || [], gp = consDrivers.value.group || []
    const cats = [...st.map(x=>x.range), ...gp.map(x=>x.range)]
    const vals = [...st.map(x=>x.avg_spend), ...gp.map(x=>x.avg_spend)]
    const nStay = st.length
    _consEc.drivers.setOption({
      grid:{ top:30, right:16, bottom:24, left:48 },
      tooltip:{ trigger:'axis', axisPointer:{ type:'shadow' }, backgroundColor:T.tipBg, borderColor:T.tipBd, textStyle:{ color:T.tipTx, fontSize:12 },
        formatter:(ps)=>{ const p = ps[0]; return `${p.axisValueLabel}<br>${p.marker}客单价 <b>¥${p.value}</b>` } },
      graphic: cats.length ? [
        { type:'text', left: nStay ? '20%' : '30%', top:6, style:{ text:'按停留时长', fill:T.axis, fontSize:10 } },
        { type:'text', right:'16%', top:6, style:{ text:'按同行规模', fill:T.axis, fontSize:10 } },
      ] : [],
      xAxis:{ type:'category', data:cats, axisLine:{ lineStyle:{ color:T.split } }, axisTick:{ show:false }, axisLabel:{ color:T.axis, fontSize:11 } },
      yAxis:{ type:'value', name:'¥', nameTextStyle:{ color:T.axis, fontSize:10 }, splitLine:{ lineStyle:{ color:T.split } }, axisLabel:{ color:T.axis, fontSize:11 } },
      series:[{ type:'bar', barMaxWidth:26, data: vals.map((v,i)=>({ value:v, itemStyle:{ color: i < nStay ? PRIMARY : CORAL, borderRadius:[4,4,0,0] } })) }],
    })
  }

  // ⑤ 满意度 × 消费四象限（散点 + 中位数分界）
  if (_consEc.quad) {
    const q = consQuad.value
    _consEc.quad.setOption({
      grid:{ top:16, right:20, bottom:34, left:52 },
      tooltip:{ trigger:'item', backgroundColor:T.tipBg, borderColor:T.tipBd, textStyle:{ color:T.tipTx, fontSize:12 },
        formatter:(p)=>`消费 ¥${p.value[0]}　满意度 ${p.value[1]}分` },
      xAxis:{ type:'value', name:'消费(¥)', nameLocation:'middle', nameGap:24, nameTextStyle:{ color:T.axis, fontSize:11 },
        splitLine:{ lineStyle:{ color:T.split } }, axisLabel:{ color:T.axis, fontSize:11 } },
      yAxis:{ type:'value', name:'满意度', min:0, max:5, nameTextStyle:{ color:T.axis, fontSize:11 },
        splitLine:{ lineStyle:{ color:T.split } }, axisLabel:{ color:T.axis, fontSize:11 } },
      series:[{ type:'scatter', symbolSize:8, data: (q.scatter||[]).map(s=>[s.spend, s.sat]),
        itemStyle:{ color:PRIMARY+'99', borderColor:PRIMARY, borderWidth:0.5 },
        markLine:{ silent:true, symbol:'none', lineStyle:{ type:'dashed', color:CORAL, width:1.2 },
          label:{ color:T.axis, fontSize:10 },
          data:[ { xAxis: q.median_spend, label:{ formatter:'中位消费' } }, { yAxis: q.median_sat, label:{ formatter:'中位满意度' } } ] } }],
    })
  }
}

// ── AI 成品报告（POST /analytics/report：后端 LLM 基于真实对话记录生成）──
const aiReportLoading = ref(false)
const aiReportText    = ref('')
const aiReportAt      = ref('')

// LLM 纯文本 → 轻排版 HTML（先转义防注入，再识别标题/列表/加粗；不引第三方 md 库）
// 轻量 markdown → HTML（先整体转义再转换，无 XSS 面；报告正文与 AI 助手输出共用）
function mdToHtml(src) {
  const esc = (s) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
  // 行内：先粗体，再斜体（避免与粗体的 ** 冲突），再行内代码
  const inline = (s) => esc(s)
    .replace(/\*\*([^*]+)\*\*/g, '<b>$1</b>')
    .replace(/(^|[^*])\*([^*\n]+)\*(?!\*)/g, '$1<em>$2</em>')
    .replace(/`([^`]+)`/g, '<code>$1</code>')
  // LLM 有时把整篇用 ```markdown … ``` 代码围栏包裹 → 先去壳，再忽略残留围栏行
  let text = (src || '').replace(/\r\n/g, '\n').trim()
  text = text.replace(/^```[\w-]*\n/, '').replace(/\n```$/, '').trim()
  let html = '', listType = null   // null | 'ul' | 'ol'
  const closeList = () => { if (listType) { html += `</${listType}>`; listType = null } }
  const openList = (t) => { if (listType !== t) { closeList(); html += `<${t}>`; listType = t } }
  for (const raw of text.split('\n')) {
    const line = raw.trim()
    if (!line) { closeList(); continue }
    // 忽略残留代码围栏行（```、```lang）
    if (/^```/.test(line)) { closeList(); continue }
    // 分隔线
    if (/^[-*_]{3,}$/.test(line)) { closeList(); html += '<hr>'; continue }
    // ATX 标题：# → h3、## → h4、### → h5（分级层次）
    let m = line.match(/^(#{1,6})\s+(.*)$/)
    if (m) { closeList(); const lv = Math.min(m[1].length + 2, 6); html += `<h${lv}>${inline(m[2])}</h${lv}>`; continue }
    // 中文小节标题：【…】 或 一、二、
    if (/^【.+】[:：]?$/.test(line) || /^[一二三四五六七八九十]+[、.．]/.test(line)) {
      closeList(); html += `<h4>${inline(line)}</h4>`; continue
    }
    // 引用
    if (/^>\s?/.test(line)) { closeList(); html += `<blockquote>${inline(line.replace(/^>\s?/, ''))}</blockquote>`; continue }
    // 有序列表（保留序号语义 → <ol>）
    m = line.match(/^\d+[.、)]\s+(.*)$/)
    if (m) { openList('ol'); html += `<li>${inline(m[1])}</li>`; continue }
    // 无序列表
    m = line.match(/^[-•*]\s+(.*)$/)
    if (m) { openList('ul'); html += `<li>${inline(m[1])}</li>`; continue }
    // 普通段落
    closeList(); html += `<p>${inline(line)}</p>`
  }
  closeList()
  return html
}
const renderedReport = computed(() => mdToHtml(aiReportText.value))
async function genAiReport() {
  aiReportLoading.value = true
  try {
    const res = await axios.post(`${ANALYTICS_BASE}/analytics/report`, {
      scenic_id: getScenicId(), days: 7,
    }, { timeout: 90000 })
    aiReportText.value = res.data?.report || '（后端未返回报告内容）'
    aiReportAt.value = new Date().toLocaleString('zh-CN')
  } catch (e) {
    ElMessage.error('报告生成失败：' + (e.response?.data?.detail || e.message))
  } finally { aiReportLoading.value = false }
}

// ── AI 分析助手 ─────────────────────────────────
const aiPanelOpen  = ref(true)
const aiMessages   = ref([])
const aiInput      = ref('')
const aiLoading    = ref(false)
const aiChatEl     = ref(null)
const aiTextareaEl = ref(null)

const aiQuickQuestions = ['当前客流压力，需要广播疏导吗？', '高价值客群是谁？给几条营销建议', '有哪些该补充的 FAQ？', '今日运营数据摘要', '游客负面情感来源分析']

function scrollAiToBottom() {
  nextTick(() => { if (aiChatEl.value) aiChatEl.value.scrollTop = aiChatEl.value.scrollHeight })
}

function autoResizeTextarea(e) {
  const el = e.target
  el.style.height = 'auto'
  el.style.height = Math.min(el.scrollHeight, 120) + 'px'
}

function sendQuickQuestion(q) { aiInput.value = q; sendAiMessage() }

async function sendAiMessage() {
  const text = aiInput.value.trim()
  if (!text || aiLoading.value) return

  const history = aiMessages.value
    .filter(m => m.content && !m.loading)
    .map(m => ({ role: m.role, content: m.content }))

  aiMessages.value.push({ role: 'user', content: text, id: Date.now() })
  aiInput.value = ''
  if (aiTextareaEl.value) aiTextareaEl.value.style.height = 'auto'
  aiLoading.value = true
  aiMessages.value.push({ role: 'assistant', content: '', id: Date.now() + 1, loading: true, status: '', actions: [] })
  scrollAiToBottom()

  try {
    const res = await fetch('/api/admin/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: text, history, scenic_id: getScenicId() })
    })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)

    const reader = res.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''
    const lastMsg = aiMessages.value[aiMessages.value.length - 1]
    lastMsg.loading = false

    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop()
      for (const line of lines) {
        if (!line.startsWith('data: ')) continue
        const s = line.slice(6)
        if (s === '[DONE]') break
        try {
          const d = JSON.parse(s)
          if (d.status) { lastMsg.status = d.status }
          if (d.text)   { lastMsg.status = ''; lastMsg.content += d.text; scrollAiToBottom() }
          if (d.action) { (lastMsg.actions ||= []).push({ ...d.action, done: false }); scrollAiToBottom() }
          if (d.error)  { lastMsg.status = ''; lastMsg.content = `错误: ${d.error}`; lastMsg.error = true }
        } catch {}
      }
    }
  } catch (e) {
    const lastMsg = aiMessages.value[aiMessages.value.length - 1]
    lastMsg.content = '请求失败，请检查后端服务与 DashScope API Key 配置'
    lastMsg.loading = false
    lastMsg.error = true
    lastMsg.status = ''
  } finally {
    aiLoading.value = false
    scrollAiToBottom()
  }
}

// ── 运营代理建议动作卡（F6）：确认后才真正执行 ─────────────────────────
function goBroadcastWith(act) {
  // 跳转到应急广播页并预填代理起草的文案
  bcText.value = act.text || ''
  if (act.emotion) bcEmotion.value = act.emotion
  bcStyle.value = 'alert'
  act.done = true
  selectNav('broadcast')
  ElMessage.success('已把广播草稿填入应急广播页，请核对后播报')
}
async function confirmAddFaqAction(act, item, idx) {
  try {
    await axios.post('/api/knowledge/faq', {
      scenic_id: sceneStore.scenicId || 'lingshan',
      question: item.question, answer: item.answer,
      category: item.category || '基础信息',
    })
    item._added = true
    ElMessage.success('已加入知识库，游客端将以最高优先级作答')
    if (activeTab.value === 'knowledge' && kbTab.value === 'faq') loadFaq()
  } catch (e) {
    ElMessage.error('添加失败：' + (e.response?.data?.detail || e.message))
  }
}
</script>

<style scoped lang="scss">
/* ── 整体布局 ─────────────────────────────────── */
.admin-layout {
  display: flex;
  width: 100vw;
  height: 100vh;
  overflow: hidden;
  background: var(--c-paper);
}

/* ── 侧边栏 ─────────────────────────────────── */
.sidebar {
  width: 240px;   /* 220 → 240：字号+2 后防启动卡副文案/账号行折行 */
  flex-shrink: 0;
  background: #FFFFFF;   /* 纯白侧栏（参考截图）；深色模式由 admin-dark.css 覆盖 */
  border-right: 1px solid var(--c-border);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}


.sidebar-nav {
  flex: 1;
  padding: 12px 10px;
  display: flex;
  flex-direction: column;
  gap: 2px;
  overflow-y: auto;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 8px 10px;
  border-radius: var(--radius-sm);
  border: 1px solid transparent;
  background: transparent;
  color: var(--c-ink-3);
  font-size: 14px;
  font-family: var(--font-sans);
  cursor: pointer;
  transition: all 0.15s;
  text-align: left;

  &:hover {
    background: var(--c-paper); color: var(--c-ink);
    svg { transform: translateX(1px); }
  }
  svg { transition: transform 0.15s; }
  &.active {
    background: var(--c-gold-2);   /* 选中 = 浅一档的天青蓝 + 白字 */
    color: #fff;
    font-weight: 600;
  }
}

.sidebar-footer {
  padding: 12px 14px;
  border-top: 1px solid var(--c-border);
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.scenic-name-input {
  display: flex;
  align-items: center;
  gap: 6px;
  color: var(--c-ink-4);

  .name-input {
    flex: 1;
    border: none;
    background: transparent;
    font-size: 13px;
    color: var(--c-ink-3);
    font-family: var(--font-sans);
    outline: none;
    padding: 0;
    &::placeholder { color: var(--c-ink-4); }
    &:focus { color: var(--c-ink); }
  }
}

.account-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.account-info {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: var(--c-ink-3);
  svg { color: var(--c-ink-4); }
}

.logout-btn {
  width: 26px; height: 26px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--c-border);
  background: transparent;
  color: var(--c-ink-4);
  display: flex; align-items: center; justify-content: center;
  cursor: pointer; transition: all 0.15s;
  &:hover { border-color: rgba(190,53,53,0.35); color: var(--c-red); background: var(--c-red-bg); }
}

/* ── 主内容 ─────────────────────────────────── */
.admin-main {
  flex: 1;
  overflow-y: auto;
  background: var(--c-paper);
}

.tab-content {
  padding: 32px 36px;
  max-width: 1240px;
  margin: 0 auto;
  animation: tab-in 0.18s ease-out;
}

.page-header {
  display: flex;
  align-items: baseline;
  gap: 12px;
  margin-bottom: 28px;
  flex-wrap: wrap;

  h2 {
    font-family: var(--font-serif);
    font-size: 22px;
    font-weight: 700;
    color: var(--c-ink);
    letter-spacing: -0.01em;
    position: relative;
    padding-bottom: 10px;

    &::after {
      content: '';
      position: absolute;
      left: 0; bottom: 0;
      width: 28px; height: 2px;
      background: var(--c-gold);
      border-radius: 1px;
    }
  }

  .page-sub {
    font-size: 12px;
    color: var(--c-ink-4);
  }

  .header-actions {
    margin-left: auto;
    display: flex;
    align-items: center;
    gap: 10px;
    flex-wrap: wrap;
  }
}

/* ── 通用组件 ─────────────────────────────────── */
.card {
  background: var(--c-surface);
  border: 1px solid var(--c-border);
  border-radius: var(--radius-lg);
  padding: 22px;
  box-shadow: var(--shadow-sm);
}

.card-title {
  display: flex;
  align-items: center;
  gap: 7px;
  font-size: 13px;
  font-weight: 700;
  color: var(--c-ink);
  margin-bottom: 18px;
  svg { color: var(--c-ink-3); flex-shrink: 0; }
}

.card-tag {
  margin-left: 6px;
  font-size: 11px;
  font-weight: 500;
  color: var(--c-gold);
  background: var(--c-gold-bg);
  border: 1px solid var(--c-gold-bdr);
  border-radius: 4px;
  padding: 1px 7px;
  line-height: 18px;
}

.two-col {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}

.col-left, .col-right {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.mb16 { margin-bottom: 16px; }
.mb24 { margin-bottom: 24px; }
.mt12 { margin-top: 12px; }
.mt16 { margin-top: 16px; }
.ml-auto { margin-left: auto; }

.primary-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 7px 14px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--c-gold);
  background: var(--c-gold);
  color: #fff;
  font-size: 13px;
  font-family: var(--font-sans);
  cursor: pointer;
  transition: all 0.15s;

  &:hover  { background: var(--c-gold-2); border-color: var(--c-gold-2); }
  &:active { transform: translateY(1px); box-shadow: inset 0 1px 3px rgba(0,0,0,0.12); }
  &:disabled { opacity: 0.5; cursor: not-allowed; }
  &.full-btn { width: 100%; justify-content: center; }
}

.ghost-btn {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 6px 12px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--c-border);
  background: var(--c-surface);
  color: var(--c-ink-2);
  font-size: 12px;
  font-family: var(--font-sans);
  cursor: pointer;
  transition: all 0.15s;

  &:hover  { border-color: var(--c-border-2); background: var(--c-paper); }
  &:active { transform: translateY(1px); }
  &:disabled { opacity: 0.5; cursor: not-allowed; }
  &.sm { padding: 4px 9px; font-size: 11px; }
}

.link-btn {
  background: none; border: none; cursor: pointer;
  font-size: 12px; color: var(--c-blue); padding: 0 6px;
  font-family: var(--font-sans); white-space: nowrap;
  transition: color 0.15s;
  &:hover  { color: var(--c-blue-2); }
  &:active { opacity: 0.7; }
  &.danger  { color: var(--c-red);   &:hover { color: #c83030; } }
  &.rebuild { color: var(--c-amber); &:hover { color: #9a6a20; } }
  &.reindex { color: var(--c-blue);  &:hover { color: var(--c-blue-2); } }
}

/* ── 形象管理 ─────────────────────────────────── */
/* 配置为主区（弹性，内部 2 列：形象库/换装/AI 跨满行，音色+背景并排），
   预览为 360px 吸顶侧栏（9:16 满填、滚动配置时常驻可见）。 */
/* ── 形象工作台（生产者视角，.rpt 词汇复用）─────────────── */
.av2-kpi { margin-bottom: 20px; }
.av2-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 400px;
  gap: 24px;
  align-items: start;
}
.av2-col-main { display: flex; flex-direction: column; gap: 20px; min-width: 0; }
.av2-col-preview { position: sticky; top: 20px; display: flex; flex-direction: column; gap: 20px; }

.av2-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: 12px;
}
.av2-card {
  display: flex; gap: 10px; padding: 10px;
  border: 1px solid var(--c-border); border-radius: var(--radius);
  background: var(--c-paper); cursor: pointer;
  transition: border-color .15s, box-shadow .15s, transform .12s;
}
.av2-card:hover { border-color: var(--c-gold-bdr); transform: translateY(-1px); }
.av2-card.sel { border-color: var(--c-gold); box-shadow: 0 0 0 2px var(--c-gold-soft, rgba(47,124,246,.18)); }
.av2-thumb {
  position: relative; width: 54px; height: 72px; flex-shrink: 0;
  border-radius: var(--radius-sm); overflow: hidden; background: #0d1017;
  img { width: 100%; height: 100%; object-fit: cover; object-position: top; }
}
.av2-check { position: absolute; top: 3px; right: 3px; color: var(--c-gold);
  background: #fff; border-radius: 50%; }
.av2-info { display: flex; flex-direction: column; gap: 3px; min-width: 0; flex: 1; }
.av2-stage { font-size: 13px; font-weight: 700; color: var(--c-ink); font-family: var(--font-serif, inherit);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.av2-orig { font-size: 10px; color: var(--c-ink-4); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.av2-pills { display: flex; flex-wrap: wrap; gap: 4px; margin-top: 2px; }
.av2-pills .sentiment-tag { font-size: 10px; padding: 1px 6px; }
.av2-pubrow { display: flex; align-items: center; gap: 6px; margin-top: auto; }
.av2-pub-label { font-size: 10px; color: var(--c-ink-4); }

.av2-field { margin-top: 14px; }
.av2-field:first-of-type { margin-top: 4px; }
.av2-flabel { display: flex; align-items: center; gap: 5px; font-size: 12px; font-weight: 600;
  color: var(--c-ink-2); margin-bottom: 7px; svg { color: var(--c-gold); } }
.av2-voice-row { display: flex; gap: 8px; align-items: center; .av-select { flex: 1; } }
.av2-try { flex-shrink: 0; padding: 0 12px; height: 40px; display: inline-flex; align-items: center; gap: 4px; }
.av2-inline { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
.av2-inline-hint { font-size: 11px; color: var(--c-ink-4); }

.av2-preview-box {
  position: relative;
  width: min(100%, calc((100dvh - 340px) * 9 / 16));
  margin-inline: auto;
  aspect-ratio: 9 / 16;
  max-height: calc(100dvh - 340px);
  border-radius: var(--radius); overflow: hidden;
  display: flex; align-items: center; justify-content: center;
  border: 1px solid var(--c-border); background: #05060a; margin-bottom: 12px;
}
.av2-preview-img { width: 100%; height: 100%; object-fit: cover; object-position: top; }
.av2-preview-empty { display: flex; flex-direction: column; align-items: center; gap: 8px;
  color: rgba(255,255,255,0.45); svg { color: rgba(255,255,255,0.22); }
  p { font-size: 12px; color: rgba(255,255,255,0.55); } }
.av2-preview-chip { position: absolute; bottom: 10px; left: 10px;
  font-size: 12px; font-weight: 700; background: rgba(255,255,255,0.92);
  color: var(--c-gold); border-radius: var(--radius-sm); padding: 3px 10px; }
.av2-welcome { font-size: 12px; color: var(--c-ink-2); font-style: italic; margin: 0 0 8px; line-height: 1.5; }
.av2-plate-note { display: flex; align-items: center; gap: 5px; font-size: 11px; color: #d08700; margin: 0 0 8px;
  svg { flex-shrink: 0; } }
.av2-preview-meta { display: flex; gap: 16px; font-size: 12px; color: var(--c-ink-4); margin-bottom: 10px; }
.av2-default-check { margin-bottom: 4px; }
.av2-apply-hint { font-size: 11px; color: var(--c-ink-4); margin: 6px 0 0; text-align: center; }
.av2-monitor-toggle { margin-top: 12px; width: 100%; background: none; border: 1px dashed var(--c-border);
  border-radius: var(--radius-sm); padding: 7px; font-size: 12px; color: var(--c-ink-3); cursor: pointer;
  display: inline-flex; align-items: center; justify-content: center; gap: 5px;
  &:hover { border-color: var(--c-gold-bdr); color: var(--c-gold); } }
.av2-monitor { margin-top: 10px; width: 100%; aspect-ratio: 9/16; max-height: 320px; margin-inline: auto;
  border-radius: var(--radius-sm); overflow: hidden; border: 1px solid var(--c-border); background: #05060a; }

/* 甜美候选批 */
.cand-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; margin-top: 12px; }
.cand-card { position: relative; aspect-ratio: 9/16; border-radius: var(--radius-sm); overflow: hidden;
  border: 2px solid var(--c-border); cursor: pointer; background: #0d1017; transition: border-color .15s; }
.cand-card:hover { border-color: var(--c-gold-bdr); }
.cand-card.sel { border-color: var(--c-gold); }
.cand-card img { width: 100%; height: 100%; object-fit: cover; object-position: top; }
.cand-badge { position: absolute; bottom: 4px; left: 4px; font-size: 10px; padding: 1px 5px;
  border-radius: 4px; color: #fff; }
.cand-badge.ok { background: rgba(34,180,120,0.85); }
.cand-badge.warn { background: rgba(214,120,80,0.9); }
.cand-check { position: absolute; top: 4px; right: 4px; color: var(--c-gold); background: #fff; border-radius: 50%; }
.cand-adopt { display: flex; gap: 8px; align-items: center; margin-top: 12px; }
.cand-hint { font-size: 11px; color: var(--c-ink-4); margin: 8px 0 0; line-height: 1.5; }

.progress-wrap {
  margin-top: 10px;
  display: flex;
  flex-direction: column;
  gap: 5px;
  span { font-size: 11px; color: var(--c-ink-4); }
}

.progress-bar {
  height: 3px;
  background: var(--c-border);
  border-radius: 2px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: var(--c-gold);
  border-radius: 2px;
  transition: width 0.3s;
}

.empty-state {
  display: flex; flex-direction: column; align-items: center; gap: 8px;
  padding: 24px; color: var(--c-ink-4);
  svg { color: var(--c-border-2); }
  p { font-size: 12px; }
}

/* ── 知识库 ─────────────────────────────────── */
.upload-zone {
  padding: 32px 20px; text-align: center;
  .upload-ico { color: var(--c-gold); margin-bottom: 10px; }
  .upload-main { font-size: 13px; color: var(--c-ink-2); em { color: var(--c-gold); font-style: normal; } }
  .upload-hint { font-size: 11px; color: var(--c-ink-4); margin-top: 6px; }
}

.search-wrap {
  display: flex; align-items: center; gap: 6px;
  border: 1px solid var(--c-border); border-radius: var(--radius-sm);
  padding: 4px 10px; background: var(--c-paper);
  .search-ico { color: var(--c-ink-4); flex-shrink:0; }
  .search-input { border:none; background:transparent; outline:none; font-size:12px; color:var(--c-ink); font-family:var(--font-sans); width:160px; &::placeholder { color:var(--c-ink-4); } }
}

.doc-cell {
  display: flex; align-items: center; gap: 7px;
  .doc-type {
    font-size:9px; font-weight:700; padding:1px 5px; border-radius:var(--radius-xs);
    &.pdf  { background:rgba(190,53,53,0.1); color:var(--c-red); }
    &.docx { background:rgba(27,77,142,0.1); color:var(--c-blue); }
    &.txt  { background:var(--c-paper);      color:var(--c-ink-4); border:1px solid var(--c-border); }
    &.md   { background:rgba(45,122,79,0.1); color:var(--c-green); }
  }
}

.status-pill {
  font-size: 11px; padding: 2px 8px; border-radius: 99px;
  &.green  { background:var(--c-green-bg); color:var(--c-green); }
  &.amber  { background:var(--c-amber-bg); color:var(--c-amber); }
  &.red    { background:var(--c-red-bg);   color:var(--c-red); }
}

.kb-summary {
  margin-top: 10px; font-size: 11px; color: var(--c-ink-4);
  padding-top: 10px; border-top: 1px solid var(--c-border);
}

/* el-table 样式优化 */
:deep(.el-table) {
  --el-table-border-color: transparent;
  --el-table-header-bg-color: var(--c-paper);
  --el-table-row-hover-bg-color: var(--c-gold-bg);

  &::before { display: none; }                          /* 去掉底部多余线 */

  .el-table__header-wrapper th {
    border-bottom: 1px solid var(--c-border) !important;
    font-size: 11px;
    color: var(--c-ink-4);
    font-weight: 500;
    padding: 7px 0;
  }

  .el-table__row td {
    border-bottom: 1px solid var(--c-border) !important;
    padding: 10px 0;
  }

  /* 最后一行不需要底线 */
  .el-table__row:last-child td {
    border-bottom: none !important;
  }

  .el-table__body-wrapper {
    .el-scrollbar__bar.is-horizontal { bottom: 0; }
    .el-scrollbar__wrap { padding-bottom: 6px; }
  }
}

.ops-cell {
  display: flex; align-items: center; gap: 0; white-space: nowrap; flex-wrap: nowrap;
}

.ops-sep {
  display: inline-block; width: 1px; height: 10px;
  background: var(--c-border-2); margin: 0 2px; flex-shrink: 0;
}

.form-grid { display: flex; flex-direction: column; gap: 12px; }
.form-row {
  display: flex; align-items: center; gap: 12px;
  label { font-size: 12px; color: var(--c-ink-3); width: 80px; flex-shrink:0; }
  .threshold-val { font-size: 12px; color: var(--c-ink-3); min-width: 28px; }
}

/* ── 知识库子 Tab ──────────────────────────────── */
.kb-nav {
  display: flex; gap: 4px;
  .kb-nav-btn {
    display: flex; align-items: center; gap: 5px;
    padding: 6px 14px; border-radius: var(--radius-sm); border: 1px solid var(--c-border);
    font-size: 12px; color: var(--c-ink-3); background: var(--c-surface); cursor: pointer;
    transition: all .15s; font-family: var(--font-sans);
    &:hover:not(.active) { border-color: var(--c-gold); color: var(--c-gold-dark); }
    &:active { transform: translateY(1px); }
    &.active { background: var(--c-gold-bg); border-color: var(--c-gold); color: var(--c-gold); font-weight: 500; }
  }
}

.kb-toolbar {
  display: flex; align-items: center; justify-content: space-between; gap: 12px; flex-wrap: wrap;
}
.kb-toolbar-right { display: flex; align-items: center; gap: 8px; }

.cat-tabs {
  display: flex; gap: 4px; flex-wrap: wrap;
  .cat-btn {
    padding: 3px 10px; border-radius: 20px; border: 1px solid var(--c-border);
    font-size: 11px; color: var(--c-ink-3); background: transparent; cursor: pointer;
    transition: all .12s; font-family: var(--font-sans);
    &.active { background: var(--c-gold-bg); border-color: var(--c-gold); color: var(--c-gold); }
    &:hover:not(.active) { border-color: var(--c-ink-4); color: var(--c-ink-2); }
  }
}

.cat-badge {
  padding: 1px 7px; border-radius: 20px; font-size: 10px;
  background: var(--c-gold-bg); color: var(--c-gold); border: 1px solid var(--c-gold);
}

.edit-form-card { background: var(--c-gold-bg); border-color: var(--c-gold-bdr); }

.edit-form {
  display: flex; flex-direction: column; gap: 10px; margin-bottom: 12px;
}
.edit-row {
  display: flex; align-items: flex-start; gap: 10px;
  label { font-size: 12px; color: var(--c-ink-3); width: 36px; flex-shrink: 0; padding-top: 5px; }
  &.edit-row-grow label { padding-top: 6px; }
}
.edit-row-double { display: flex; gap: 12px; align-items: flex-start; }
.edit-input {
  flex: 1; height: 30px; padding: 0 10px; font-size: 13px;
  border: 1px solid var(--c-border); border-radius: var(--radius-sm);
  background: var(--c-paper); color: var(--c-ink); font-family: var(--font-sans);
  outline: none; transition: border-color .15s, box-shadow .15s;
  &:focus {
    border-color: var(--c-gold);
    box-shadow: 0 0 0 2px rgba(0,64,152,0.14);
  }
}
.edit-actions {
  display: flex; justify-content: flex-end; gap: 8px;
  padding-top: 10px; border-top: 1px solid var(--c-border);
}

.faq-list {
  display: flex; flex-direction: column;
}
.faq-item {
  padding: 12px 0; border-bottom: 1px solid var(--c-border);
  &.last { border-bottom: none; }
  &.editing { background: var(--c-paper); border-radius: var(--radius-sm); padding: 12px; margin: 0 -4px; }
}
.faq-view { display: flex; flex-direction: column; gap: 4px; }
.faq-q {
  display: flex; align-items: center; gap: 6px;
  font-size: 13px; font-weight: 500; color: var(--c-ink);
}
.faq-ico { color: var(--c-gold); flex-shrink: 0; }
.faq-a { font-size: 12px; color: var(--c-ink-3); line-height: 1.6; padding-left: 18px; }
.faq-foot {
  display: flex; align-items: center; gap: 8px; padding-left: 18px; margin-top: 4px;
}
.item-date { font-size: 11px; color: var(--c-ink-4); }
.char-hint { font-size: 11px; color: var(--c-ink-4); }
.item-ops { margin-left: auto; display: flex; gap: 0; }

.empty-state {
  display: flex; flex-direction: column; align-items: center; gap: 8px;
  padding: 40px 0; color: var(--c-ink-4);
  p { font-size: 12px; margin: 0; }
}

.char-count { font-size: 11px; color: var(--c-ink-4); text-align: right; margin-top: 4px; }

/* ── 文本段落 ──────────────────────────────────── */
.text-grid {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(340px, 1fr)); gap: 12px;
}
.text-card { padding: 14px 16px; }
.text-view-header {
  display: flex; align-items: center; gap: 8px; margin-bottom: 8px;
}
.text-title { font-size: 14px; font-weight: 500; color: var(--c-ink); flex: 1; min-width: 0; }
.text-preview {
  font-size: 12px; color: var(--c-ink-3); line-height: 1.7;
  display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical;
  overflow: hidden; margin: 0 0 8px;
}

/* ── 数据大屏 ─────────────────────────────────── */
.range-tabs {
  display: flex; border: 1px solid var(--c-border); border-radius: var(--radius-sm); overflow: hidden;
  .range-btn {
    padding: 4px 12px; font-size: 12px; border: none; background: var(--c-surface);
    color: var(--c-ink-3); cursor: pointer; transition: all .15s; font-family: var(--font-sans);
    &.active { background: var(--c-gold-bg); color: var(--c-gold); }
    &:hover:not(.active) { background: var(--c-paper); }
  }
}

.update-time { font-size: 11px; color: var(--c-ink-4); }

.kpi-row {
  display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; margin-bottom: 20px;
}

.kpi-card {
  background: var(--c-surface); border: 1px solid var(--c-border);
  border-radius: var(--radius-lg); padding: 20px;
  display: flex; flex-direction: column;
  box-shadow: var(--shadow-sm); transition: all .2s;
  &:hover { box-shadow: var(--shadow); transform: translateY(-2px); }
}

.kpi-card-top {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 14px;

  .kpi-label { font-size: 12px; color: var(--c-ink-3); }

  .kpi-icon-wrap {
    width: 32px; height: 32px; border-radius: var(--radius-sm);
    display: flex; align-items: center; justify-content: center; flex-shrink: 0;
    transition: transform 0.2s cubic-bezier(0.25, 1, 0.5, 1);
  }
}

.kpi-card:hover .kpi-icon-wrap { transform: scale(1.12); }

.kpi-value { font-size: 32px; font-weight: 700; font-family: var(--font-serif); line-height: 1; margin-bottom: 8px; }

.kpi-trend {
  font-size: 11px; display: flex; align-items: center; gap: 3px;
  &.muted { color: var(--c-ink-4); }
  &.up   { color: var(--c-green); }
  &.down { color: var(--c-red); }
}

.charts-grid {
  display: grid; grid-template-columns: 1.3fr 1fr; gap: 16px;
}

.chart-card { height: 290px; display: flex; flex-direction: column; }

.bar-chart {
  flex: 1; display: flex; align-items: flex-end; gap: 6px; padding-top: 8px;
  .bar-col {
    flex: 1; display: flex; flex-direction: column; align-items: center; gap: 4px; height: 100%;
    cursor: default;
    &:hover .bar-fill { opacity: 1; background: var(--c-gold-2); box-shadow: 0 0 8px rgba(0,64,152,0.22); }
    &:hover .bar-day  { color: var(--c-ink-2); }
    &:hover .bar-val  { color: var(--c-ink); font-weight: 600; }
  }
  .bar-track { flex: 1; width: 100%; display: flex; align-items: flex-end; }
  .bar-fill {
    width: 100%; background: var(--c-gold); border-radius: 3px 3px 0 0; min-height: 3px;
    transition: height .4s, background .15s, opacity .15s, box-shadow .15s;
    opacity: 0.78;
    transform-origin: bottom;
    animation: barGrow 0.55s cubic-bezier(0.34, 1.4, 0.64, 1) both;
  }
  .bar-col:nth-child(1) .bar-fill { animation-delay: 0.04s; }
  .bar-col:nth-child(2) .bar-fill { animation-delay: 0.08s; }
  .bar-col:nth-child(3) .bar-fill { animation-delay: 0.12s; }
  .bar-col:nth-child(4) .bar-fill { animation-delay: 0.16s; }
  .bar-col:nth-child(5) .bar-fill { animation-delay: 0.20s; }
  .bar-col:nth-child(6) .bar-fill { animation-delay: 0.24s; }
  .bar-col:nth-child(7) .bar-fill { animation-delay: 0.28s; }
  .bar-day  { font-size: 10px; color: var(--c-ink-4); transition: color .15s; }
  .bar-val  { font-size: 10px; color: var(--c-ink-3); transition: color .15s, font-weight .15s; }
}

.hot-list {
  flex: 1; overflow-y: auto; display: flex; flex-direction: column; gap: 7px;
  .hot-item {
    display:flex; align-items:center; gap:7px;
    padding: 3px 4px; border-radius: var(--radius-xs);
    transition: background 0.15s;
    cursor: default;
    &:hover { background: var(--c-paper-2);
      .hot-q  { color: var(--c-ink); }
      .hot-fill { filter: brightness(1.18); }
      .hot-n  { color: var(--c-ink-2); font-weight: 600; }
    }
  }
  .hot-rank { width:18px; height:18px; border-radius:50%; background:var(--c-paper); color:var(--c-ink-4); font-size:10px; font-weight:700; display:flex; align-items:center; justify-content:center; flex-shrink:0;
    &.top { background:var(--c-gold-bg); color:var(--c-gold); } }
  .hot-q   { flex:1; font-size:12px; color:var(--c-ink-2); white-space:nowrap; overflow:hidden; text-overflow:ellipsis; transition: color .15s; }
  .hot-bar { width:80px; height:5px; border-radius:3px; background:var(--c-border); flex-shrink:0; overflow: hidden; }
  .hot-fill{
    height:100%; border-radius:3px; background: var(--c-gold-3);
    transform-origin: left;
    animation: barSlide 0.45s cubic-bezier(0.34, 1.2, 0.64, 1) both;
    transition: filter .15s;
  }
  .hot-item:nth-child(1)  .hot-fill { animation-delay: 0.05s; }
  .hot-item:nth-child(2)  .hot-fill { animation-delay: 0.09s; }
  .hot-item:nth-child(3)  .hot-fill { animation-delay: 0.13s; }
  .hot-item:nth-child(4)  .hot-fill { animation-delay: 0.17s; }
  .hot-item:nth-child(5)  .hot-fill { animation-delay: 0.21s; }
  .hot-item:nth-child(6)  .hot-fill { animation-delay: 0.25s; }
  .hot-item:nth-child(7)  .hot-fill { animation-delay: 0.29s; }
  .hot-item:nth-child(8)  .hot-fill { animation-delay: 0.33s; }
  .hot-item:nth-child(9)  .hot-fill { animation-delay: 0.37s; }
  .hot-item:nth-child(10) .hot-fill { animation-delay: 0.41s; }
  .hot-n   { font-size:10px; color:var(--c-ink-4); width:28px; text-align:right; padding-right:6px; transition: color .15s, font-weight .15s; }
}

.sat-wrap { display: flex; align-items: flex-start; gap: 24px; flex: 1; }
.sat-big {
  .sat-num  { font-size: 44px; font-weight: 700; color: var(--c-ink); font-family: var(--font-serif); }
  .sat-unit { font-size: 14px; color: var(--c-ink-4); }
}
.star-dist { flex: 1; display: flex; flex-direction: column; gap: 7px; justify-content: center;
  .star-row {
    display:flex; align-items:center; gap:7px;
    padding: 3px 4px; border-radius: var(--radius-xs);
    transition: background 0.15s;
    cursor: default;
    &:hover { background: var(--c-paper-2);
      .star-fill { filter: brightness(1.15); }
      .star-pct  { color: var(--c-ink-2); font-weight: 600; }
    }
    .star-n    { font-size:11px; color:var(--c-ink-4); width:14px; text-align:right; }
    .star-track{ flex:1; height:6px; border-radius:3px; background:var(--c-border); overflow: hidden; }
    .star-fill {
      height:100%; border-radius:3px;
      transform-origin: left;
      animation: barSlide 0.45s cubic-bezier(0.34, 1.2, 0.64, 1) both;
      transition: filter .15s;
    }
    .star-pct  { font-size:10px; color:var(--c-ink-4); width:28px; transition: color .15s, font-weight .15s; }
  }
  .star-row:nth-child(1) .star-fill { animation-delay: 0.05s; }
  .star-row:nth-child(2) .star-fill { animation-delay: 0.10s; }
  .star-row:nth-child(3) .star-fill { animation-delay: 0.15s; }
  .star-row:nth-child(4) .star-fill { animation-delay: 0.20s; }
  .star-row:nth-child(5) .star-fill { animation-delay: 0.25s; }
}

.spot-list { display:flex; flex-direction:column; gap:10px; flex:1; justify-content:center;
  .spot-item {
    display:flex; align-items:center; gap:9px;
    padding: 3px 4px; border-radius: var(--radius-xs);
    transition: background 0.15s;
    cursor: default;
    &:hover { background: var(--c-paper-2);
      .spot-name { color: var(--c-ink); font-weight: 500; }
      .spot-fill { filter: brightness(1.15); }
      .spot-pct  { color: var(--c-ink-2); font-weight: 600; }
    }
    .spot-name  { font-size:12px; color:var(--c-ink-2); width:70px; transition: color .15s, font-weight .15s; }
    .spot-track { flex:1; height:8px; border-radius:4px; background:var(--c-border); overflow: hidden; }
    .spot-fill  {
      height:100%; border-radius:4px;
      transform-origin: left;
      animation: barSlide 0.45s cubic-bezier(0.34, 1.2, 0.64, 1) both;
      transition: filter .15s;
    }
    .spot-pct   { font-size:11px; color:var(--c-ink-4); width:32px; text-align:right; transition: color .15s, font-weight .15s; }
  }
  .spot-item:nth-child(1) .spot-fill { animation-delay: 0.05s; }
  .spot-item:nth-child(2) .spot-fill { animation-delay: 0.10s; }
  .spot-item:nth-child(3) .spot-fill { animation-delay: 0.15s; }
  .spot-item:nth-child(4) .spot-fill { animation-delay: 0.20s; }
  .spot-item:nth-child(5) .spot-fill { animation-delay: 0.25s; }
  .spot-item:nth-child(6) .spot-fill { animation-delay: 0.30s; }
}

/* ── 感受度报告（BI 白卡范式：KPI条 / 主图 / 表格 / 环图） ── */
.rpt-kpi-card {
  display: flex; align-items: stretch;
  background: var(--c-surface); border: 1px solid var(--c-border);
  border-radius: var(--radius-lg); box-shadow: var(--shadow-sm);
  padding: 16px 6px;
}
.rpt-kpi { flex: 1; display: flex; align-items: center; gap: 14px; padding: 2px 22px; min-width: 0; }
.rpt-kpi-div { width: 1px; background: var(--c-border); margin: 4px 0; flex-shrink: 0; }
.rpt-kpi-ico {
  width: 44px; height: 44px; border-radius: 12px; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
  /* 粉彩图标方块（参考截图 KPI 条）：浅蓝 / 浅紫 / 浅橙 / 渐变蓝 */
  &.k0 { background: #E8F2FF; color: #2F7CF6; }
  &.k1 { background: #F1EDFF; color: #7B61FF; }
  &.k2 { background: #FFF3E6; color: #FF9A2E; }
  &.k3 { background: linear-gradient(135deg, #4DA1FF, #2E7CF6); color: #fff; }
}
.rpt-kpi-body { display: flex; flex-direction: column; gap: 3px; min-width: 0; }
.rpt-kpi-label { font-size: 12px; color: var(--c-ink-3); white-space: nowrap; }
.rpt-kpi-num {
  font-size: 26px; font-weight: 700; line-height: 1.1; color: var(--c-ink);
  font-variant-numeric: tabular-nums;
  .rpt-unit { font-style: normal; font-size: 12px; font-weight: 400; color: var(--c-ink-4); margin-left: 3px; }
}

.rpt-card-hd { display: flex; align-items: center; gap: 10px; margin-bottom: 12px; }
.rpt-card-title { font-size: 14px; font-weight: 600; color: var(--c-ink); }
.rpt-hd-sub { font-size: 11px; color: var(--c-ink-4); }
.rpt-hd-btn { margin-left: auto; }
.rpt-hd-legend {
  margin-left: auto; font-size: 11px; color: var(--c-ink-3);
  display: flex; align-items: center; gap: 5px;
  .rpt-dot { width: 8px; height: 8px; border-radius: 50%; display: inline-block; margin-left: 10px;
    &.pos { background: #35C3B2; } &.neg { background: #F5715D; } &.vol { background: rgba(79,154,240,0.45); } }
}

.rpt-ec-main { height: 280px; }
.rpt-ec-donut { height: 258px; }

/* ── 消费分析：数据来源徽章 + 营销决策卡 ── */
.cons-src-badge {
  display: inline-flex; align-items: center; gap: 5px;
  font-size: 11.5px; color: var(--c-ink-3);
  background: color-mix(in srgb, var(--color-primary, #4F5BE0) 9%, var(--c-surface));
  border: 1px solid color-mix(in srgb, var(--color-primary, #4F5BE0) 22%, transparent);
  padding: 4px 10px; border-radius: 999px; white-space: nowrap;
  svg { color: var(--color-primary, #4F5BE0); }
}
.cons-advice-list { display: flex; flex-direction: column; gap: 10px; }
.cons-advice {
  display: flex; align-items: flex-start; gap: 12px;
  padding: 13px 14px; border-radius: var(--radius-md, 10px);
  background: var(--c-surface-2, var(--c-surface));
  border: 1px solid var(--c-border);
  transition: border-color .18s, box-shadow .18s;
  &:hover { border-color: color-mix(in srgb, var(--color-primary, #4F5BE0) 40%, var(--c-border)); box-shadow: var(--shadow-sm); }
}
.cons-adv-idx {
  width: 30px; height: 30px; border-radius: 9px; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
  background: #FFF3E6; color: #FF9A2E;
}
.cons-adv-body { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 5px; }
.cons-adv-insight { font-size: 13.5px; font-weight: 600; color: var(--c-ink); line-height: 1.5; }
.cons-adv-row { font-size: 12.5px; color: var(--c-ink-3); line-height: 1.55; display: flex; gap: 7px; align-items: baseline; }
.cons-adv-tag {
  flex-shrink: 0; font-size: 11px; font-weight: 600; padding: 1px 7px; border-radius: 5px; line-height: 1.6;
  &.act { background: color-mix(in srgb, #35C3B2 16%, transparent); color: #1E8f80; }
  &.exp { background: color-mix(in srgb, #4F5BE0 14%, transparent); color: #4a55c9; }
}
.cons-adv-do {
  flex-shrink: 0; align-self: center; display: inline-flex; align-items: center; gap: 5px;
  font-size: 12px; font-weight: 500; padding: 6px 12px; border-radius: 8px; cursor: pointer;
  background: var(--color-primary, #4F5BE0); color: #fff; border: none;
  transition: filter .16s;
  &:hover { filter: brightness(1.08); }
}

.rpt-table {
  width: 100%; border-collapse: collapse; font-size: 12px;
  th { text-align: left; font-weight: 500; color: var(--c-ink-4); font-size: 11px;
       padding: 7px 10px; border-bottom: 1px solid var(--c-border); background: var(--c-paper); }
  td { padding: 9px 10px; border-bottom: 1px solid var(--c-border); color: var(--c-ink-2); }
  tbody tr:last-child td { border-bottom: none; }
  tbody tr:hover td { background: var(--c-paper); }
}
.rpt-rank {
  display: inline-flex; width: 20px; height: 20px; border-radius: 6px;
  align-items: center; justify-content: center;
  font-size: 11px; font-weight: 600; color: var(--c-ink-4); background: var(--c-paper-2);
  &.top { color: #fff; background: #2F7CF6; }
}
.rpt-td-name { color: var(--c-ink); }
.rpt-td-num { font-variant-numeric: tabular-nums; }
.rpt-track { height: 6px; border-radius: 3px; background: var(--c-border); overflow: hidden; }
.rpt-fill { height: 100%; border-radius: 3px; background: linear-gradient(90deg, #7FBCF5, #2F7CF6); }
.rpt-link {
  border: none; background: none; color: #2F7CF6; font-size: 12px; cursor: pointer; padding: 0;
  &:hover { text-decoration: underline; }
}

/* 文字报告排版（v-html 注入，需 :deep）—— markdown 分级/有序无序/引用/代码/斜体全支持 */
.rpt-doc { font-size: 13px; line-height: 1.9; color: var(--c-ink-2);
  :deep(h3) { font-size: 15px; font-weight: 700; color: var(--c-ink); margin: 18px 0 8px;
              padding-left: 10px; border-left: 4px solid var(--c-gold-3, #2F7CF6); letter-spacing: .2px; }
  :deep(h4) { font-size: 13.5px; font-weight: 600; color: var(--c-ink); margin: 14px 0 6px;
              padding-left: 9px; border-left: 3px solid #2F7CF6; }
  :deep(h5) { font-size: 12.5px; font-weight: 600; color: var(--c-ink-2); margin: 11px 0 5px; }
  :deep(h3:first-child), :deep(h4:first-child), :deep(h5:first-child) { margin-top: 2px; }
  :deep(p)  { margin: 7px 0; }
  :deep(ul), :deep(ol) { margin: 7px 0; padding-left: 22px; }
  :deep(ul) { list-style: disc; }
  :deep(ol) { list-style: decimal; }
  :deep(li) { margin: 4px 0; padding-left: 3px; }
  :deep(li::marker) { color: var(--c-gold-3, #2F7CF6); font-weight: 600; }
  :deep(b), :deep(strong) { color: var(--c-ink); font-weight: 700; }
  :deep(em) { font-style: normal; color: var(--c-gold-3, #2F7CF6); font-weight: 600; }
  :deep(code) { font-family: ui-monospace, Menlo, Consolas, monospace; font-size: 12px;
                background: var(--c-paper-2); border: 1px solid var(--c-border); border-radius: 4px; padding: 1px 5px; color: var(--c-ink); }
  :deep(blockquote) { margin: 8px 0; padding: 6px 12px; border-left: 3px solid var(--c-border);
                      background: var(--c-paper-2); border-radius: 0 6px 6px 0; color: var(--c-ink-3); }
  :deep(hr) { border: none; border-top: 1px dashed var(--c-border); margin: 14px 0; }
}

.dialogue-list { display:flex; flex-direction:column; gap:10px;
  .dialogue-item { padding:12px 14px; border-radius:var(--radius); border:1px solid var(--c-border); background:var(--c-paper); }
  .dlg-meta { display:flex; align-items:center; gap:8px; margin-bottom:7px;
    .dlg-time { font-size:11px; color:var(--c-ink-4); }
  }
  .sentiment-tag { font-size:10px; padding:1px 7px; border-radius:99px;
    &.positive { background:var(--c-green-bg); color:var(--c-green); }
    &.negative { background:var(--c-red-bg); color:var(--c-red); }
    &.neutral  { background:var(--c-paper-2); color:var(--c-ink-4); border:1px solid var(--c-border); }
  }
  .dlg-q { font-size:13px; color:var(--c-ink); margin-bottom:5px; &::before { content:'Q  '; color:var(--c-gold); font-weight:700; } }
  .dlg-a { font-size:12px; color:var(--c-ink-3); line-height:1.6; &::before { content:'A  '; color:var(--c-ink-4); } }
}

/* ── 数据大屏错误 ─────────────────────────────────── */
.dash-error-banner {
  display: flex; align-items: center; gap: 8px;
  padding: 10px 16px; border-radius: var(--radius);
  background: var(--c-red-bg); border: 1px solid rgba(190,53,53,0.2);
  color: var(--c-red); font-size: 12px; margin-bottom: 16px;
  svg { flex-shrink: 0; }
}

/* ── 知识库撤销条 ─────────────────────────────────── */
.undo-toast {
  display: flex; align-items: center; gap: 8px;
  padding: 9px 14px; border-radius: var(--radius-sm);
  background: var(--c-ink); color: rgba(250,248,244,0.88); font-size: 12px;
  margin-bottom: 14px;
}

/* ── 检索配置提示 ─────────────────────────────────── */
.config-hint {
  font-size: 11px; color: var(--c-ink-4); line-height: 1.6; margin: 0;
  padding: 4px 0 2px;
}

/* ── 工具 ─────────────────────────────────── */
.spin { animation: spin 1s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

.status-pill.pulsing { animation: status-pulse 1.8s ease-in-out infinite; }
@keyframes status-pulse {
  0%, 100% { opacity: 1; }
  50%       { opacity: 0.5; }
}

@keyframes msg-in {
  from { opacity: 0; transform: translateY(8px); }
  to   { opacity: 1; transform: translateY(0); }
}

@keyframes tab-in {
  from { opacity: 0; transform: translateY(5px); }
  to   { opacity: 1; transform: translateY(0); }
}

@keyframes barGrow {
  from { transform: scaleY(0); }
  to   { transform: scaleY(1); }
}

@keyframes barSlide {
  from { transform: scaleX(0); }
  to   { transform: scaleX(1); }
}

@media (prefers-reduced-motion: reduce) {
  .spin,
  .ai-online-dot,
  .ai-typing-dots i { animation: none !important; }

  .primary-btn, .ghost-btn, .link-btn, .kb-nav-btn,
  .nav-item svg, .bar-fill, .bar-day, .bar-val,
  .kpi-card, .kpi-icon-wrap { transition: none !important; transform: none !important; }

  .ai-bot-icon, .status-pill.pulsing,
  .ai-msg-row, .tab-content { animation: none !important; }

  .bar-fill, .hot-fill, .star-fill, .spot-fill { animation: none !important; }
}

/* ── 报告页 loading ─────────────────────────────────── */
.report-loading {
  display: flex; flex-direction: column; align-items: center; gap: 10px;
  padding: 60px 0; color: var(--c-ink-4);
  span { font-size: 13px; }
}

.chart-empty {
  display: flex; flex-direction: column; align-items: center; gap: 8px;
  padding: 30px 0; color: var(--c-ink-4); flex: 1; justify-content: center;
  svg { color: var(--c-border-2); }
  p { font-size: 12px; }
}
.chart-empty-sm { font-size:11px; color:var(--c-ink-4); padding:8px 0; }

.profile-grid {
  display: grid; grid-template-columns: 1fr 1fr; gap: 16px; flex: 1;
}
.profile-section {
  display: flex; flex-direction: column; gap: 8px;
  .profile-label { font-size:10px; color:var(--c-ink-3); font-weight:600; text-transform:uppercase; letter-spacing:.05em; margin-bottom:2px; }
}

.feature-meta {
  display:flex; gap:16px; margin-bottom:12px;
  span { font-size:11px; color:var(--c-ink-3); b { color:var(--c-ink); font-size:13px; } }
}

/* ── AI 分析助手面板 ─────────────────────────────────── */
.ai-panel {
  width: 288px;
  flex-shrink: 0;
  background: var(--c-surface);
  border-left: 1px solid var(--c-border);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  transition: width 0.22s ease;

  &.collapsed {
    width: 40px;
    .ai-messages, .ai-input-wrap, .ai-header-title, .ai-online-dot, .ai-header-ico { display: none; }
    .ai-panel-header { padding: 14px 0; justify-content: center; }
  }
}

.ai-toggle-btn {
  width: 24px; height: 24px; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
  border: none; background: transparent; cursor: pointer;
  color: var(--c-ink-3); border-radius: var(--radius-sm);
  transition: all 0.15s;
  &:hover { color: var(--c-ink); background: var(--c-paper); }
  svg { transition: transform 0.22s ease; }
  svg.flipped { transform: rotate(180deg); }
}

.ai-panel-header {
  display: flex;
  align-items: center;
  gap: 7px;
  padding: 14px 16px 13px;
  border-bottom: 1px solid var(--c-border);
  background: linear-gradient(135deg, #F6FAFF 0%, var(--c-surface) 60%);   /* 蓝晕减淡 */
  flex-shrink: 0;

  .ai-header-ico   { color: var(--c-gold-2); flex-shrink: 0; }
  .ai-header-title { font-size: 13px; font-weight: 600; color: var(--c-ink); font-family: var(--font-serif); flex: 1; }
  .ai-online-dot {
    width: 6px; height: 6px; border-radius: 50%;
    background: var(--c-green); flex-shrink: 0;
    box-shadow: 0 0 5px rgba(45,122,79,0.5);
    animation: pulse-dot 2.4s ease-in-out infinite;
  }
}

@keyframes pulse-dot {
  0%, 100% { opacity: 1; }
  50%       { opacity: 0.3; }
}

.ai-messages {
  flex: 1;
  overflow-y: auto;
  padding: 14px 12px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  scroll-behavior: smooth;
}

.ai-welcome {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  gap: 5px;
  padding: 18px 6px 8px;

  .ai-bot-icon {
    width: 46px; height: 46px;
    border-radius: 50%;
    background: #F3F8FF;
    border: 1px solid #E5EFFD;
    display: flex; align-items: center; justify-content: center;
    color: var(--c-gold-2);
    margin-bottom: 6px;
    animation: bot-float 3.2s ease-in-out infinite;
  }
  .ai-welcome-title { font-size: 13px; font-weight: 600; color: var(--c-ink); }
  .ai-welcome-sub   { font-size: 11px; color: var(--c-ink-4); line-height: 1.65; margin-top: 2px; }
}

@keyframes bot-float {
  0%, 100% { transform: translateY(0); }
  50%       { transform: translateY(-5px); }
}

.ai-quick-list {
  display: flex;
  flex-direction: column;
  gap: 5px;
  margin-top: 12px;
  width: 100%;

  .ai-quick-chip {
    padding: 7px 11px;
    border-radius: var(--radius-sm);
    border: 1px solid #E5EFFD;
    background: #F7FAFF;
    color: #4C8DF7;
    font-size: 12px;
    cursor: pointer;
    font-family: var(--font-sans);
    transition: all .15s;
    display: flex; align-items: center; justify-content: space-between;

    &::after {
      content: '→';
      font-size: 11px;
      opacity: 0;
      transform: translateX(-6px);
      transition: opacity .15s, transform .15s;
      flex-shrink: 0;
    }
    &:hover {
      background: var(--c-gold-2); color: #fff; border-color: var(--c-gold-2);
      &::after { opacity: 1; transform: translateX(0); }
    }
  }
}

.ai-msg-row {
  display: flex;
  gap: 6px;
  align-items: flex-start;
  animation: msg-in 0.22s cubic-bezier(0.25, 1, 0.5, 1);
  &.user { flex-direction: row-reverse; }

  .ai-msg-icon {
    width: 22px; height: 22px;
    border-radius: 50%;
    background: #F3F8FF;
    border: 1px solid #E5EFFD;
    display: flex; align-items: center; justify-content: center;
    color: var(--c-gold-2);
    flex-shrink: 0;
    margin-top: 2px;
  }
}

.ai-bubble {
  max-width: 86%;
  padding: 8px 11px;
  font-size: 12px;
  line-height: 1.7;
  word-break: break-word;
  white-space: pre-wrap;

  &.assistant {
    background: var(--c-paper);
    border: 1px solid var(--c-border);
    color: var(--c-ink-2);
    border-radius: 2px 12px 12px 12px;
  }
  &.user {
    background: var(--c-gold);
    color: #fff;
    border-radius: 12px 2px 12px 12px;
  }
  &.error {
    background: var(--c-red-bg);
    border-color: rgba(190,53,53,0.2);
    color: var(--c-red);
  }
}

/* AI 助手 markdown 输出（v-html 渲染，:deep 穿透 scoped；覆盖气泡的 pre-wrap） */
.ai-md { white-space: normal; }
.ai-md :deep(p) { margin: 0 0 6px; }
.ai-md :deep(p:last-child) { margin-bottom: 0; }
.ai-md :deep(h4) {
  font-size: 12.5px; font-weight: 700; color: var(--c-ink);
  margin: 8px 0 5px; padding-left: 7px; border-left: 3px solid var(--c-gold-2);
}
.ai-md :deep(h4:first-child) { margin-top: 0; }
.ai-md :deep(ul), .ai-md :deep(ol) { margin: 0 0 6px; padding-left: 18px; }
.ai-md :deep(ul) { list-style: disc; }
.ai-md :deep(ol) { list-style: decimal; }
.ai-md :deep(ul:last-child), .ai-md :deep(ol:last-child) { margin-bottom: 0; }
.ai-md :deep(li) { margin: 2px 0; }
.ai-md :deep(li::marker) { color: var(--c-gold-2); }
.ai-md :deep(h3) { font-size: 13px; font-weight: 700; color: var(--c-ink); margin: 8px 0 5px; padding-left: 7px; border-left: 3px solid var(--c-gold-2); }
.ai-md :deep(h3:first-child) { margin-top: 0; }
.ai-md :deep(h5) { font-size: 12px; font-weight: 600; color: var(--c-ink-2); margin: 6px 0 4px; }
.ai-md :deep(em) { font-style: normal; color: var(--c-gold-2); font-weight: 600; }
.ai-md :deep(blockquote) { margin: 5px 0; padding: 4px 10px; border-left: 3px solid var(--c-border); background: var(--c-paper-2); border-radius: 0 5px 5px 0; color: var(--c-ink-3); }
.ai-md :deep(b) { color: var(--c-ink); font-weight: 600; }
.ai-md :deep(code) {
  font-size: 11px; padding: 1px 5px; border-radius: 4px;
  background: var(--c-paper-2); border: 1px solid var(--c-border);
  color: var(--c-gold-dark);
}
.ai-md :deep(hr) { border: none; border-top: 1px solid var(--c-border); margin: 7px 0; }

.ai-typing-dots {
  display: inline-flex;
  gap: 4px;
  align-items: center;
  padding: 3px 0;

  i {
    display: block;
    width: 5px; height: 5px;
    border-radius: 50%;
    background: var(--c-ink-4);
    animation: dot-bounce 1.4s ease-in-out infinite;
    &:nth-child(2) { animation-delay: .2s; }
    &:nth-child(3) { animation-delay: .4s; }
  }
}

@keyframes dot-bounce {
  0%, 60%, 100% { transform: translateY(0); opacity: .4; }
  30%            { transform: translateY(-5px); opacity: 1; }
}

.ai-input-wrap {
  display: flex;
  align-items: flex-end;
  gap: 6px;
  padding: 10px 12px;
  border-top: 1px solid var(--c-border);
  background: var(--c-surface);
  flex-shrink: 0;
}

.ai-input {
  flex: 1;
  border: 1px solid var(--c-border);
  border-radius: var(--radius-sm);
  padding: 7px 10px;
  font-size: 12px;
  font-family: var(--font-sans);
  color: var(--c-ink);
  background: var(--c-paper);
  outline: none;
  resize: none;
  min-height: 34px;
  max-height: 120px;
  line-height: 1.5;
  transition: border-color .15s;

  &::placeholder { color: var(--c-ink-4); }
  &:focus         { border-color: var(--c-gold); }
  &:disabled      { opacity: .55; }
}

.ai-send {
  width: 34px; height: 34px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--c-border);
  background: var(--c-paper);
  color: var(--c-ink-4);
  display: flex; align-items: center; justify-content: center;
  cursor: pointer;
  transition: all .15s;
  flex-shrink: 0;

  &.active                        { background: var(--c-gold); border-color: var(--c-gold); color: #fff; }
  &:not(:disabled):hover:not(.active) { border-color: var(--c-gold-bdr); color: var(--c-gold); }
  &:disabled                      { cursor: not-allowed; opacity: .45; }
}

/* ── 响应式断点 ───────────────────────────────── */

/* ≤900px: 侧边栏收窄为仅图标模式，AI 面板收起 */
@media (max-width: 900px) {
  .ai-panel { display: none; }
  .sidebar {
    width: 54px;
    flex-shrink: 0;

    .sidebar-logo span,
    .sidebar-footer { display: none; }
  }

  .nav-item {
    justify-content: center;
    padding: 10px;
    gap: 0;
    span { display: none; }
  }

  .tab-content {
    padding: 20px 18px;
  }

  .two-col,
  .av2-layout,
  .charts-grid {
    grid-template-columns: 1fr;
  }
  .av2-col-preview { position: static; top: auto; }
}

/* 触摸设备：放大最小触控区域至 44×44px */
@media (pointer: coarse) {
  .link-btn {
    padding: 6px 10px;
    min-height: 36px;
    display: inline-flex;
    align-items: center;
  }

  .ghost-btn.sm {
    padding: 7px 12px;
    font-size: 12px;
  }
}

/* ══ 顶部导航栏 ══ */
.top-nav {
  position: fixed;
  top: 0; left: 0; right: 0;
  height: 62px;          /* 52 → 62（1.2 倍加高，元素同步大两号） */
  background: #FFFFFF;   /* 纯白顶栏（参考截图）；深色模式由 admin-dark.css 覆盖 */
  border-bottom: 1px solid var(--c-border);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px 0 16px;
  z-index: 9999;
  flex-shrink: 0;
}

.tn-left {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}

/* 顶栏中段：实时弹幕迷你条「游客正在问」（占用品牌与时钟之间的空白区） */
.tn-mid {
  flex: 1;
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 10px;
  margin: 0 22px;
}
.tn-dmk-label {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 12.5px;
  color: var(--c-ink-4);
  flex-shrink: 0;
  user-select: none;
}
.tn-dmk-label svg { color: var(--c-gold-2); }
.tn-dmk { flex: 1; }

/* ── 品牌区强化（方案A·渐变品牌字）：logo 34 + 渐变蓝特粗 20px，子标题淡化+竖线隔开 ── */
.tn-logo {
  width: 34px;
  height: 34px;
  object-fit: contain;
}

.tn-brand {
  font-size: 20px;
  font-weight: 800;
  letter-spacing: 1.5px;
  font-family: var(--font-serif);
  color: #1B5FD9;                       /* 不支持 background-clip:text 时的兜底色 */
  background: linear-gradient(135deg, #1B5FD9 0%, #5B9CF8 100%);
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
}

.tn-divider {
  width: 1px;
  height: 18px;
  background: var(--c-border-2);
  margin: 0 12px 0 10px;
  flex-shrink: 0;
}

.tn-scenic {
  font-size: 12px;
  color: var(--c-ink-4);
  font-weight: 400;
  letter-spacing: 0.5px;
}

.tn-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.tn-lang {
  display: flex;
  background: rgba(255,255,255,0.08);
  border-radius: 7px;
  padding: 2px;
  gap: 1px;
}

.tn-lang-btn {
  padding: 4px 9px;
  border-radius: 5px;
  border: none;
  background: transparent;
  color: rgba(255,255,255,0.5);
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  font-family: var(--font-sans);
  transition: all 0.15s;

  &.active {
    background: rgba(255,255,255,0.95);
    color: #0B1829;
    font-weight: 700;
  }

  &:not(.active):hover {
    color: rgba(255,255,255,0.85);
    background: rgba(255,255,255,0.12);
  }
}

.tn-gps {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: rgba(255,255,255,0.5);
  background: rgba(255,255,255,0.07);
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 20px;
  padding: 4px 10px;

  svg { color: var(--c-gold); }
}

.tn-date {
  font-size: 13px;
  color: var(--c-ink-4);
  margin-right: 10px;
  font-variant-numeric: tabular-nums;
}

.tn-clock {
  font-size: 15px;
  font-weight: 600;
  color: var(--c-ink);
  font-variant-numeric: tabular-nums;
  letter-spacing: 1px;
  min-width: 64px;
  text-align: center;
}

.tn-return-btn {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 6px 13px;
  border-radius: 7px;
  border: 1px solid rgba(255,255,255,0.18);
  background: rgba(255,255,255,0.06);
  color: rgba(255,255,255,0.8);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  font-family: var(--font-sans);
  transition: all 0.15s;
  white-space: nowrap;

  &:hover {
    background: rgba(255,255,255,0.12);
    border-color: rgba(255,255,255,0.3);
    color: #fff;
  }
}

/* 整体下移 62px 避免被顶部栏遮住（与 .top-nav height 联动） */
.admin-layout {
  padding-top: 62px !important;
}


/* ══ 数据大屏 · 暗玻璃悬浮（Dark Glassmorphism）══════════════════════
   底 = 软深灰蓝 + 紫/青/粉三个环境光斑；卡片 = 磨砂玻璃浮在光上 */
.tab-dashboard-screen {
  position: fixed; inset: 0; z-index: 9999;
  background: #12141F;
  display: flex; flex-direction: column;
  overflow: hidden;
  font-family: var(--font-sans);
  background-image:
    radial-gradient(42% 55% at 10% 12%, rgba(124,58,237,0.30), transparent 66%),
    radial-gradient(36% 48% at 92% 22%, rgba(34,211,238,0.20), transparent 66%),
    radial-gradient(40% 52% at 55% 108%, rgba(236,72,153,0.18), transparent 66%);
}
.dsh-hd {
  height: 56px; flex-shrink: 0;
  display: grid; grid-template-columns: 1fr auto 1fr;
  align-items: center; padding: 0 20px;
  background: rgba(255,255,255,0.04);
  border-bottom: 1px solid rgba(255,255,255,0.10);
  -webkit-backdrop-filter: blur(18px); backdrop-filter: blur(18px);
  position: relative;
}
.dsh-hd::after {
  content: "";
  position: absolute; bottom: 0; left: 14%; right: 14%;
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(167,139,250,0.55), rgba(34,211,238,0.45), transparent);
}
.dsh-hd-l { display: flex; align-items: center; gap: 14px; }
.dsh-scenic { font-size: 13px; color: rgba(232,234,242,0.62); font-weight: 500; }
.dsh-ranges {
  display: flex; gap: 1px;
  background: rgba(255,255,255,0.06);
  border: 1px solid rgba(255,255,255,0.12);
  border-radius: 999px; padding: 2px;
}
.dsh-rb {
  padding: 3px 11px; border: none; background: transparent;
  color: rgba(232,234,242,0.5); font-size: 12px; cursor: pointer;
  border-radius: 999px; transition: all .12s; font-family: var(--font-sans);
}
.dsh-rb.active {
  background: linear-gradient(120deg, #7C3AED, #8B5CF6);
  color: #fff; box-shadow: 0 0 10px rgba(139,92,246,0.45);
}
.dsh-rb:hover:not(.active) { color: rgba(232,234,242,0.85); }
.dsh-hd-c {
  display: flex; align-items: center; gap: 14px;
  font-size: 21px; font-weight: 700; color: #F0F1F7;
  letter-spacing: 0.12em; font-family: var(--font-serif);
  text-shadow: 0 0 28px rgba(167,139,250,0.45);
}
.dsh-deco-line {
  display: inline-block; width: 36px; height: 2px;
  background: linear-gradient(90deg, transparent, #A78BFA); border-radius: 1px;
}
.dsh-deco-r { background: linear-gradient(90deg, #22D3EE, transparent); }
.dsh-hd-r { display: flex; align-items: center; justify-content: flex-end; gap: 12px; }
.dsh-hdate { font-size: 13px; color: rgba(232,234,242,0.5); }
.dsh-htime { font-size: 18px; font-weight: 700; color: #F0F1F7; font-variant-numeric: tabular-nums; letter-spacing: 0.05em; }
.dsh-hbtn {
  width: 28px; height: 28px;
  display: flex; align-items: center; justify-content: center;
  background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.14);
  color: rgba(232,234,242,0.62); border-radius: 8px; cursor: pointer; transition: all .12s;
}
.dsh-hbtn:hover { background: rgba(255,255,255,0.14); color: #fff; }
.dsh-hbtn:disabled { opacity: .4; cursor: not-allowed; }
.dsh-hbtn.dsh-exit:hover { border-color: rgba(251,113,133,0.5); color: #fb7185; background: rgba(251,113,133,0.08); }
/* 退出大屏带文字，宽度自适应 */
.dsh-hbtn.dsh-exit { width: auto; padding: 0 10px; gap: 5px; font-size: 13px; }
.dsh-exit-txt { white-space: nowrap; }
.dsh-error-bar {
  display: flex; align-items: center; gap: 8px;
  padding: 8px 20px; background: rgba(251,113,133,0.1);
  border-bottom: 1px solid rgba(251,113,133,0.25);
  font-size: 13px; color: #fb7185; flex-shrink: 0;
}
.dsh-error-bar button {
  margin-left: auto; background: none; border: 1px solid rgba(251,113,133,0.4);
  color: #fb7185; padding: 2px 10px; border-radius: 3px; cursor: pointer; font-size: 12px;
}
/* 大屏弹幕带：头部正下方横贯全屏，3 轨 90px；胶囊直接飘在光斑底色上（不加背景板） */
.dsh-dmk {
  flex-shrink: 0;
  margin: 4px 16px 0;
}

.dsh-body {
  flex: 1;
  /* 左右两栏加宽（客群画像/时段热度/实时客流需要更多横向空间），中栏相应收窄 → 仍保持不等宽交错 */
  display: grid; grid-template-columns: 344px 1fr 376px;
  gap: 12px; padding: 12px 16px 12px;
  overflow: hidden; min-height: 0;
}
.dsh-col { display: flex; flex-direction: column; gap: 12px; min-height: 0; overflow: hidden; }
.dsh-col-c { display: flex; flex-direction: column; gap: 12px; min-height: 0; overflow: hidden; }
.dsh-panel {
  background: rgba(255,255,255,0.06);
  border: 1px solid rgba(255,255,255,0.13);
  border-radius: 16px; padding: 12px 14px;
  position: relative; flex-shrink: 0;
  -webkit-backdrop-filter: blur(18px); backdrop-filter: blur(18px);
  box-shadow: 0 8px 28px rgba(0,0,0,0.35), inset 0 1px 0 rgba(255,255,255,0.10);
}
.dsh-pf { flex: 1; display: flex; flex-direction: column; min-height: 0; }
/* 交错节拍：同栏面板配比不同，横向边界互不对齐 */
.dsh-pf.f-lg { flex: 1.3; }
.dsh-pf.f-sm { flex: 0.85; }
.dsh-pf.f-xs { flex: 0.95; }    /* 时段热度：加高，给横轴刻度留出显示空间 */
.dsh-pf.f-xl { flex: 1.35; }    /* 客群画像：加高防标签/图例挤压 */
/* 防挤压保险：面板最低高度略降，避免高缩放/矮视口下左右栏内容溢出压到底部数据带 */
.dsh-pf { min-height: 116px; }
.dsh-pm { flex: 0 0 auto; }
.dsh-phd {
  font-size: 13px; font-weight: 600; color: rgba(232,234,242,0.78);
  letter-spacing: 1.5px;
  padding-bottom: 8px; margin-bottom: 6px;
  border-bottom: 1px solid rgba(255,255,255,0.08);
  display: flex; align-items: center; gap: 7px; flex-shrink: 0;
}
.dsh-phd::before {
  content: "";
  width: 3px; height: 12px;
  background: linear-gradient(180deg, #A78BFA, #22D3EE);
  border-radius: 2px; flex-shrink: 0;
  box-shadow: 0 0 6px rgba(139,92,246,0.55);
}
.dsh-pmeta { font-size: 11px; color: rgba(232,234,242,0.38); margin-left: auto; font-weight: 400; letter-spacing: 0; }
.dsh-sat-n { margin-left: auto; font-size: 19px; font-weight: 700; color: #a78bfa; letter-spacing: 0; }
.dsh-sat-n small { font-size: 12px; color: rgba(232,234,242,0.4); }
.dsh-ec { width: 100%; }
/* 趋势主图随面板弹性伸缩（勿用 vh 定高：弹幕带/小屏会挤矮面板导致图表溢出压下排） */
.dsh-ec-main { flex: 1; min-height: 104px; height: auto; }
/* 图表尺寸统一：除趋势主图外，全部撑满面板、同一最小高度（min-height 只在压缩时生效，正常 height:100% 撑满，故调低不影响常规分辨率、只给矮视口让出收缩空间） */
.dsh-ec-md, .dsh-ec-sm, .dsh-ec-lg { height: 100%; min-height: 92px; }
.dsh-pm { height: calc(44% - 8px); display: flex; flex-direction: column; }
.dsh-r2 {
  flex: 1; display: grid; grid-template-columns: 1.25fr 1fr;   /* 中栏下排也不对称 */
  gap: 12px; min-height: 0;
}
/* 底部决策数据带：三块不等宽面板（延续交错原则），高度自适应视口 */
.dsh-strip {
  flex-shrink: 0;
  display: grid; grid-template-columns: 1fr 1.05fr 0.95fr 1.15fr;  /* 4 格：消费结构/年龄/同行规模/客单价分层·营收贡献 */
  gap: 12px; padding: 0 16px 12px;
  height: clamp(196px, 26vh, 264px);   /* 收窄：给上方 body（客群画像/时段热度所在栏）让出高度，防矮视口/高缩放下底部数据带压住上排面板 */
  min-height: 0;
}
.dsh-strip .dsh-panel { display: flex; flex-direction: column; min-height: 0; }
.dsh-r2 .dsh-panel { flex: 1; display: flex; flex-direction: column; }
.dsh-kpi-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
.dsh-kpi {
  background: rgba(255,255,255,0.05);
  border: 1px solid rgba(255,255,255,0.10);
  border-radius: 12px; padding: 9px 11px;
  display: flex; align-items: center; gap: 8px;
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.08);
}
.dsh-kpi-ico { flex-shrink: 0; filter: drop-shadow(0 0 6px currentColor); }
.dsh-kpi-body { flex: 1; min-width: 0; }
.dsh-kpi-val { font-size: 17px; font-weight: 700; line-height: 1.2; font-variant-numeric: tabular-nums; }
.dsh-kpi-lbl { font-size: 10px; color: rgba(232,234,242,0.45); margin-top: 2px; }
.sidebar-theme-row {
  padding: 8px 8px 4px;
  border-top: 1px solid var(--c-border);
  margin-top: 4px;
}
.sidebar-theme-btn {
  width: 100%; display: flex; align-items: center; gap: 7px;
  padding: 7px 10px; border-radius: 6px; border: none; cursor: pointer;
  font-size: 13px; font-family: var(--font-sans);
  color: var(--c-ink-3); background: transparent;
  transition: background .12s, color .12s;
}
.sidebar-theme-btn:hover { background: var(--c-paper-2); color: var(--c-ink); }

/* ── 侧栏分组标签 + 大屏启动卡 ── */
.nav-group-label {
  font-size: 11px; letter-spacing: 2.5px; font-weight: 600;
  color: var(--c-ink-4); padding: 12px 14px 5px; user-select: none;
}
.bigscreen-card {
  margin: 4px 10px 0; width: calc(100% - 20px);
  display: flex; align-items: center; gap: 10px; text-align: left;
  padding: 11px 13px; border: none; border-radius: 12px; cursor: pointer;
  background: linear-gradient(135deg, var(--c-gold) 0%, var(--c-gold-2) 100%);
  color: #fff; font-family: var(--font-sans);
  box-shadow: var(--shadow-sm);
  transition: filter .15s, transform .12s, box-shadow .15s;
}
.bigscreen-card:hover { filter: brightness(1.1); box-shadow: var(--shadow); }
.bigscreen-card:active { transform: translateY(1px); }
.bs-ico { display: flex; flex-shrink: 0; }
.bs-txt { display: flex; flex-direction: column; gap: 1px; min-width: 0; }
.bs-txt b { font-size: 14px; font-weight: 600; }
.bs-txt i { font-style: normal; font-size: 11px; opacity: .78; }
.sat-score {
  display: flex;
  align-items: baseline;
  gap: 2px;
  padding: 2px 0;
}
.sat-num-big {
  font-size: 28px;
  font-weight: 700;
  color: var(--c-gold);
  font-variant-numeric: tabular-nums;
}
.sat-unit-sm { font-size: 12px; color: var(--c-ink-4); }
.feature-meta-sm {
  font-size: 11px;
  color: var(--c-ink-4);
  margin-bottom: 4px;
}
.feature-meta-sm b { color: var(--c-ink-2); font-weight: 600; }

/* ── 形象管理·配置台 ── */
.full-btn { width: 100%; justify-content: center; }
.mt8 { margin-top: 8px; }

.av-filters { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 12px; }
.av-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(96px, 1fr)); gap: 10px; }
.av-card {
  position: relative; border: 1px solid var(--c-border); border-radius: var(--radius-sm);
  overflow: hidden; background: rgba(255,255,255,0.03); cursor: pointer; padding: 0;
  transition: border-color .2s, transform .1s;
  img { width: 100%; aspect-ratio: 4/5; object-fit: cover; object-position: top; display: block; }
  .av-name { display: block; font-size: 11px; font-weight: 500; color: var(--c-ink-2);
    padding: 4px 5px; text-align: center; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  &:hover { border-color: var(--c-gold-bdr); }
  &.sel { border-color: var(--c-gold); box-shadow: 0 0 0 1px var(--c-gold); }
  &.soon { opacity: .55; cursor: not-allowed; img { filter: grayscale(.4); } }
  &:active:not(.soon) { transform: scale(.97); }
  .av-check { position: absolute; top: 4px; right: 4px; color: var(--c-gold);
    background: rgba(0,0,0,.4); border-radius: 50%; }
  .av-badge.soon { position: absolute; top: 4px; left: 4px; font-size: 9px;
    background: rgba(0,0,0,.55); color: rgba(255,255,255,.8); padding: 1px 5px; border-radius: 8px; }
}
.av-empty { grid-column: 1/-1; text-align: center; font-size: 12px; color: var(--c-ink-4); padding: 16px 0; }

.av-wardrobe { display: flex; gap: 8px; overflow-x: auto; padding-bottom: 4px; }
.wd-card {
  flex: 0 0 64px; border: 1px solid var(--c-border); border-radius: var(--radius-sm);
  overflow: hidden; background: rgba(255,255,255,0.03); cursor: pointer; padding: 0;
  img { width: 64px; height: 80px; object-fit: cover; object-position: top; display: block; }
  span { display: block; font-size: 10px; color: var(--c-ink-2); padding: 3px;
    text-align: center; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  &.sel { border-color: var(--c-gold); box-shadow: 0 0 0 1px var(--c-gold); }
}

.section-hint { font-size: 11px; color: var(--c-ink-4); margin: 10px 0 0; line-height: 1.5; }

/* 音色 / 场景背景：各占一行的下拉 */
.av-select-row { display: flex; flex-direction: column; gap: 14px; }
.av-select-item { min-width: 0; display: flex; flex-direction: column; gap: 7px; }
.av-select-label {
  display: inline-flex; align-items: center; gap: 6px;
  font-size: 13px; font-weight: 600; color: var(--c-ink-2);
}
.av-select { width: 100%; }
/* 下拉选项内容（.opt-*）的样式在全局 main.css 里（popper 被 teleport 到 body，scoped 触及不到） */

.preview-video { width: 100%; height: 100%; object-fit: cover; background: #05060a; }
.preview-applying {
  position: absolute; inset: 0; display: flex; align-items: center; justify-content: center; gap: 8px;
  background: rgba(0,0,0,.45); color: #fff; font-size: 13px;
}
.preview-meta { display: flex; gap: 16px; font-size: 12px; color: var(--c-ink-4); margin-bottom: 4px; }


/* Mobile dashboard fallback */
@media (max-width: 760px) {
  .tab-dashboard-screen {
    position: fixed;
    overflow-y: auto;
    overflow-x: hidden;
    -webkit-overflow-scrolling: touch;
  }
  .dsh-hd {
    height: auto;
    min-height: 64px;
    display: flex;
    flex-wrap: wrap;
    gap: 6px 8px;
    padding: 8px 10px;
  }
  .dsh-hd::after { left: 0; right: 0; }
  .dsh-hd-c {
    order: -1;
    width: 100%;
    justify-content: center;
    gap: 8px;
    font-size: 17px;
    line-height: 1.2;
    letter-spacing: 0;
    text-align: center;
    white-space: nowrap;
  }
  .dsh-deco-line { width: 22px; }
  .dsh-hd-l,
  .dsh-hd-r {
    flex: 1 1 calc(50% - 4px);
    min-width: 0;
    gap: 6px;
  }
  .dsh-hd-r { justify-content: flex-end; }
  .dsh-scenic {
    max-width: 88px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .dsh-ranges { min-width: 0; overflow-x: auto; }
  .dsh-rb { padding: 3px 8px; white-space: nowrap; }
  .dsh-hdate { display: none; }
  .dsh-htime { font-size: 15px; }
  .dsh-hbtn { width: 28px; height: 28px; flex-shrink: 0; }
  .dsh-body {
    display: flex;
    flex-direction: column;
    gap: 8px;
    padding: 8px;
    overflow: visible;
    min-height: auto;
  }
  .dsh-strip {
    display: flex;
    flex-direction: column;
    gap: 8px;
    padding: 0 8px 8px;
    height: auto;
  }
  .dsh-strip .dsh-ec-sm { min-height: 170px; }
  .dsh-col,
  .dsh-col-c {
    gap: 8px;
    min-height: auto;
    overflow: visible;
  }
  .dsh-panel {
    width: 100%;
    flex: none;
    padding: 10px;
  }
  .dsh-pf,
  .dsh-pm {
    flex: none;
    height: auto;
    min-height: 0;
  }
  .dsh-r2 {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }
  .dsh-kpi-grid { grid-template-columns: 1fr 1fr; }
  .dsh-kpi { padding: 10px 8px; }
  .dsh-kpi-val { font-size: 19px; }
  .dsh-kpi-lbl { font-size: 11px; }
  .dsh-ec-main,
  .dsh-ec-md,
  .dsh-ec-sm,
  .dsh-ec-lg {
    height: 220px;
    min-height: 220px;
  }
}

@media (max-width: 420px) {
  .dsh-hd-c { font-size: 16px; gap: 6px; }
  .dsh-deco-line { width: 16px; }
  .dsh-hd-l { flex: 1 1 150px; }
  .dsh-hd-r { flex: 0 0 auto; }
  .dsh-scenic { max-width: 64px; }
  .dsh-rb { padding: 3px 7px; }
  .dsh-htime { font-size: 14px; }
}

/* ── 整库替换开关行 ── */
.kb-replace-row {
  display: flex; align-items: center; gap: 8px;
  margin-top: 10px; font-size: 12px; color: var(--c-text-2, #8a93a6);
  cursor: pointer;
}

/* ── 知识库体检报告 ── */
.st-items { display: flex; flex-direction: column; gap: 10px; }
.st-item {
  padding: 10px 12px; border-radius: 10px;
  background: rgba(120, 150, 220, 0.06);
  border-left: 3px solid var(--c-green, #2D7A4F);
}
.st-item.fail { border-left-color: var(--c-red, #BE3535); }
.st-q { font-size: 13px; font-weight: 600; display: flex; align-items: center; gap: 8px; }
.st-kw { font-size: 11px; margin: 6px 0 4px; opacity: 0.85; display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
.st-a { font-size: 12px; line-height: 1.7; opacity: 0.8; }


/* ── 不定态进度条（真实等待，不假装百分比）── */
.progress-bar.indeterminate { position: relative; overflow: hidden; }
.progress-bar.indeterminate .progress-fill { animation: indet-slide 1.4s ease-in-out infinite; }
@keyframes indet-slide {
  0% { margin-left: -35%; }
  100% { margin-left: 100%; }
}

</style>

<style scoped lang="scss">
/* ═══ 管理端十项升级：新增/覆盖样式 ═══ */

/* ── F1 上传入口 ── */
.upload-entry { display:flex; align-items:center; justify-content:space-between; gap:16px; flex-wrap:wrap; }
.upload-entry-info { display:flex; align-items:center; gap:14px; }
.upload-entry .upload-ico { color: var(--c-gold-3); flex-shrink:0; }
.upload-entry .upload-main { font-size:14px; color:var(--c-ink); font-weight:600; margin:0; }
.upload-entry .upload-hint { font-size:12px; color:var(--c-ink-3); margin:3px 0 0; }
.primary-btn.lg { padding:9px 18px; font-size:14px; }
.uploader-dialog { display:block; }

/* ── F7 分类彩色标签 ── */
.cat-dot { display:inline-block; width:8px; height:8px; border-radius:50%; margin-right:6px; vertical-align:middle; flex-shrink:0; }
.cat-btn { display:inline-flex; align-items:center; }
.cat-badge.tinted { display:inline-flex; align-items:center; border:1px solid; border-radius:var(--radius-xs); padding:2px 8px; font-weight:600; }
.cat-opt { display:inline-flex; align-items:center; }
.prio-pill { display:inline-flex; align-items:center; gap:3px; font-size:11px; font-weight:700;
  color:#fff; background:linear-gradient(135deg,#FF4D6D,#FF7A45); border:none; border-radius:var(--radius-xs);
  padding:3px 8px; box-shadow:0 1px 5px rgba(255,77,109,.38); }

/* ── F4 体检报告丰富 ── */
.st-kpis { display:flex; align-items:center; gap:22px; padding:6px 2px 16px; flex-wrap:wrap; }
.st-gauge-ring { width:96px; height:96px; border-radius:50%; display:flex; align-items:center; justify-content:center; }
.st-gauge-inner { width:74px; height:74px; border-radius:50%; background:var(--c-paper); display:flex; flex-direction:column; align-items:center; justify-content:center; }
.st-gauge-val { font-size:22px; font-weight:800; line-height:1; }
.st-gauge-lbl { font-size:11px; color:var(--c-ink-3); margin-top:3px; }
.st-kpi-cells { display:flex; gap:10px; flex-wrap:wrap; }
.st-kpi-cell { min-width:76px; background:var(--c-paper-2); border:1px solid var(--c-border); border-radius:var(--radius-sm); padding:10px 12px; display:flex; flex-direction:column; gap:3px; }
.st-kpi-cell b { font-size:19px; color:var(--c-ink); font-weight:700; }
.st-kpi-cell span { font-size:11px; color:var(--c-ink-3); }
.st-bytype { display:flex; flex-direction:column; gap:8px; margin-bottom:14px; }
.st-bytype-row { display:flex; align-items:center; gap:10px; font-size:12px; }
.st-bytype-name { width:64px; color:var(--c-ink-2); flex-shrink:0; }
.st-bytype-bar { flex:1; height:8px; background:var(--c-border); border-radius:99px; overflow:hidden; }
.st-bytype-fill { height:100%; border-radius:99px; transition:width .5s; }
.st-bytype-val { width:96px; text-align:right; color:var(--c-ink-3); flex-shrink:0; }
.st-meta { display:flex; flex-wrap:wrap; gap:6px; margin:6px 0; }
.st-chip { display:inline-flex; align-items:center; gap:3px; font-size:11px; color:var(--c-ink-3);
  background:var(--c-paper-2); border:1px solid var(--c-border); border-radius:var(--radius-xs); padding:2px 7px; }

/* ── F5 应急广播页 ── */
/* 状态条 */
.bc-status-strip { display:grid; grid-template-columns: 1fr 1fr 1.6fr 1fr; gap:12px; margin-bottom:16px; }
@media (max-width: 1100px) { .bc-status-strip { grid-template-columns:1fr 1fr; } }
.bc-stat { display:flex; align-items:center; gap:11px; padding:12px 14px; background:var(--c-paper);
  border:1px solid var(--c-border); border-radius:var(--radius-sm); box-shadow:var(--shadow-sm); min-width:0; }
.bc-stat-ico { width:36px; height:36px; border-radius:9px; display:flex; align-items:center; justify-content:center;
  color:var(--c-ink-3); background:var(--c-paper-2); flex-shrink:0; }
.bc-stat-ico.on { color:var(--c-green); background:var(--c-green-bg, rgba(52,168,83,.12)); }
.bc-stat-ico.off { color:var(--c-ink-3); }
.bc-stat-ico.live { color:#fff; background:linear-gradient(135deg,#FF4D6D,#FF7A45); animation:bc-livepulse 1.4s infinite; }
@keyframes bc-livepulse { 0%,100%{box-shadow:0 0 0 0 rgba(255,77,109,.4);} 50%{box-shadow:0 0 0 6px rgba(255,77,109,0);} }
.bc-stat-body { display:flex; flex-direction:column; gap:2px; min-width:0; }
.bc-stat-label { font-size:11.5px; color:var(--c-ink-3); }
.bc-stat-val { display:inline-flex; align-items:center; gap:5px; font-size:13px; font-weight:700; color:var(--c-ink); }
.bc-stat-val b { font-size:16px; color:var(--c-gold-3); }
.bc-stat-val.on { color:var(--c-green); } .bc-stat-val.off { color:var(--c-ink-3); }
.bc-stat-dot { width:6px; height:6px; border-radius:50%; background:currentColor; flex-shrink:0; }
.bc-stat-now { font-size:12.5px; color:var(--c-ink-3); white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.bc-stat-now.speaking { color:var(--c-ink); font-weight:600; }

.bc-layout { display:grid; grid-template-columns: minmax(0,1.4fr) minmax(0,1fr); gap:16px; align-items:start; }
@media (max-width: 1100px) { .bc-layout { grid-template-columns:1fr; } }
.bc-field-label { font-size:12px; font-weight:600; color:var(--c-ink-2); margin:14px 0 8px; }
.bc-field-label:first-of-type { margin-top:2px; }

/* 广播级别 */
.bc-levels { display:flex; gap:10px; }
.bc-level { flex:1; display:inline-flex; align-items:center; justify-content:center; gap:6px; padding:10px 8px; cursor:pointer;
  font-size:13px; font-weight:600; color:var(--c-ink-2); background:var(--c-paper-2);
  border:1.5px solid var(--c-border); border-radius:var(--radius-sm); transition:all .15s; }
.bc-level:hover { border-color:var(--c-ink-3); }
.bc-level.urgent.active    { color:#fff; background:linear-gradient(135deg,#FF3B5C,#FF6B3D); border-color:transparent; box-shadow:0 3px 10px rgba(255,59,92,.3); }
.bc-level.important.active { color:#fff; background:linear-gradient(135deg,#FF9F0A,#FF7A45); border-color:transparent; box-shadow:0 3px 10px rgba(255,122,69,.28); }
.bc-level.normal.active    { color:#fff; background:linear-gradient(135deg,#4F5BE0,#5B9CF8); border-color:transparent; box-shadow:0 3px 10px rgba(79,91,224,.28); }

/* 模板分组 */
.bc-tpl-groups { display:flex; flex-direction:column; gap:12px; }
.bc-tpl-group { display:flex; flex-direction:column; gap:7px; }
.bc-tpl-gl { display:inline-flex; align-items:center; gap:6px; font-size:11.5px; color:var(--c-ink-3); }
.bc-templates { display:flex; flex-wrap:wrap; gap:8px; }
.bc-tpl-btn { display:inline-flex; align-items:center; gap:5px; font-size:12.5px; color:var(--c-ink-2);
  background:var(--c-paper-2); border:1px solid var(--c-border); border-radius:99px; padding:6px 12px; cursor:pointer; transition:all .15s; }
.bc-tpl-btn:hover { border-color:var(--c-gold-3); color:var(--c-gold-3); background:var(--c-gold-bg); }
.bc-est { display:inline-flex; align-items:center; gap:5px; font-size:12px; color:var(--c-ink-3); margin-top:8px; }
.bc-est b { color:var(--c-gold-3); }
.bc-row { display:flex; align-items:center; gap:12px; margin-top:14px; flex-wrap:wrap; }
.bc-row-label { font-size:13px; color:var(--c-ink-2); width:64px; flex-shrink:0; }
.bc-dur { display:inline-flex; align-items:center; gap:6px; font-size:12px; color:var(--c-ink-3); }
.bc-repeat-live { display:inline-flex; align-items:center; gap:4px; font-size:12px; font-weight:600; color:var(--c-gold-3); }
.ghost-btn.danger:hover { color:var(--c-red); border-color:var(--c-red); }

.bc-side { display:flex; flex-direction:column; gap:16px; }
.bc-prev-switch { margin-left:auto; display:inline-flex; background:var(--c-paper-2); border:1px solid var(--c-border);
  border-radius:99px; padding:2px; }
.bc-prev-switch button { border:none; background:transparent; color:var(--c-ink-3); font-size:11.5px; font-weight:600;
  padding:3px 12px; border-radius:99px; cursor:pointer; transition:all .15s; }
.bc-prev-switch button.active { color:#fff; background:var(--c-gold-3); }
/* 现场预览：直播 FLV（竖屏 9:16 / 手机端 16:9） */
.bc-preview-stage { position:relative; border-radius:var(--radius-sm); overflow:hidden;
  background:linear-gradient(135deg,#20232f,#2b2438); display:flex; align-items:center; justify-content:center; }
.bc-preview-stage.portrait { aspect-ratio:9/16; max-height:420px; margin:0 auto; width:auto; }
.bc-preview-stage.main { aspect-ratio:16/9; }
.bc-preview-video { width:100%; height:100%; object-fit:cover; display:block; background:#000; }
.bc-preview-ph { position:absolute; inset:0; display:flex; flex-direction:column; align-items:center; justify-content:center;
  gap:8px; color:rgba(255,255,255,.6); font-size:12px; }
.bc-live-badge { position:absolute; top:10px; left:10px; display:inline-flex; align-items:center; gap:5px;
  font-size:11px; font-weight:800; letter-spacing:.5px; color:#fff; background:rgba(220,40,40,.9);
  padding:3px 9px; border-radius:99px; }
.bc-live-badge i { width:6px; height:6px; border-radius:50%; background:#fff; animation:bc-livepulse 1.4s infinite; }
.bc-speaking-badge { position:absolute; top:10px; right:10px; display:inline-flex; align-items:center; gap:4px;
  font-size:11px; font-weight:700; color:#fff; background:linear-gradient(135deg,#FF4D6D,#FF7A45);
  padding:3px 9px; border-radius:99px; box-shadow:0 2px 8px rgba(255,77,109,.4); }
.bc-preview-sub { position:absolute; left:6%; right:6%; bottom:8%; text-align:center; padding:10px 14px; border-radius:10px;
  font-size:14px; font-weight:700; color:#fff; line-height:1.5; backdrop-filter:blur(4px); box-shadow:0 6px 20px rgba(0,0,0,.35); }
.bc-preview-sub.alert { background:rgba(210,44,44,.9); }
.bc-preview-sub.info { background:rgba(40,90,200,.9); }
.bc-history { display:flex; flex-direction:column; gap:10px; max-height:300px; overflow-y:auto; }
.bc-hist-item { display:flex; gap:9px; align-items:flex-start; }
.bc-hist-dot { width:8px; height:8px; border-radius:50%; margin-top:6px; flex-shrink:0; }
.bc-hist-dot.ok { background:var(--c-green); } .bc-hist-dot.fail { background:var(--c-red); }
.bc-hist-body { flex:1; min-width:0; }
.bc-hist-text { font-size:13px; color:var(--c-ink); margin:0; line-height:1.5; }
.bc-hist-meta { display:flex; align-items:center; gap:6px; font-size:11px; color:var(--c-ink-3); margin:3px 0 0; }
.bc-hist-lv { display:inline-flex; align-items:center; font-size:10.5px; font-weight:700; padding:1px 7px; border-radius:99px; color:#fff; }
.bc-hist-lv.urgent { background:#FF3B5C; } .bc-hist-lv.important { background:#FF7A45; } .bc-hist-lv.normal { background:#4F5BE0; }
.bc-hist-resend { flex-shrink:0; width:26px; height:26px; border-radius:7px; display:flex; align-items:center; justify-content:center;
  background:transparent; border:1px solid var(--c-border); color:var(--c-ink-3); cursor:pointer; transition:all .15s; }
.bc-hist-resend:hover { color:var(--c-gold-3); border-color:var(--c-gold-3); background:var(--c-gold-bg); }
.empty-state.sm { padding:18px; font-size:12px; }

/* ── F6 运营代理动作卡 + 状态 ── */
.ai-msg-col { display:flex; flex-direction:column; gap:8px; min-width:0; flex:1; }
.ai-tool-status { display:inline-flex; align-items:center; gap:6px; font-size:12.5px; color:var(--c-gold-3); }
.ai-actions { display:flex; flex-direction:column; gap:8px; }
.ai-action-card { border:1px solid var(--c-gold-bdr); background:var(--c-gold-bg); border-radius:10px; padding:10px 12px; }
.ai-action-hd { display:flex; align-items:center; gap:6px; font-size:12.5px; font-weight:700; color:#B8860B; margin-bottom:6px; }
.ai-action-body { font-size:13px; color:var(--c-ink); line-height:1.55; margin:0 0 8px; }
.ai-action-btn { display:inline-flex; align-items:center; gap:4px; font-size:12px; font-weight:600; cursor:pointer;
  color:#fff; background:var(--c-gold-3); border:none; border-radius:99px; padding:5px 14px; transition:opacity .15s; }
.ai-action-btn:hover { opacity:.9; } .ai-action-btn:disabled { opacity:.5; cursor:default; }
.ai-action-btn.sm { padding:3px 10px; font-size:11px; }
.ai-faq-sug { border-top:1px dashed var(--c-gold-bdr); padding-top:8px; margin-top:8px; }
.ai-faq-sug:first-of-type { border-top:none; padding-top:0; margin-top:0; }
.ai-faq-q { font-size:12.5px; font-weight:600; color:var(--c-ink); }
.ai-faq-a { font-size:12px; color:var(--c-ink-2); line-height:1.5; margin:3px 0 6px; }

/* ── F8 左下角状态 ── */
.sidebar-footer { padding:10px; display:flex; flex-direction:column; gap:8px; border-top:1px solid var(--c-border); }
.sf-scenic { display:flex; align-items:center; gap:10px; padding:8px 10px; background:var(--c-paper-2); border:1px solid var(--c-border); border-radius:var(--radius-sm); }
.sf-scenic-ico { width:30px; height:30px; border-radius:8px; display:flex; align-items:center; justify-content:center;
  color:#fff; background:linear-gradient(135deg,var(--c-gold-3),var(--c-gold-2)); flex-shrink:0; }
.sf-scenic-body { display:flex; flex-direction:column; min-width:0; }
.sf-scenic-name { font-size:13px; font-weight:700; color:var(--c-ink); white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.sf-scenic-status { display:inline-flex; align-items:center; gap:5px; font-size:11px; color:var(--c-green); }
.sf-live-dot { width:6px; height:6px; border-radius:50%; background:var(--c-green); box-shadow:0 0 0 0 rgba(52,168,83,.5); animation:sf-pulse 2s infinite; }
@keyframes sf-pulse { 0%{box-shadow:0 0 0 0 rgba(52,168,83,.5);} 70%{box-shadow:0 0 0 5px rgba(52,168,83,0);} 100%{box-shadow:0 0 0 0 rgba(52,168,83,0);} }
.sf-account { display:flex; align-items:center; gap:9px; padding:6px 10px; }
.sf-avatar { width:30px; height:30px; border-radius:50%; display:flex; align-items:center; justify-content:center;
  font-size:13px; font-weight:700; color:#fff; background:linear-gradient(135deg,#6d78e8,#4F5BE0); flex-shrink:0; }
.sf-account-body { display:flex; flex-direction:column; min-width:0; flex:1; }
.sf-account-name { font-size:13px; font-weight:600; color:var(--c-ink); white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.sf-account-role { font-size:11px; color:var(--c-ink-3); }
.sf-icon-btn { width:28px; height:28px; border-radius:7px; display:flex; align-items:center; justify-content:center;
  background:transparent; border:1px solid var(--c-border); color:var(--c-ink-3); cursor:pointer; transition:all .15s; }
.sf-icon-btn:hover { color:var(--c-red); border-color:var(--c-red); background:var(--c-red-bg); }
.sf-theme-btn { display:flex; align-items:center; justify-content:center; gap:7px; width:100%; padding:8px;
  background:var(--c-paper-2); border:1px solid var(--c-border); border-radius:var(--radius-sm); color:var(--c-ink-2);
  font-size:12.5px; cursor:pointer; transition:all .15s; }
.sf-theme-btn:hover { border-color:var(--c-gold-3); color:var(--c-gold-3); }

/* ── F9 输入框流行样式 ── */
.ai-input { border-radius:14px !important; transition:border-color .18s, box-shadow .18s; }
.ai-input:focus { border-color:var(--c-gold-3) !important; box-shadow:0 0 0 3px var(--c-gold-bg) !important; }
.edit-input, .search-input { border-radius:10px !important; transition:border-color .18s, box-shadow .18s; }
.edit-input:focus, .search-input:focus { border-color:var(--c-gold-3) !important; box-shadow:0 0 0 3px var(--c-gold-bg) !important; outline:none; }
</style>
