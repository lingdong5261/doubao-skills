const { request } = require('../lib/request');
const { yuan } = require('../lib/format');

/**
 * 算送装费：按小区分区 + 楼层
 * 顾客常问「送到 6 楼多少钱」，这一步必须走接口，不能让模型估。
 */
async function deliveryQuote(params) {
  const p = params || {};
  const skuId = String(p.skuId || '');
  const goodsId = String(p.goodsId || '');
  const address = String(p.address || '');
  const floor = Number(p.floor) || 1;

  if (!skuId && !goodsId) {
    return {
      isError: true,
      content: [{ type: 'text', text: '要算哪一款的送装？先定下商品和规格，我再按你的地址算。' }]
    };
  }

  let q;
  try {
    q = await request({ url: '/api/delivery/quote', method: 'POST', data: { skuId, goodsId, address, floor } });
  } catch (e) {
    return { isError: true, content: [{ type: 'text', text: '送装费算不出来，稍后再试或直接问店里。' }] };
  }
  if (q.error) {
    return { isError: true, content: [{ type: 'text', text: q.error }] };
  }

  return {
    isError: false,
    content: [{
      type: 'text',
      text: '送到' + (q.zone || '你所在区域') + '、' + floor + ' 楼，送装费一共 '
        + yuan(q.total) + '，约 ' + q.arriveDays + ' 天到家。' + q.note
    }],
    structuredContent: {
      zone: q.zone,
      base: q.base,
      baseText: yuan(q.base),
      zoneFee: q.zoneFee,
      floorFee: q.floorFee,
      total: q.total,
      totalText: yuan(q.total),
      arriveDays: q.arriveDays,
      note: q.note
    }
  };
}

module.exports = deliveryQuote;
