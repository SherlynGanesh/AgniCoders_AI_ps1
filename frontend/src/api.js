// Order desk API. LLM runs on the backend.
// POST /orders/parse   {message} -> {id, items:[Item], clarification}
// POST /orders/confirm {id, items} -> {bill:{lines:[{name,qty,unit,price,total}],subtotal,total}, deliveryNote}
// Item = {raw,name,qty,unit,price,status:'ok'|'ambiguous'|'oos'|'unknown',note?,options?:[{label,price}]}
import { DEMO, req } from './authService';

const oils = [{ label: 'Sunflower oil 1L', price: 150 }, { label: 'Sunflower oil 5L', price: 720 },
  { label: 'Groundnut oil 1L', price: 190 }, { label: 'Mustard oil 1L', price: 170 }];
const CAT = [
  { k: ['atta', 'aata'], name: 'Atta', pic: '🌾', unit: 'kg', price: 45, stock: 50 },
  { k: ['sugar', 'cheeni', 'chini'], name: 'Sugar', pic: '🍬', unit: 'kg', price: 48, stock: 20 },
  { k: ['butter', 'makhan'], name: 'Amul Butter 100g', pic: '🧈', unit: 'pc', price: 58, stock: 20 },
  { k: ['namak', 'salt'], name: 'Tata Salt 1kg', pic: '🧂', unit: 'pc', price: 28, stock: 0 },
  { k: ['tel', 'oil'], name: 'Cooking oil', pic: '🫒', unit: 'pc', options: oils, stock: 9 },
];
const NUM = { ek: 1, do: 2, teen: 3, char: 4, half: 0.5, aadha: 0.5, adha: 0.5 };

function mockParse(msg) {
  const items = msg.split(/,|\baur\b|\band\b/i).map(s => s.trim()).filter(Boolean).map(raw => {
    const w = raw.toLowerCase();
    const p = CAT.find(c => c.k.some(k => w.includes(k)));
    if (!p) return { raw, name: raw, qty: 1, unit: '', price: 0, conf: 40, status: 'unknown', note: 'Not in catalog' };
    const m = w.match(/(\d+(?:\.\d+)?)|\b(ek|do|teen|char|half|aadha|adha)\b/);
    const qty = m ? (m[1] ? +m[1] : NUM[m[2]]) : 1;
    const base = { raw, pic: p.pic, conf: p.options ? 70 : 98, name: p.name, qty, unit: p.unit, price: p.price || 0 };
    if (p.options) return { ...base, status: 'ambiguous', options: p.options, note: 'Which one?' };
    if (qty > p.stock) return { ...base, status: 'oos', note: p.stock ? `Only ${p.stock} ${p.unit} in stock` : 'Out of stock' };
    return { ...base, status: 'ok' };
  });
  return { id: 'demo-' + Date.now(), items, clarification: makeClarification(items) };
}
export function makeClarification(items) {
  const q = items.flatMap(i => i.status === 'ambiguous' ? [`${i.name}: ${i.options.map(o => o.label).join(', ')} — kaunsa chahiye?`]
    : i.status === 'oos' ? [`${i.name} abhi available nahi hai (${i.note}).`]
    : i.status === 'unknown' ? [`"${i.raw}" samajh nahi aaya, please batayein.`] : []);
  return q.length ? 'Namaste! ' + q.join(' ') : '';
}
export const parseOrder = message => DEMO ? Promise.resolve(mockParse(message)) : req('/orders/parse', { method: 'POST', body: JSON.stringify({ message }) });
export function confirmOrder(id, items, message = '') {
  if (!DEMO) return req('/orders/confirm', { method: 'POST', body: JSON.stringify({ id, items }) });
  const lines = items.map(i => ({ name: i.name, qty: i.qty, unit: i.unit, price: i.price, total: i.qty * i.price }));
  const total = lines.reduce((s, l) => s + l.total, 0);
  return Promise.resolve({ bill: { lines, subtotal: total, total },
    deliveryNote: /kal subah/i.test(message) ? 'Deliver tomorrow morning.' : 'Deliver today.' });
}
