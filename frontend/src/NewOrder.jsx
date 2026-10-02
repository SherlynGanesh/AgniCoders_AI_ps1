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
  const speak = async () => {
    setErr('');
    const S = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!S) {
      setErr('Voice recognition requires Google Chrome or Edge. You can use Type Order or click a sample below.');
      return;
    }
    if (live) {
      if (rec.current) {
        try { rec.current.stop(); } catch (_) {}
      }
      setLive(false);
      return;
    }

    try {
      if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
        try {
          const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
          stream.getTracks().forEach(t => t.stop());
        } catch (permErr) {
          setErr('Microphone access blocked. Click the lock icon in your browser address bar to Allow microphone.');
          return;
        }
      }

      const r = new S();
      r.continuous = false;
      r.interimResults = true;
      r.lang = SPEECH[lang] || 'hi-IN';

      r.onstart = () => {
        setLive(true);
        setErr('');
      };

      r.onresult = (e) => {
        const text = Array.from(e.results).map(res => res[0].transcript).join('');
        setMsg(text);
        if (e.results[0] && e.results[0].isFinal) {
          runWith(text);
        }
      };

      r.onerror = (e) => {
        console.warn('Voice recognition error:', e.error);
        setLive(false);
        if (e.error === 'not-allowed') {
          setErr('Microphone permission blocked. Please allow microphone in browser URL settings.');
        } else if (e.error === 'network') {
          setErr('Browser speech recognition network issue. Please use Quick Samples or Type Order.');
        } else if (e.error === 'no-speech') {
          setErr('No speech detected. Please speak closer to your microphone or click a sample order.');
        } else {
          setErr(`Voice recognition error: ${e.error}. Try again or use Type Order.`);
        }
      };

      r.onend = () => {
        setLive(false);
      };

      rec.current = r;
      r.start();
    } catch (e) {
      setLive(false);
      setErr('Microphone failed: ' + (e.message || 'unknown error'));
    }
  };

  const runWith = async (text) => {
    const query = (typeof text === 'string' ? text : msg).trim();
    if (!query || busy) return;
    setBusy(true); setErr('');
    try {
      const res = await api.parseOrder(query);
      setOrder(res);
    } catch (e) {
      setErr(e.message || 'Error processing order.');
    } finally {
      setBusy(false);
    }
  };
  const update = items => setOrder(o => ({ ...o, items, clarification: api.makeClarification(items) }));
  const choose = () => { const o = order.items[sel].options[pick];
    update(order.items.map((it, n) => n === sel ? { ...it, name: o.label, price: o.price, status: 'ok', conf: 95, options: undefined, note: '' } : it)); setSel(null); };
  const ready = order && order.items.length > 0 && order.items.every(i => i.status === 'ok');
  const review = () => go('/confirm', { state: { order, msg } });

  return (
    <div className="vgrid">
      <section className="card vcard">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6, fontSize: 12, fontWeight: 600, color: '#059669', background: '#ecfdf5', padding: '3px 10px', borderRadius: 12 }}>
            <span style={{ width: 8, height: 8, borderRadius: '50%', background: '#10b981', display: 'inline-block' }}></span>
            PostgreSQL AI Backend Connected
          </span>
        </div>
        <div className="tabs"><button className={tab === 'voice' ? 'on' : ''} onClick={() => setTab('voice')}>Voice Order</button>
          <button className={tab === 'type' ? 'on' : ''} onClick={() => setTab('type')}>Type Order</button></div>
        {tab === 'voice' && <><button className={'mic' + (live ? ' live' : '')} onClick={speak} aria-label="Tap to speak">🎙</button>
          <p><b>{live ? '🔴 Listening… speak now (tap to stop)' : 'Tap to speak'}</b></p>
          <p className="muted">{live ? 'Speak in Hindi/Hinglish (e.g. 2 kilo atta, ek butter)' : 'or click sample / type your order'}</p></>}
        <textarea
          value={msg}
          onChange={e => setMsg(e.target.value)}
          onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); runWith(msg); } }}
          rows={3}
          placeholder="e.g. 2 kilo atta, ek butter de do… (press Enter to process)"
        />
        <div className="row l" style={{ marginTop: 8, gap: 8 }}>
          <button className="cta" onClick={() => runWith(msg)} disabled={busy || !msg.trim()} style={{ flex: 1 }}>{busy ? 'Processing with AI Desk…' : 'Process'}</button>
          <button type="button" className={'btn ' + (live ? 'cta' : 'ghost')} onClick={speak} style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
            🎙️ {live ? '🔴 Stop' : 'Speak'}
          </button>
        </div>
        {err && <p className="err" role="alert" style={{ marginTop: 8 }}>{err}</p>}
        <div className="demobox">
          <b>Quick Order Samples (Click to auto-process):</b>
          <div className="row l" style={{ marginTop: 6, flexWrap: 'wrap', gap: 6 }}>
            {SAMPLES.map(s => (
              <button key={s.label} type="button" className="btn-sm" onClick={() => { setMsg(s.text); runWith(s.text); }}>
                {s.label}
              </button>
            ))}
          </div>
        </div>
      </section>
      <section className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
          <h2>AI Understanding</h2>
          <small className="muted">Live PostgreSQL Matching</small>
        </div>
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
