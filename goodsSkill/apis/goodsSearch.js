const { request } = require('../lib/request');
const { yuan } = require('../lib/format');

/**
 * 按尺寸 / 材质 / 预算 / 品类找货
 * 只返回真货：价格和库存都取自接口，模型不能自己算。
 */
async function goodsSearch(params) {
  const p = params || {};
  const keyword = String(p.keyword || '');
  const category = String(p.category || '');
  const maxPrice = Number(p.maxPrice) || 0;
  const size = String(p.size || '');
  const limit = Math.min(5, Number(p.limit) || 3);

  const qs = [
    'keyword=' + encodeURIComponent(keyword),
    category ? 'category=' + encodeURIComponent(category) : '',
    maxPrice ? 'maxPrice=' + maxPrice : '',
    size ? 'size=' + encodeURIComponent(size) : '',
    'limit=' + limit
  ].filter(Boolean).join('&');

  let data;
  try {
    data = await request({ url: '/api/goods/search?' + qs });
  } catch (e) {
    return {
      isError: true,
      content: [{ type: 'text', text: '查商品超时了，让顾客稍等一下再问，或者直接进小程序自己翻。' }]
    };
  }

  const items = data.items || [];
  if (!items.length) {
    return {
      isError: false,
      content: [{
        type: 'text',
        text: '按这个条件没找到合适的款。可以放宽预算、换个尺寸，或者到店看实物——店里还有没上架的样品。'
      }],
      structuredContent: { total: 0, items: [] }
    };
  }

  const top = items[0];
  const stockLine = top.stockTotal > 0
    ? '现货 ' + top.stockTotal + ' 件'
    : (top.hasMadeToOrder ? '按单生产，约 15 天' : '暂时缺货');

  return {
    isError: false,
    content: [{
      type: 'text',
      text: '找到 ' + items.length + ' 款。最接近的是「' + top.title + '」，'
        + yuan(top.price) + '起，' + top.sizeText + '，' + stockLine + '。'
    }],
    // structuredContent 里 pagePath 会被平台抽成回复正文里的蓝链
    structuredContent: {
      total: items.length,
      items: items.map(function (it) {
        return {
          id: it.id,
          title: it.title,
          price: it.price,
          priceText: yuan(it.price),
          sizeText: it.sizeText,
          stockTotal: it.stockTotal,
          tags: it.tags,
          pagePath: it.pagePath,
          skus: it.skus
        };
      })
    },
    // 页面接力：用户点卡片直接落到这款的详情页，并高亮有货的规格
    handoff: function () {
      const pick = top.skus.find(function (s) { return s.madeToOrder || s.stock > 0; }) || top.skus[0];
      return {
        query: 'id=' + top.id,
        payload: {
          highlightSku: pick ? pick.skuId : null,
          price: pick ? pick.price : top.price,
          stock: pick ? pick.stock : 0
        }
      };
    }
  };
}

module.exports = goodsSearch;
