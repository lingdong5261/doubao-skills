function yuan(n) {
  const s = String(Math.round(Number(n) || 0));
  return '¥' + s.replace(/\B(?=(\d{3})+(?!\d))/g, ',');
}

/** 给模型看的短文本，太长会被截断也浪费上下文 */
function clip(text, max) {
  const m = max || 160;
  if (!text) return '';
  return text.length > m ? text.slice(0, m) + '…' : text;
}

module.exports = { yuan, clip };
