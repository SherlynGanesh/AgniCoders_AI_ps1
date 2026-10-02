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
  const textLower = msg.toLowerCase();
  const flags = [];
  let deliveryNote = '';
  let contextQuality = 'CLEAR';

  const hasTemporalAata = /\b(aata|atta)\s+(bhej|de\b|dya|pahije|lagel|nikal|lao|kar\b|delivery|jaldi|urgent)\b/i.test(textLower) ||
    /\b(bhej|de\b|dya|pahije|lagel|jaldi|urgent)\s+(aata|atta)\b/i.test(textLower);
  const hasCommodityAtta = /(\d+|ek|do|teen|char|chaar|paanch|panch|aadha|half|\bkg\b|\bkilo\b|\bpacket\b)\s*(kilo|kg|packet|g|gm)?\s+(atta|aata)\b/i.test(textLower) ||
    /\b(aashirvaad|pillsbury|fortune|gehun|sharbati|flour)\s+(atta|aata)\b/i.test(textLower);

  let cleaned = msg;
  if (hasTemporalAata && hasCommodityAtta) {
    flags.push("🟢 Multi-Context Resolved: Detected Wheat Flour ('Atta') AND Marathi Temporal Urgency ('Aata' -> Deliver Now).");
    deliveryNote = "Deliver immediately (Customer requested 'Aata / Now').";
    cleaned = cleaned.replace(/\b(aata|atta)\s+(bhej|de|dya|pahije|lagel|nikal|lao|kar|delivery)\b/gi, '$2');
  } else if (hasTemporalAata && !hasCommodityAtta) {
    flags.push("🟢 Marathi Linguistic Context: Resolved 'Aata' as Temporal Adverb (Deliver Immediately), not Wheat Flour.");
    deliveryNote = "Deliver immediately (Customer requested 'Aata / Now').";
    cleaned = cleaned.replace(/\b(aata|atta)\b/gi, '');
  } else if (hasCommodityAtta) {
    flags.push("🟢 Linguistic Disambiguation: Confirmed 'Atta' as Wheat Flour commodity based on numeric quantity/unit context.");
  } else if (/\b(atta|aata)\b/i.test(textLower)) {
    flags.push("🟡 Context Ambiguity: 'Atta' can mean Marathi 'Aata' (Now) or Wheat Flour. Clarification recommended.");
    contextQuality = "AMBIGUOUS";
  }

  const items = cleaned.split(/,|\baur\b|\band\b/i).map(s => s.trim()).filter(Boolean).map(raw => {
    const w = raw.toLowerCase();
    const p = CAT.find(c => c.k.some(k => w.includes(k)));
    if (!p) return null;
    const m = w.match(/(\d+(?:\.\d+)?)|\b(ek|do|teen|char|half|aadha|adha)\b/);
    const qty = m ? (m[1] ? +m[1] : NUM[m[2]]) : 1;
    const base = { raw, pic: p.pic, conf: p.options ? 70 : 98, name: p.name, qty, unit: p.unit, price: p.price || 0 };
    if (p.options) return { ...base, status: 'ambiguous', options: p.options, note: 'Which one?' };
    if (qty > p.stock) return { ...base, status: 'oos', note: p.stock ? `Only ${p.stock} ${p.unit} in stock` : 'Out of stock' };
    return { ...base, status: 'ok' };
  }).filter(Boolean);

  if (!items.length) {
    flags.push("⚠️ Audio / Context Alert: Could not extract recognizable store items from speech. Please speak louder or rephrase.");
    contextQuality = "INAUDIBLE";
  }

  return { id: 'demo-' + Date.now(), items, clarification: makeClarification(items), flags, contextQuality, deliveryNote };
}
export function makeClarification(items) {
  const q = items.flatMap(i => i.status === 'ambiguous' ? [`${i.name}: ${i.options.map(o => o.label).join(', ')} — kaunsa chahiye?`]
    : i.status === 'oos' ? [`${i.name} abhi available nahi hai (${i.note}).`]
    : i.status === 'unknown' ? [`"${i.raw}" samajh nahi aaya, please batayein.`] : []);
  return q.length ? 'Namaste! ' + q.join(' ') : '';
}
export const parseOrder = message => req('/orders/parse', { method: 'POST', body: JSON.stringify({ message }) }).catch(err => {
  console.warn('Backend request failed, falling back to local engine:', err);
  return mockParse(message);
});

export function confirmOrder(id, items, message = '', delivery_note = '') {
  return req('/orders/confirm', { method: 'POST', body: JSON.stringify({ id, items, message, delivery_note }) }).catch(() => {
    const lines = items.map(i => ({ name: i.name, qty: i.qty, unit: i.unit, price: i.price, total: i.qty * i.price }));
    const total = lines.reduce((s, l) => s + l.total, 0);
    return Promise.resolve({ bill: { lines, subtotal: total, total },
      deliveryNote: delivery_note || (/kal subah/i.test(message) ? 'Deliver tomorrow morning.' : 'Deliver today.') });
  });
}

export async function sendVoiceOrder(audioBlob) {
  const formData = new FormData();
  formData.append('audio', audioBlob, 'order_audio.wav');
  formData.append('shop_id', '1');

  const API_BASE = 'http://localhost:8000/api';
  const res = await fetch(`${API_BASE}/orders/voice`, {
    method: 'POST',
    body: formData,
  });
  if (!res.ok) throw new Error(`Backend voice error: ${res.statusText}`);
  return await res.json();
}

