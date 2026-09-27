/**
 * 网络封装：把 wx.request / wx.uploadFile 包成 Promise，统一超时与错误。
 * 小程序原生请求无 CORS（开发版需在 DevTools 勾「不校验合法域名」）。
 */
const cfg = require('../config.js');

/** POST JSON，返回解析后的 data；非 2xx 抛错。 */
function post(base, path, data, timeout = 60000) {
  return new Promise((resolve, reject) => {
    wx.request({
      url: base + path,
      method: 'POST',
      data: data || {},
      header: { 'content-type': 'application/json' },
      timeout,
      success(res) {
        if (res.statusCode >= 200 && res.statusCode < 300) resolve(res.data);
        else reject(new Error((res.data && (res.data.detail || res.data.message)) || ('HTTP ' + res.statusCode)));
      },
      fail(err) { reject(new Error(err.errMsg || '网络请求失败')); },
    });
  });
}

/** GET JSON。query 为对象。 */
function get(base, path, query, timeout = 30000) {
  let url = base + path;
  if (query) {
    const qs = Object.keys(query)
      .map(k => `${encodeURIComponent(k)}=${encodeURIComponent(query[k])}`)
      .join('&');
    if (qs) url += (url.includes('?') ? '&' : '?') + qs;
  }
  return new Promise((resolve, reject) => {
    wx.request({
      url, method: 'GET', timeout,
      success(res) {
        if (res.statusCode >= 200 && res.statusCode < 300) resolve(res.data);
        else reject(new Error('HTTP ' + res.statusCode));
      },
      fail(err) { reject(new Error(err.errMsg || '网络请求失败')); },
    });
  });
}

/** 上传文件（multipart），用于 /asr 语音转写。 */
function upload(base, path, filePath, name, formData, timeout = 30000) {
  return new Promise((resolve, reject) => {
    wx.uploadFile({
      url: base + path,
      filePath,
      name: name || 'file',
      formData: formData || {},
      timeout,
      success(res) {
        if (res.statusCode >= 200 && res.statusCode < 300) {
          try { resolve(JSON.parse(res.data)); }
          catch (e) { resolve(res.data); }
        } else reject(new Error('HTTP ' + res.statusCode));
      },
      fail(err) { reject(new Error(err.errMsg || '上传失败')); },
    });
  });
}

module.exports = {
  // —— 桥接层（数字人驱动）——
  liveAsk: (body) => post(cfg.BRIDGE, '/live/ask', body, 60000),
  liveSay: (body) => post(cfg.BRIDGE, '/live/say', body, 30000),
  liveHealth: () => get(cfg.BRIDGE, '/live/health', null, 5000),

  // —— RAG 后端（多模态 / 行程）——
  greeting: (scenic_id, group_type) => get(cfg.BACKEND, '/trip/greeting', { scenic_id, group_type }),
  tripSummary: (session_id, scenic_id) => get(cfg.BACKEND, '/trip/summary', { session_id, scenic_id }),
  chatImage: (body) => post(cfg.BACKEND, '/chat/image', body, 40000),
  // 语音识别：队友 Paraformer ASR（景区术语纠错内置），字段名 audio，language=auto
  asr: (filePath) => upload(cfg.TTS_BACKEND, '/api/speech/asr', filePath, 'audio', { language: 'auto' }),
};
