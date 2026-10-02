import { useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import * as auth from './authService';
import * as api from './api';
import { SPEECH } from './i18n';
import { useAuth, useData } from './AuthContext';

const inr = n => '₹' + (+n).toLocaleString('en-IN');
const SAMPLES = [
  { label: '🛒 Grocery & Dairy', text: 'Bhaiya, 2 kilo atta, ek Amul butter aur sugar aadha kilo, tel bhi chahiye, kal subah tak bhej dena' },
  { label: '🧴 Personal & Home Care', text: 'Dettol soap 2 piece, coconut oil 200ml aur plastic bathroom mug bhej do' },
  { label: '🍜 Packaged Food & Snacks', text: 'Maggi 4 pack, Parle-G biscuit aur tea masala chahiye' },
];
const LBL = { ok: 'Matched', ambiguous: 'Needs selection', oos: 'Stock issue', unknown: 'Not found' };

export default function NewOrder() {
  const { lang } = useAuth(), go = useNavigate();
  const [msg, setMsg] = useState(''), [order, setOrder] = useState(null), [sel, setSel] = useState(null), [pick, setPick] = useState(0);
  const [tab, setTab] = useState('voice'), [busy, setBusy] = useState(false), [err, setErr] = useState(''), [live, setLive] = useState(false), [copied, setCopied] = useState(false), rec = useRef();
  const speak = () => {
    const S = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!S) return setErr('Voice input is not supported in this browser. Use Type Order instead.');
    if (live) return rec.current.stop();
    const r = new S(); r.lang = SPEECH[lang] || 'hi-IN'; r.onresult = e => setMsg(e.results[0][0].transcript); r.onend = () => setLive(false);
    rec.current = r; r.start(); setLive(true);
  };
  const run = async () => { if (!msg.trim() || busy) return; setBusy(true); setErr('');
    try { setOrder(await api.parseOrder(msg)); } catch (e) { setErr(e.message); } finally { setBusy(false); } };
  const update = items => setOrder(o => ({ ...o, items, clarification: api.makeClarification(items) }));
  const choose = () => { const o = order.items[sel].options[pick];
    update(order.items.map((it, n) => n === sel ? { ...it, name: o.label, price: o.price, status: 'ok', conf: 95, options: undefined, note: '' } : it)); setSel(null); };
  const ready = order && order.items.length > 0 && order.items.every(i => i.status === 'ok');
  const review = () => go('/confirm', { state: { order, msg } });

  return (
    <div className="vgrid">
      <section className="card vcard">
        <div className="tabs"><button className={tab === 'voice' ? 'on' : ''} onClick={() => setTab('voice')}>Voice Order</button>
          <button className={tab === 'type' ? 'on' : ''} onClick={() => setTab('type')}>Type Order</button></div>
        {tab === 'voice' && <><button className={'mic' + (live ? ' live' : '')} onClick={speak} aria-label="Tap to speak">🎙</button>
          <p><b>{live ? 'Listening… tap to stop' : 'Tap to speak'}</b></p><p className="muted">or type your order</p></>}
        <textarea value={msg} onChange={e => setMsg(e.target.value)} rows={3} placeholder="e.g. 2 kilo atta, ek butter de do…" />
        <button className="cta" onClick={run} disabled={busy || !msg.trim()}>{busy && !order ? 'Processing…' : 'Process'}</button>
        <div className="demobox">
          <b>Quick Order Samples:</b>
          <div className="row l" style={{ marginTop: 6, flexWrap: 'wrap', gap: 6 }}>
            {SAMPLES.map(s => (
              <button key={s.label} type="button" className="btn-sm" onClick={() => setMsg(s.text)}>
                {s.label}
              </button>
            ))}
          </div>
        </div>
      </section>
      <section className="card">
        <h2>AI Understanding</h2>
        {!order ? <p className="muted">Speak or type an order. Items will be extracted and matched to your catalog here.</p> : <>
          <p className="muted">Original Transcript</p><p className="tbox">{msg}</p>
          <p className="muted">Extracted Items</p>
          {order.items.map((it, i) => <div className="xi" key={i}><span className="pic sm">{it.pic || '🛒'}</span>
            <div style={{ flex: 1 }}><b>{it.name}</b> <span className="muted">{it.qty} {it.unit}</span>{it.note && <div className="note">{it.note}</div>}</div>
            <span className="muted">{it.conf}%</span><span className={'chip ' + it.status}>{LBL[it.status]}</span>
            {it.status === 'ok' ? <b>{inr(it.qty * it.price)}</b> : it.options ? <button className="btn-sm" onClick={() => { setSel(i); setPick(0); }}>Choose</button>
              : <button className="link" onClick={() => update(order.items.filter((_, n) => n !== i))}>Remove</button>}</div>)}
          {order.clarification && <div className="clar"><b>Reply to customer</b><p>{order.clarification}</p>
            <button className="link" onClick={() => { navigator.clipboard?.writeText(order.clarification); setCopied(true); setTimeout(() => setCopied(false), 1500); }}>{copied ? 'Copied' : 'Copy message'}</button></div>}
          {ready ? <button className="cta" onClick={review}>Review &amp; confirm</button> : <p className="warn">Some items need your confirmation</p>}</>}
      </section>
      {sel !== null && <div className="modal" role="dialog" aria-modal="true"><div className="card mbox"><h2>Which {order.items[sel].name.toLowerCase()} do you want?</h2>
        <p className="muted">Multiple products match. Please choose the correct item.</p>
        {order.items[sel].options.map((o, k) => <label key={o.label} className={'radio' + (pick === k ? ' on' : '')}><input type="radio" checked={pick === k} onChange={() => setPick(k)} /> {o.label}<b>{inr(o.price)}</b></label>)}
        <div className="row"><button className="btn ghost" onClick={() => setSel(null)}>Cancel</button><button className="cta" onClick={choose}>Confirm</button></div></div></div>}
    </div>
  );
}
