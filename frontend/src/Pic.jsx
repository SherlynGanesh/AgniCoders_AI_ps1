import { useState } from 'react';
const bg = ['#E6F7F1', '#EDE9FE', '#FEF3C7', '#DBEAFE', '#D1FAE5'];
// Zepto-style tile: white background, product photo contained. Falls back to emoji if the photo file is missing.
export function Pic({ p, size = '' }) {
  const [bad, setBad] = useState(false);
  return p.img && !bad
    ? <img className={'pic photo ' + size} src={p.img} alt={p.name} onError={() => setBad(true)} />
    : <span className={'pic ' + size} style={{ background: bg[p.id % 5] }} role="img" aria-label={p.name}>{p.emoji || '🛒'}</span>;
}
