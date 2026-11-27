const { request } = require('../lib/request');
const { yuan } = require('../lib/format');

/** 查订单：支持按订单号，或不给订单号时返回该用户最近 3 单 */
async function orderTrack(params) {
  const p = params || {};
  const orderNo = String(p.orderNo || '');
  const openid = String(p.openid || '');

  let data;
  try {
    data = await request({
      url: '/api/orders/' + encodeURIComponent(orderNo || 'latest') + (openid && !orderNo ? '?openid=' + encodeURIComponent(openid) : '')
    });
  } catch (e) {
    return { isError: true, content: [{ type: 'text', text: '订单查询失败，稍后再试。' }] };
  }

  const orders = data.orders || [];
  if (!orders.length) {
    return {
      isError: false,
      content: [{ type: 'text', text: '没查到订单。订单号发我一下，或者进「我的-订单」里看。' }],
      structuredContent: { orders: [] }
    };
  }

  const o = orders[0];
  return {
    isError: false,
    content: [{
      type: 'text',
      text: '订单 ' + o.no + '：' + o.title + '（' + o.skuName + '），' + yuan(o.total)
        + '，当前状态「' + o.statusText + '」。' + (o.status === 'pending_payment' ? '付款后 3–7 天安排送装。' : '')
    }],
    structuredContent: {
      orders: orders.map(function (x) {
        return {
          orderNo: x.no,
          title: x.title,
          skuName: x.skuName,
          total: x.total,
          totalText: yuan(x.total),
          status: x.status,
          statusText: x.statusText,
          createdAt: x.createdAt,
          pagePath: '/pages/order/detail?no=' + x.no
        };
      })
    },
    handoff: function () {
      return { query: 'no=' + o.no, payload: { orderNo: o.no } };
    }
  };
}

module.exports = orderTrack;
