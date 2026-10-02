import { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import * as auth from './authService';
import * as api from './api';
import { SPEECH } from './i18n';
import { useAuth } from './AuthContext';

const inr = n => '₹' + (+n).toLocaleString('en-IN');

const MARATHI_SAMPLES = [
  { label: '🌾 2 kilo atta, ek butter (Wheat Flour)', text: '2 kilo atta, ek amul butter' },
  { label: '⚡ Aata 2 packet milk bhej do (Marathi Now)', text: 'aata 2 packet milk bhej do' },
  { label: '🗣️ Aata dya bhaiya, urgent lagel (Marathi Imperative)', text: 'aata dya bhaiya, urgent lagel' },
  { label: '❓ Atta de do (Ambiguity check)', text: 'atta de do' },
  { label: '🔇 Hnmm shhh... (Inaudible / Low context)', text: 'hnmm shhh...' },
];

const RETAIL_SAMPLES = [
  { label: '🛒 Grocery & Dairy (Kal subah)', text: 'Bhaiya, 2 kilo atta, ek Amul butter aur sugar aadha kilo, kal subah tak bhej dena' },
  { label: '🧴 Personal & Home Care', text: 'Dettol soap 2 piece, coconut oil 200ml aur plastic bathroom mug bhej do' },
  { label: '🍜 Packaged Food & Snacks', text: 'Maggi 4 pack, Parle-G biscuit aur tea masala chahiye' },
];

const LBL = { ok: 'Matched', ambiguous: 'Needs selection', oos: 'Stock issue', unknown: 'Not found' };

export default function NewOrder() {
  const { lang } = useAuth(), go = useNavigate();
  const [msg, setMsg] = useState('');
  const [order, setOrder] = useState(null);
  const [sel, setSel] = useState(null);
  const [pick, setPick] = useState(0);
  const [tab, setTab] = useState('voice');
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState('');
  const [live, setLive] = useState(false);
  const [copied, setCopied] = useState(false);

  // Audio level & inaudible detection
  const [audioLevel, setAudioLevel] = useState(0);
  const [audioAudible, setAudioAudible] = useState(false);
  const [audioWarning, setAudioWarning] = useState('');

  const recRef = useRef(null);
  const audioContextRef = useRef(null);
  const analyserRef = useRef(null);
  const micStreamRef = useRef(null);
  const animFrameRef = useRef(null);

  // Clean up audio & mic streams on unmount
  useEffect(() => {
    return () => {
      stopAudioMonitoring();
      if (recRef.current) {
        try { recRef.current.abort(); } catch (_) {}
      }
    };
  }, []);

  const stopAudioMonitoring = () => {
    if (animFrameRef.current) {
      cancelAnimationFrame(animFrameRef.current);
      animFrameRef.current = null;
    }
    if (micStreamRef.current) {
      micStreamRef.current.getTracks().forEach(t => t.stop());
      micStreamRef.current = null;
    }
    if (audioContextRef.current) {
      try { audioContextRef.current.close(); } catch (_) {}
      audioContextRef.current = null;
    }
    setAudioLevel(0);
    setAudioAudible(false);
  };

  const stopListening = () => {
    stopAudioMonitoring();
    if (recRef.current) {
      try { recRef.current.stop(); } catch (_) {}
      recRef.current = null;
    }
    setLive(false);
  };

  const startListening = async () => {
    setErr('');
    setAudioWarning('');

    if (live) {
      stopListening();
      return;
    }

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      setErr('Voice recognition requires Google Chrome or Edge. You can use Type Order or click the samples below.');
      return;
    }

    try {
      // 1. Setup Web Audio API volume & audible detection
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      micStreamRef.current = stream;

      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      const audioCtx = new AudioCtx();
      audioContextRef.current = audioCtx;

      const source = audioCtx.createMediaStreamSource(stream);
      const analyser = audioCtx.createAnalyser();
      analyser.fftSize = 256;
      source.connect(analyser);
      analyserRef.current = analyser;

      const bufferLength = analyser.frequencyBinCount;
      const dataArray = new Uint8Array(bufferLength);
      let maxLevelSeen = 0;
      const startTime = Date.now();

      const monitorAudio = () => {
        if (!analyserRef.current) return;
        analyserRef.current.getByteFrequencyData(dataArray);

        let sum = 0;
        for (let i = 0; i < bufferLength; i++) {
          sum += dataArray[i];
        }
        const avg = sum / bufferLength;
        const level = Math.min(100, Math.round((avg / 128) * 100));
        setAudioLevel(level);

        if (level > 8) {
          maxLevelSeen = Math.max(maxLevelSeen, level);
          setAudioAudible(true);
          setAudioWarning('');
        } else {
          setAudioAudible(false);
        }

        // Diagnostic flag: If 2.5s pass and mic volume is near zero
        if (Date.now() - startTime > 2500 && maxLevelSeen < 8) {
          setAudioWarning('⚠️ You are not audible. Please speak louder or move closer to the mic.');
        }

        animFrameRef.current = requestAnimationFrame(monitorAudio);
      };
      animFrameRef.current = requestAnimationFrame(monitorAudio);

      // 2. Setup Speech Recognition
      const r = new SpeechRecognition();
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
          stopListening();
          runWith(text);
        }
      };

      r.onerror = (e) => {
        console.warn('SpeechRecognition error:', e.error);
        stopListening();
        if (e.error === 'not-allowed') {
          setErr('Microphone permission blocked. Click the lock icon in your browser URL bar to allow microphone access.');
        } else if (e.error === 'no-speech') {
          setAudioWarning('⚠️ You are not audible: No speech was detected by the microphone. Please speak louder or choose a sample.');
        } else if (e.error === 'network') {
          setErr('Speech recognition cloud connection unavailable. Please use the quick samples or Type Order.');
        } else {
          setErr(`Microphone input issue: ${e.error}. Try again or select a test sample.`);
        }
      };

      r.onend = () => {
        stopListening();
      };

      recRef.current = r;
      r.start();
    } catch (e) {
      stopListening();
      setErr('Microphone access failed: ' + (e.message || 'permission denied'));
    }
  };

  const runWith = async (text) => {
    const query = (typeof text === 'string' ? text : msg).trim();
    if (!query || busy) return;
    setBusy(true);
    setErr('');
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
  const choose = () => {
    const o = order.items[sel].options[pick];
    update(order.items.map((it, n) => n === sel ? { ...it, name: o.label, price: o.price, status: 'ok', conf: 95, options: undefined, note: '' } : it));
    setSel(null);
  };

  const ready = order && order.items && order.items.length > 0 && order.items.every(i => i.status === 'ok');
  const review = () => go('/confirm', { state: { order, msg } });

  return (
    <div className="vgrid">
      <section className="card vcard">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6, fontSize: 12, fontWeight: 600, color: '#059669', background: '#ecfdf5', padding: '4px 12px', borderRadius: 12 }}>
            <span style={{ width: 8, height: 8, borderRadius: '50%', background: '#10b981', display: 'inline-block' }}></span>
            PostgreSQL AI Backend Connected
          </span>
          {order?.contextQuality && (
            <span style={{
              fontSize: 11,
              fontWeight: 700,
              padding: '3px 8px',
              borderRadius: 8,
              background: order.contextQuality === 'CLEAR' ? '#ecfdf5' : order.contextQuality === 'AMBIGUOUS' ? '#fef3c7' : '#fee2e2',
              color: order.contextQuality === 'CLEAR' ? '#065f46' : order.contextQuality === 'AMBIGUOUS' ? '#92400e' : '#991b1b'
            }}>
              Context: {order.contextQuality}
            </span>
          )}
        </div>

        <div className="tabs">
          <button className={tab === 'voice' ? 'on' : ''} onClick={() => setTab('voice')}>Voice Order</button>
          <button className={tab === 'type' ? 'on' : ''} onClick={() => setTab('type')}>Type Order</button>
        </div>

        {tab === 'voice' && (
          <div style={{ textAlign: 'center', padding: '10px 0' }}>
            <button
              className={'mic' + (live ? ' live' : '')}
              onClick={startListening}
              aria-label="Tap to speak"
              style={{
                boxShadow: live ? '0 0 0 10px rgba(239, 68, 68, 0.25)' : 'none',
                transition: 'all 0.2s ease'
              }}
            >
              🎙
            </button>
            <p style={{ marginTop: 8 }}>
              <b>{live ? '🔴 Listening… Speak now (Tap to stop)' : 'Tap microphone to speak'}</b>
            </p>
            <p className="muted" style={{ fontSize: 13 }}>
              {live ? 'Speak in Hindi / Marathi / Hinglish (e.g. 2 kilo atta, ek butter)' : 'Or choose sample / type your order below'}
            </p>

            {/* Live Real-time Decibel / Volume Meter */}
            {live && (
              <div style={{ margin: '14px auto 8px', maxWidth: 300, background: '#f3f4f6', padding: '8px 12px', borderRadius: 10 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, marginBottom: 4, fontWeight: 600 }}>
                  <span style={{ color: audioAudible ? '#059669' : '#9ca3af' }}>
                    {audioAudible ? '🔊 Voice Audible' : '🔇 Low Volume'}
                  </span>
                  <span style={{ color: '#4b5563' }}>{audioLevel}%</span>
                </div>
                <div style={{ width: '100%', height: 8, background: '#e5e7eb', borderRadius: 4, overflow: 'hidden' }}>
                  <div style={{
                    width: `${audioLevel}%`,
                    height: '100%',
                    background: audioAudible ? 'linear-gradient(90deg, #10b981, #059669)' : '#f59e0b',
                    transition: 'width 0.1s ease'
                  }}></div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Diagnostic Audio Warning */}
        {audioWarning && (
          <div style={{
            background: '#fffbeb',
            border: '1px solid #fde68a',
            color: '#b45309',
            padding: '8px 12px',
            borderRadius: 8,
            fontSize: 13,
            fontWeight: 600,
            marginBottom: 10
          }}>
            {audioWarning}
          </div>
        )}

        <textarea
          value={msg}
          onChange={e => setMsg(e.target.value)}
          onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); runWith(msg); } }}
          rows={3}
          placeholder="e.g. 2 kilo atta, ek butter de do… (press Enter to process)"
        />

        <div className="row l" style={{ marginTop: 8, gap: 8 }}>
          <button
            className="cta"
            onClick={() => runWith(msg)}
            disabled={busy || !msg.trim()}
            style={{ flex: 1 }}
          >
            {busy ? 'Processing with AI Desk…' : 'Process Order'}
          </button>
          <button
            type="button"
            className={'btn ' + (live ? 'cta' : 'ghost')}
            onClick={startListening}
            style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}
          >
            🎙️ {live ? '🔴 Stop Mic' : 'Speak'}
          </button>
        </div>

        {err && <p className="err" role="alert" style={{ marginTop: 8 }}>{err}</p>}

        {/* Linguistic Test Samples: Marathi vs Wheat Flour */}
        <div className="demobox" style={{ marginTop: 14 }}>
          <b style={{ color: '#1e293b', fontSize: 13 }}>🌾 Marathi vs Atta Disambiguation Tests:</b>
          <div className="row l" style={{ marginTop: 6, flexWrap: 'wrap', gap: 6 }}>
            {MARATHI_SAMPLES.map(s => (
              <button
                key={s.label}
                type="button"
                className="btn-sm"
                style={{ fontSize: 11, padding: '4px 8px' }}
                onClick={() => { setMsg(s.text); runWith(s.text); }}
              >
                {s.label}
              </button>
            ))}
          </div>
        </div>

        {/* General Retail Samples */}
        <div className="demobox" style={{ marginTop: 10 }}>
          <b style={{ color: '#1e293b', fontSize: 13 }}>🛒 General Retail & Grocery Samples:</b>
          <div className="row l" style={{ marginTop: 6, flexWrap: 'wrap', gap: 6 }}>
            {RETAIL_SAMPLES.map(s => (
              <button
                key={s.label}
                type="button"
                className="btn-sm"
                style={{ fontSize: 11, padding: '4px 8px' }}
                onClick={() => { setMsg(s.text); runWith(s.text); }}
              >
                {s.label}
              </button>
            ))}
          </div>
        </div>
      </section>

      {/* AI Understanding & Verification Card */}
      <section className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
          <h2>AI Understanding</h2>
          <small className="muted">Live PostgreSQL Matching</small>
        </div>

        {!order ? (
          <p className="muted" style={{ marginTop: 14 }}>
            Speak or type an order above. DukaanMitra will extract products, detect Marathi vs Hindi meanings, and match against your 5,500+ store catalog.
          </p>
        ) : (
          <>
            <p className="muted" style={{ marginTop: 10 }}>Customer Said</p>
            <p className="tbox">{msg}</p>

            {/* Delivery Note / Urgency Banner */}
            {order.deliveryNote && (
              <div style={{
                background: '#eff6ff',
                border: '1px solid #bfdbfe',
                color: '#1e40af',
                padding: '8px 12px',
                borderRadius: 8,
                fontSize: 13,
                fontWeight: 600,
                marginTop: 8,
                display: 'flex',
                alignItems: 'center',
                gap: 8
              }}>
                <span>⚡</span>
                <span>{order.deliveryNote}</span>
              </div>
            )}

            {/* AI Flags & Linguistic Insights */}
            {order.flags && order.flags.length > 0 && (
              <div style={{ marginTop: 10, display: 'flex', flexDirection: 'column', gap: 6 }}>
                {order.flags.map((flag, idx) => {
                  const isWarning = flag.includes('⚠️') || flag.includes('Alert');
                  const isAmbiguous = flag.includes('🟡') || flag.includes('Ambiguity');
                  const bg = isWarning ? '#fee2e2' : isAmbiguous ? '#fef3c7' : '#ecfdf5';
                  const color = isWarning ? '#991b1b' : isAmbiguous ? '#92400e' : '#065f46';
                  const border = isWarning ? '#fca5a5' : isAmbiguous ? '#fde68a' : '#a7f3d0';

                  return (
                    <div
                      key={idx}
                      style={{
                        background: bg,
                        color: color,
                        border: `1px solid ${border}`,
                        padding: '6px 10px',
                        borderRadius: 6,
                        fontSize: 12,
                        fontWeight: 600,
                        lineHeight: 1.4
                      }}
                    >
                      {flag}
                    </div>
                  );
                })}
              </div>
            )}

            <p className="muted" style={{ marginTop: 14 }}>Extracted Store Items ({order.items.length})</p>

            {order.items.length === 0 ? (
              <div style={{
                background: '#f8fafc',
                border: '1px dashed #cbd5e1',
                padding: '16px',
                borderRadius: 8,
                textAlign: 'center',
                color: '#64748b',
                marginTop: 6
              }}>
                <span style={{ fontSize: 24, display: 'block', marginBottom: 4 }}>🔍</span>
                <b>No items matched</b>
                <p style={{ fontSize: 12, margin: '4px 0 0' }}>
                  The input did not contain recognized catalog items. Click one of the test samples above or rephrase.
                </p>
              </div>
            ) : (
              order.items.map((it, i) => (
                <div className="xi" key={i}>
                  <span className="pic sm">{it.pic || '🛒'}</span>
                  <div style={{ flex: 1 }}>
                    <b>{it.name}</b> <span className="muted">{it.qty} {it.unit}</span>
                    {it.note && <div className="note">{it.note}</div>}
                  </div>
                  <span className="muted">{it.conf}%</span>
                  <span className={'chip ' + it.status}>{LBL[it.status] || it.status}</span>
                  {it.status === 'ok' ? (
                    <b>{inr(it.qty * it.price)}</b>
                  ) : it.options ? (
                    <button className="btn-sm" onClick={() => { setSel(i); setPick(0); }}>Choose</button>
                  ) : (
                    <button className="link" onClick={() => update(order.items.filter((_, n) => n !== i))}>Remove</button>
                  )}
                </div>
              ))
            )}

            {order.clarification && (
              <div className="clar" style={{ marginTop: 12 }}>
                <b>Reply to customer</b>
                <p>{order.clarification}</p>
                <button
                  className="link"
                  onClick={() => {
                    navigator.clipboard?.writeText(order.clarification);
                    setCopied(true);
                    setTimeout(() => setCopied(false), 1500);
                  }}
                >
                  {copied ? '✓ Copied to clipboard' : 'Copy message'}
                </button>
              </div>
            )}

            <div style={{ marginTop: 16 }}>
              {ready ? (
                <button className="cta" onClick={review} style={{ width: '100%' }}>
                  Review &amp; Confirm Order →
                </button>
              ) : order.items.length > 0 ? (
                <p className="warn" style={{ textAlign: 'center' }}>
                  ⚠️ Some items need variant selection before confirmation
                </p>
              ) : null}
            </div>
          </>
        )}
      </section>

      {/* Ambiguity Selection Modal */}
      {sel !== null && order?.items[sel] && (
        <div className="modal" role="dialog" aria-modal="true">
          <div className="card mbox">
            <h2>Which {order.items[sel].name.toLowerCase()} do you want?</h2>
            <p className="muted">Multiple products match your request. Please choose the correct variant from your catalog:</p>
            {order.items[sel].options.map((o, k) => (
              <label key={o.label} className={'radio' + (pick === k ? ' on' : '')}>
                <input type="radio" checked={pick === k} onChange={() => setPick(k)} />
                {o.label}
                <b>{inr(o.price)}</b>
              </label>
            ))}
            <div className="row" style={{ marginTop: 16 }}>
              <button className="btn ghost" onClick={() => setSel(null)}>Cancel</button>
              <button className="cta" onClick={choose}>Confirm Selection</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
