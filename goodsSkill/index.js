/**
 * SKILL 注册入口
 * 必须在独立分包里，且 app.json 的 agent.skills[].path 与本文件所在目录一致。
 * 这里只做三件事：建 skill、挂中间件、把原子接口注册进去。
 */

const skill = wx.modelContext.createSkill('/skills/goodsSkill');

/* 统一埋点：每次原子接口调用都记一条，日报的「AI 咨询量/未成交咨询」就靠它 */
skill.use(async function (ctx, next) {
  const start = Date.now();
  try {
    await next();
  } catch (err) {
    wx.reportEvent && wx.reportEvent('ai_api_error', { name: ctx.name, msg: String(err && err.message) });
    throw err;
  } finally {
    wx.reportEvent && wx.reportEvent('ai_api_trace', {
      name: ctx.name,
      cost: Date.now() - start
    });
  }
});

const goodsSearch = require('./apis/goodsSearch');
const goodsDetail = require('./apis/goodsDetail');
const stockCheck = require('./apis/stockCheck');
const deliveryQuote = require('./apis/deliveryQuote');
const orderCreate = require('./apis/orderCreate');
const orderTrack = require('./apis/orderTrack');
const storeInfo = require('./apis/storeInfo');

skill.registerAPI('goodsSearch', goodsSearch);
skill.registerAPI('goodsDetail', goodsDetail);
skill.registerAPI('stockCheck', stockCheck);
skill.registerAPI('deliveryQuote', deliveryQuote);
skill.registerAPI('orderCreate', orderCreate);
skill.registerAPI('orderTrack', orderTrack);
skill.registerAPI('storeInfo', storeInfo);
