const { request } = require('../lib/request');

/** 门店信息：地址、营业时间、能不能到店试坐 */
async function storeInfo() {
  let s;
  try {
    s = await request({ url: '/api/store' });
  } catch (e) {
    return { isError: true, content: [{ type: 'text', text: '门店信息暂时取不到，稍后再问。' }] };
  }

  return {
    isError: false,
    content: [{
      type: 'text',
      text: s.name + '在' + s.address + '，营业时间 ' + s.hours + '。可以到店试坐，'
        + s.services.slice(0, 3).join('、') + '都有。'
    }],
    structuredContent: {
      name: s.name,
      address: s.address,
      hours: s.hours,
      phone: s.phone,
      services: s.services,
      pagePath: s.pagePath
    },
    handoff: function () {
      return { query: '', payload: {} };
    }
  };
}

module.exports = storeInfo;
