const app = getApp();
const cfg = require('../../config.js');
const api = require('../../utils/api.js');

const SCENICS = [
  { id: 'lingshan', name: '灵山胜境' },
  { id: 'nihuawan', name: '拈花湾' },
  { id: 'xihu', name: '西湖' },
  { id: 'huangshan', name: '黄山' },
  { id: 'gugong', name: '故宫' },
];
const GROUPS = [
  { id: 'adult', name: '独自/成人' },
  { id: 'family_kids', name: '亲子同行' },
  { id: 'senior', name: '陪伴长辈' },
  { id: 'couple', name: '情侣出游' },
];
const SUGGESTIONS = [
  { t: '这里有什么必看的', q: '这个景区有哪些必看的景点和看点？' },
  { t: '帮我推荐路线', q: '请根据我的同行情况，帮我推荐一条游览路线。' },
  { t: '讲个历史故事', q: '给我讲一个这里的历史文化故事吧。' },
  { t: '现在人多吗', q: '现在景区人多吗？怎么错开人流高峰？' },
  { t: '附近吃什么', q: '附近有什么特色美食或值得一试的小吃？' },
];
const INTENT = { qa: '问答', navigation: '指路', recommend: '推荐', empathy: '关怀', chitchat: '闲聊' };
const EMO = {
  happy: '😊 开心', excited: '🤩 兴奋', neutral: '🙂 平静', calm: '🙂 平静',
  curious: '🤔 好奇', empathetic: '🥰 关切', apologetic: '🙏 抱歉', concerned: '🥺 关切',
};

