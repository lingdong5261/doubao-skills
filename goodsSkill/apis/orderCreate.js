const { request } = require('../lib/request');
const { yuan } = require('../lib/format');

/**
 * 下单。真实环境里这一步要先确认规格、地址、楼层，再调微信支付。
 * 这里只创建待支付订单，把支付参数留给小程序页面（requestPayment）。
 */
async function orderCreate(params) {
  const p = params || {};
  const skuId = String(p.skuId || '');
  const qty = Math.max(1, Number(p.qty) || 1);
  const address = String(p.address || '');
  const floor = Number(p.floor) || 1;
  const note = String(p.note || '');

  if (!skuId) {
    return {
      isError: true,
      content: [{ type: 'text', text: '下单前要先定规格——哪一款、什么颜色尺寸？' }]
    };
  }
  if (!address) {
    return {
      isError: true,
      content: [{ type: 'text', text: '收货地址还没给我，送到哪个小区、几楼？' }]
    };
  }

  // openid 不给就交给服务端兜底，别传空串把默认值覆盖掉
  const body = { skuId, qty, address, floor, note };
  if (p.openid) body.openid = String(p.openid);

  let r;
  try {
    r = await request({
      url: '/api/orders',
      method: 'POST',
      data: body
    });
  } catch (e) {
    return { isError: true, content: [{ type: 'text', text: '下单接口没通，稍后再试，或直接进小程序结算页。' }] };
  }

  if (r.error) {
    return { isError: true, content: [{ type: 'text', text: r.error }] };
  }

  const o = r.order;
  return {
    isError: false,
    content: [{
      type: 'text',
      text: '已下单：' + o.title + '（' + o.skuName + '）× ' + o.qty
        + '，商品 ' + yuan(o.goodsAmount) + ' + 送装 ' + yuan(o.deliveryFee)
        + ' = ' + yuan(o.total) + '。订单号 ' + o.no + '，现在去付款就锁定库存。'
    }],
    structuredContent: {
      orderNo: o.no,
      orderId: o.id,
      title: o.title,
      skuName: o.skuName,
      qty: o.qty,
      goodsAmount: o.goodsAmount,
      deliveryFee: o.deliveryFee,
      total: o.total,
      totalText: yuan(o.total),
      status: o.status,
      statusText: o.statusText,
      // 蓝色链接指向订单详情，付款在页面里完成
      pagePath: '/pages/order/detail?no=' + o.no
    },
    handoff: function () {
      return { query: 'no=' + o.no, payload: { orderNo: o.no, total: o.total, needPay: true } };
    }
  };
}

module.exports = orderCreate;
