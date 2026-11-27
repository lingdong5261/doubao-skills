const { request } = require('../lib/request');
const { yuan } = require('../lib/format');

/** 一款商品的完整信息：材质、尺寸、卖点、送装规则、全部 SKU 库存 */
async function goodsDetail(params) {
  const id = String((params && params.id) || '');
  if (!id) {
    return {
      isError: true,
      content: [{ type: 'text', text: '要查哪一款？给我商品名或型号就行，比如「白蜡木双人床」。' }]
    };
  }

  let g;
  try {
    g = await request({ url: '/api/goods/' + encodeURIComponent(id) });
  } catch (e) {
    return { isError: true, content: [{ type: 'text', text: '商品信息拉取失败，稍后再问一次。' }] };
  }

  const inStock = g.skus.filter(function (s) { return s.madeToOrder || s.stock > 0; });
  const stockText = inStock.length
    ? inStock.map(function (s) {
        return s.name + '：' + (s.madeToOrder ? '按单生产 ' + s.leadTimeDays + ' 天' : '现货 ' + s.stock + ' 件');
      }).join('；')
    : '全部规格暂时缺货';

  return {
    isError: false,
    content: [{
      type: 'text',
      text: '「' + g.title + '」' + yuan(g.price) + '起。' + g.material + '，尺寸 ' + g.sizeText
        + '。库存：' + stockText + '。' + g.delivery
    }],
    structuredContent: {
      id: g.id,
      title: g.title,
      price: g.price,
      priceText: yuan(g.price),
      listPrice: g.listPrice,
      material: g.material,
      sizeText: g.sizeText,
      sellingPoints: g.sellingPoints,
      delivery: g.delivery,
      tags: g.tags,
      pagePath: g.pagePath,
      skus: g.skus.map(function (s) {
        return {
          skuId: s.skuId,
          name: s.name,
          price: s.price,
          priceText: yuan(s.price),
          stock: s.stock,
          madeToOrder: s.madeToOrder,
          leadTimeDays: s.leadTimeDays
        };
      })
    },
    handoff: function () {
      return { query: 'id=' + g.id, payload: { skuId: inStock[0] ? inStock[0].skuId : null } };
    }
  };
}

module.exports = goodsDetail;
