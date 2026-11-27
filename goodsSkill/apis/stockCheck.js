const { request } = require('../lib/request');

/** 查某个 SKU 的实时库存 / 是否按单生产 / 交期 */
async function stockCheck(params) {
  const skuId = String((params && params.skuId) || '');
  if (!skuId) {
    return {
      isError: true,
      content: [{ type: 'text', text: '要查哪个规格？先告诉我是哪款、什么颜色或尺寸。' }]
    };
  }

  let s;
  try {
    s = await request({ url: '/api/stock?skuId=' + encodeURIComponent(skuId) });
  } catch (e) {
    return { isError: true, content: [{ type: 'text', text: '库存查询失败，请稍后再试。' }] };
  }

  return {
    isError: false,
    content: [{ type: 'text', text: s.text }],
    structuredContent: {
      skuId: s.skuId,
      name: s.name,
      stock: s.stock,
      inStock: s.inStock,
      madeToOrder: s.madeToOrder,
      leadTimeDays: s.leadTimeDays
    }
  };
}

module.exports = stockCheck;