Page({
  data: {
    // 系统/布局
    statusBarHeight: 20, navBarHeight: 44, safeBottom: 0,
    // 流程
    started: false, connecting: false, connectingText: '正在唤醒慧昭…',
    connected: false, statusText: '未连接',
    hls: '', videoStalled: false, videoStalledText: '画面连接中…',
    videoMuted: true,  // iOS 只允许静音 autoplay：先静音起播，bindplaying 后再取消静音恢复慧昭声音
    vdebug: '',        // 屏幕可见的 video 事件调试日志（定位 HLS 卡点用）
    // 选择器
    scenicNames: SCENICS.map(s => s.name), scenicIndex: 0,
    groupNames: GROUPS.map(g => g.name), groupIndex: 0,
    // 输入/回答
    draft: '', busy: false, thinking: false,
    reply: '', placeholder: '连接后，慧昭会主动与您打招呼。可语音、打字提问，或拍照让我帮您定位讲解。',
    location: '', intentLabel: '', emoLabel: '', timing: '',
    micState: 'idle',
    suggestions: SUGGESTIONS,
    // 行程游记
    tripOpen: false, tripLoading: false, tripText: '',
  },

  onLoad() {
    const g = app.globalData;
    this.setData({
      statusBarHeight: g.statusBarHeight,
      navBarHeight: g.navBarHeight,
      safeBottom: g.safeBottom,
      hls: cfg.HLS,
    });
    this._rec = wx.getRecorderManager();
    this._rec.onStop((res) => this._onRecStop(res));
    this._rec.onError(() => { this.setData({ micState: 'idle' }); this._toast('录音失败'); });
    this._typer = null;
    this._recStartAt = 0;
    this._recCancel = false;
  },

  onUnload() { if (this._typer) clearInterval(this._typer); },

  // ───────── 工具 ─────────
  scenicId() { return SCENICS[this.data.scenicIndex].id; },
  groupId() { return GROUPS[this.data.groupIndex].id; },
  _vibrate() { try { wx.vibrateShort({ type: 'light' }); } catch (e) {} },
  _toast(title, icon = 'none') { wx.showToast({ title, icon, duration: 1800 }); },

  // 打字机揭示回答
  _typeReply(text) {
    if (this._typer) clearInterval(this._typer);
    this.setData({ reply: '', thinking: false });
    let i = 0;
    this._typer = setInterval(() => {
      i += 2;
      this.setData({ reply: text.slice(0, i) });
      if (i >= text.length) { clearInterval(this._typer); this._typer = null; this.setData({ reply: text }); }
    }, 24);
  },

  // ───────── 连接 / 迎宾 ─────────
  start() {
    this.setData({ connecting: true, connectingText: '正在唤醒慧昭…' });
    // 启动 HLS 画面（设 started 触发 <video> 渲染）
    this._vt0 = Date.now();  // video 事件计时起点
    this.setData({ started: true, hls: cfg.HLS + '?t=' + Date.now(), vdebug: '0.0s 开始加载 ' + cfg.HLS });
    // iOS 常拦截 autoplay：在「开始体验」这个用户手势上下文里主动 play()，
    // 否则 video 会停在 waiting（画面缓冲中）不动。延迟到 <video> 渲染后再取 context。
    this._vctx = wx.createVideoContext('dh', this);
    setTimeout(() => { try { this._vctx && this._vctx.play(); } catch (e) {} }, 300);
    // 探活后进入；即便桥接探活失败也允许进入（画面与问答各自降级）
    api.liveHealth().catch(() => ({})).then(() => {
      setTimeout(() => {
        this.setData({
          connecting: false, connected: true,
          statusText: '已连接 · ' + this.data.scenicNames[this.data.scenicIndex],
        });
        this._greet();
      }, 900);
    });
  },

  _greet() {
    this.setData({ thinking: true, intentLabel: '', emoLabel: '', location: '', timing: '' });
    api.greeting(this.scenicId(), this.groupId())
      .then((g) => {
        const text = (g && (g.text || g.summary)) || '欢迎来到这里，我是您的导览员慧昭，很高兴为您服务～';
        this.setData({ emoLabel: '🪷 主动迎宾' });
        this._typeReply(text);
        api.liveSay({ sessionid: cfg.SESSION_ID, text, scenic_id: this.scenicId(), emotion: (g && g.emotion) || 'happy' }).catch(() => {});
      })
      .catch(() => {
        this.setData({ thinking: false });
        this._typeReply('欢迎来到这里，我是您的导览员慧昭，随时为您讲解、推荐路线，或帮您拍照定位～');
      });
  },

  // ───────── 文字提问 ─────────
  onInput(e) { this.setData({ draft: e.detail.value }); },

  quickAsk(e) {
    const i = e.currentTarget.dataset.i;
    this._ask(this.data.suggestions[i].q);
  },

  askText() {
    const msg = (this.data.draft || '').trim();
    if (!msg) return;
    this._ask(msg);
  },

  _ask(message) {
    if (this.data.busy) return;
    if (!this.data.connected) { this._toast('请先开始游览'); return; }
    this._vibrate();
    this.setData({
      busy: true, thinking: true, draft: '',
      intentLabel: '', emoLabel: '', location: '', timing: '',
    });
    const t0 = Date.now();
    api.liveAsk({
      sessionid: cfg.SESSION_ID,
      session_id: app.globalData.sessionId,
      message,
      scenic_id: this.scenicId(),
      group_type: this.groupId(),
    })
      .then((d) => {
        const dt = ((Date.now() - t0) / 1000).toFixed(1);
        this.setData({
          intentLabel: INTENT[d.intent] || '问答',
          emoLabel: EMO[d.emotion] || '🙂 平静',
          timing: dt,
        });
        this._typeReply(d.reply || '（暂时没有找到答案，换个说法再问问我？）');
      })
      .catch((err) => {
        this.setData({ thinking: false });
        this._typeReply('网络好像有点不稳，请稍后再问我一次～');
        this._toast(err.message || '请求失败');
      })
      .finally(() => this.setData({ busy: false }));
  },

  // ───────── 语音（按住说话）─────────
  micStart() {
    if (!this.data.connected) { this._toast('请先开始游览'); return; }
    if (this.data.busy) return;
    this._recCancel = false;
    this._recStartAt = Date.now();
    this._vibrate();
    this.setData({ micState: 'recording' });
    this._rec.start({
      duration: 60000, sampleRate: 16000, numberOfChannels: 1,
      encodeBitRate: 48000, format: 'mp3',
    });
  },

  micEnd(e) {
    if (this.data.micState !== 'recording') return;
    // 上滑取消：触点明显高于起始（touchend 的 y 比 dock 高很多）
    if (e && e.changedTouches && e.changedTouches[0]) {
      const y = e.changedTouches[0].clientY;
      if (y && y < 360) this._recCancel = true; // 屏幕上半部分松手 = 取消
    }
    if (Date.now() - this._recStartAt < 350) { this._recCancel = true; this._toast('说话时间太短'); }
    this._vibrate();
    this.setData({ micState: this._recCancel ? 'idle' : 'recognizing' });
    this._rec.stop();
  },

  _onRecStop(res) {
    if (this._recCancel || !res || !res.tempFilePath) { this.setData({ micState: 'idle' }); return; }
    this.setData({ micState: 'recognizing' });
    api.asr(res.tempFilePath, this.scenicId())
      .then((d) => {
        this.setData({ micState: 'idle' });
        const text = d && d.text && d.text.trim();
        if (text) { this.setData({ draft: text }); this._ask(text); }
        else this._toast('没听清，请再说一次');
      })
      .catch(() => { this.setData({ micState: 'idle' }); this._toast('识别失败，请重试'); });
  },

  // ───────── 拍照视觉定位 ─────────
  takePhoto() {
    if (!this.data.connected) { this._toast('请先开始游览'); return; }
    if (this.data.busy) return;
    this._vibrate();
    wx.chooseMedia({
      count: 1, mediaType: ['image'], sourceType: ['camera', 'album'], sizeType: ['compressed'], camera: 'back',
      success: (r) => {
        const file = r.tempFiles && r.tempFiles[0];
        if (file && file.tempFilePath) this._locate(file.tempFilePath);
      },
      fail: () => {},
    });
  },

  _locate(filePath) {
    this.setData({
      busy: true, thinking: true,
      intentLabel: '', emoLabel: '', location: '', timing: '',
    });
    const t0 = Date.now();
    const fmt = filePath.toLowerCase().endsWith('.png') ? 'png' : 'jpeg';
    let b64;
    try {
      b64 = wx.getFileSystemManager().readFileSync(filePath, 'base64');
    } catch (e) {
      this.setData({ busy: false, thinking: false }); this._toast('读取照片失败'); return;
    }
    api.chatImage({
      session_id: app.globalData.sessionId,
      scenic_id: this.scenicId(),
      image_b64: b64,
      image_format: fmt,
      question: '我面前是什么？帮我定位、讲解，并指引我接下来去哪。',
    })
      .then((d) => {
        const dt = ((Date.now() - t0) / 1000).toFixed(1);
        this.setData({
          location: d.location || '',
          intentLabel: d.location ? '视觉定位' : '识别',
          emoLabel: EMO[d.emotion] || '🙂 平静',
          timing: dt,
        });
        this._typeReply(d.reply || '（这张我没太看清，换个角度再拍一张？）');
        if (d.reply) api.liveSay({ sessionid: cfg.SESSION_ID, text: d.reply, scenic_id: this.scenicId(), emotion: d.emotion || 'neutral' }).catch(() => {});
      })
      .catch((err) => {
        this.setData({ thinking: false });
        this._typeReply('照片识别失败了，请再试一次～');
        this._toast(err.message || '识别失败');
      })
      .finally(() => this.setData({ busy: false }));
  },

  // ───────── 行程游记 ─────────
  openTrip() {
    this.setData({ tripOpen: true, tripLoading: true, tripText: '' });
    api.tripSummary(app.globalData.sessionId, this.scenicId())
      .then((d) => {
        this.setData({
          tripLoading: false,
          tripText: (d && (d.summary || d.text)) ||
            '这趟旅程才刚开始，多和慧昭聊聊、多拍几张照片，游记会更精彩哦～',
        });
      })
      .catch(() => this.setData({ tripLoading: false, tripText: '游记生成失败，请稍后再试。' }));
  },
  closeTrip() { this.setData({ tripOpen: false }); },
  noop() {},

  // ───────── 选择器 ─────────
  onScenicChange(e) {
    const idx = +e.detail.value;
    this.setData({ scenicIndex: idx });
    if (this.data.connected) {
      this.setData({ statusText: '已连接 · ' + this.data.scenicNames[idx] });
      this._greet();
    }
  },
  onGroupChange(e) { this.setData({ groupIndex: +e.detail.value }); },

  // ───────── 视频状态（带屏幕调试 HUD，定位 HLS 卡点）─────────
  // 把 video 生命周期事件追加到屏幕可见的 debug 行 + Console，截图即可诊断
  _vlog(tag, extra) {
    const t = ((Date.now() - (this._vt0 || Date.now())) / 1000).toFixed(1);
    const line = `${t}s ${tag}${extra ? ' ' + extra : ''}`;
    console.log('[video]', line);
    const log = (this.data.vdebug ? this.data.vdebug + ' | ' : '') + line;
    // 只保留最近若干条，避免过长
    const parts = log.split(' | ').slice(-8);
    this.setData({ vdebug: parts.join(' | ') });
  },
  onVideoLoadedMeta(e) {
    const d = e && e.detail || {};
    this._vlog('元数据✓', `${d.width}x${d.height} ${d.duration}s`);
  },
  onVideoPlay() { this._vlog('play事件'); },
  onVideoProgress(e) {
    const b = e && e.detail && e.detail.buffered;
    this._vlog('progress', b != null ? `buffered=${b}%` : '');
  },
  onVideoTimeUpdate(e) {
    const d = e && e.detail || {};
    // 节流：每秒最多记一次，且只在前几次记（证明帧在前进）
    this._tuCount = (this._tuCount || 0) + 1;
    if (this._tuCount <= 5) this._vlog('timeupdate', `cur=${(d.currentTime||0).toFixed(1)}`);
  },
  onVideoPause() { this._vlog('pause'); },
  onVideoEnded() { this._vlog('ended'); },
  copyDebug() {
    wx.setClipboardData({ data: this.data.vdebug, success: () => this._toast('已复制调试日志') });
  },
  onVideoError(e) {
    const msg = (e && e.detail && e.detail.errMsg) || '未知错误';
    this._vlog('ERROR', msg);
    this.setData({ videoStalled: true, videoStalledText: '画面连接失败：' + msg });
    this._retryVideo();
  },
  onVideoWaiting() {
    this._vlog('waiting缓冲');
    this.setData({ videoStalled: true, videoStalledText: '画面缓冲中…' });
  },
  onVideoPlaying() {
    this._vlog('playing▶');
    // 画面真正开始播了 → 此时取消静音是被 iOS 允许的（已在播放中），恢复慧昭声音
    this.setData({ videoStalled: false });
    if (this.data.videoMuted) {
      setTimeout(() => this.setData({ videoMuted: false }), 200);
    }
  },
  _retryVideo() {
    if (this._retrying) return;
    this._retrying = true;
    setTimeout(() => {
      this.setData({ hls: cfg.HLS + '?t=' + Date.now() });
      try { this._vctx && this._vctx.play(); } catch (e) {}
      this._retrying = false;
    }, 2500);
  },
});
