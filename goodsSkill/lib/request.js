/**
 * 双端请求适配
 * - 小程序里用 wx.request
 * - 本地 Node 调试时用 fetch
 * 这样 apis/*.js 的代码在同一份里跑通，不用维护两套。
 */

const REMOTE_BASE = 'https://shop.example.com'; // ← 上线前改成你自己的 HTTPS 域名（要备案）
const LOCAL_BASE = 'http://127.0.0.1:8787';

function isWeChat() {
  return typeof wx !== 'undefined' && typeof wx.request === 'function';
}

function baseUrl() {
  if (isWeChat()) {
    // 开发者工具勾选「不校验合法域名」后可连本地；体验版/正式版必须 https
    try {
      const env = wx.getAccountInfoSync().miniProgram.envVersion;
      if (env === 'develop') return LOCAL_BASE;
    } catch (e) {}
    return REMOTE_BASE;
  }
  return (typeof process !== 'undefined' && process.env && process.env.API_BASE) || LOCAL_BASE;
}

function request(options) {
  const url = /^https?:/.test(options.url) ? options.url : baseUrl() + options.url;
  const method = options.method || 'GET';
  const data = options.data || {};

  if (isWeChat()) {
    return new Promise((resolve, reject) => {
      wx.request({
        url,
        method,
        data,
        header: { 'content-type': 'application/json' },
        timeout: 8000,
        success(res) {
          if (res.statusCode >= 200 && res.statusCode < 300) resolve(res.data);
          else reject(new Error('接口返回 ' + res.statusCode + '：' + JSON.stringify(res.data)));
        },
        fail(err) {
          reject(new Error('网络请求失败：' + (err.errMsg || '')));
        }
      });
    });
  }

  const init = { method, headers: { 'content-type': 'application/json' } };
  if (method !== 'GET') init.body = JSON.stringify(data);

  return fetch(url, init).then((r) => {
    if (!r.ok) return r.text().then((t) => Promise.reject(new Error('接口返回 ' + r.status + '：' + t)));
    return r.json();
  });
}

module.exports = { request, baseUrl };
