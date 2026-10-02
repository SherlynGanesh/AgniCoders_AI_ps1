import { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import * as auth from './authService';
import * as api from './api';
import { SPEECH } from './i18n';
import { useAuth } from './AuthContext';

const inr = n => '₹' + (+n).toLocaleString('en-IN');

const STORE_SAMPLES = [
  { label: '🛒 Grocery & Dairy', text: 'Bhaiya, 2 kilo atta, ek Amul butter aur sugar aadha kilo, kal subah tak bhej dena' },
  { label: '🧴 Personal & Home Care', text: 'Dettol soap 2 piece, coconut oil 200ml aur plastic bathroom mug bhej do' },
  { label: '🍜 Packaged Food & Snacks', text: 'Maggi 4 pack, Parle-G biscuit aur tea masala chahiye' },
];

const LBL = { ok: 'Matched', ambiguous: 'Needs selection', oos: 'Stock issue', unknown: 'Not found' };

// Convert Float32Array PCM samples into standard 16-bit PCM WAV
function encodeWAV(samples, sampleRate) {
  const buffer = new ArrayBuffer(44 + samples.length * 2);
  const view = new DataView(buffer);

  const writeString = (offset, string) => {
    for (let i = 0; i < string.length; i++) {
      view.setUint8(offset + i, string.charCodeAt(i));
    }
  };

  writeString(0, 'RIFF');
  view.setUint32(4, 36 + samples.length * 2, true);
  writeString(8, 'WAVE');
  writeString(12, 'fmt ');
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true); // PCM format
  view.setUint16(22, 1, true); // Mono channel
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * 2, true); // Byte rate
  view.setUint16(32, 2, true); // Block align
  view.setUint16(34, 16, true); // 16 bits per sample
  writeString(36, 'data');
  view.setUint32(40, samples.length * 2, true);

  let offset = 44;
  for (let i = 0; i < samples.length; i++) {
    const s = Math.max(-1, Math.min(1, samples[i]));
    view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7FFF, true);
    offset += 2;
  }

  return new Blob([view], { type: 'audio/wav' });
}

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

  // Audio level & status
  const [audioLevel, setAudioLevel] = useState(0);
  const [audioAudible, setAudioAudible] = useState(false);
  const [statusMsg, setStatusMsg] = useState('');

  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const micStreamRef = useRef(null);
  const audioContextRef = useRef(null);
  const animFrameRef = useRef(null);
  const speechRecRef = useRef(null);
  const recognizedTextRef = useRef('');

  // Clean up streams on unmount
  useEffect(() => {
    return () => {
      stopAllAudio();
    };
  }, []);

  const stopAllAudio = () => {
    if (animFrameRef.current) {
      cancelAnimationFrame(animFrameRef.current);
      animFrameRef.current = null;
    }
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      try { mediaRecorderRef.current.stop(); } catch (_) {}
    }
    if (speechRecRef.current) {
      try { speechRecRef.current.stop(); } catch (_) {}
      speechRecRef.current = null;
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

  const handleMicClick = async () => {
    setErr('');

    if (live) {
      // User tapped Stop -> Finish recording and process
      setStatusMsg('Finishing recording…');
      setLive(false);
      if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
        mediaRecorderRef.current.stop();
      }
      if (speechRecRef.current) {
        try { speechRecRef.current.stop(); } catch (_) {}
      }
      return;
    }

    try {
      setStatusMsg('Requesting microphone access…');
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true
        }
      });
      micStreamRef.current = stream;

      // 1. Setup AudioContext & Analyser for real-time visual meter
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      const audioCtx = new AudioCtx();
      if (audioCtx.state === 'suspended') {
        await audioCtx.resume();
      }
      audioContextRef.current = audioCtx;

      const source = audioCtx.createMediaStreamSource(stream);
      const analyser = audioCtx.createAnalyser();
      analyser.fftSize = 256;
      source.connect(analyser);

      const bufferLength = analyser.frequencyBinCount;
      const dataArray = new Uint8Array(bufferLength);

      const monitorAudio = () => {
        if (!micStreamRef.current) return;
        analyser.getByteFrequencyData(dataArray);

        let sum = 0;
        for (let i = 0; i < bufferLength; i++) {
          sum += dataArray[i];
        }
        const avg = sum / bufferLength;
        const level = Math.min(100, Math.round((avg / 128) * 100));
        setAudioLevel(level);

        if (level > 4) {
          setAudioAudible(true);
        } else {
          setAudioAudible(false);
        }

        animFrameRef.current = requestAnimationFrame(monitorAudio);
      };
      animFrameRef.current = requestAnimationFrame(monitorAudio);

      // 2. Setup standard browser MediaRecorder (100% reliable)
      audioChunksRef.current = [];
      let mimeType = '';
      if (typeof MediaRecorder !== 'undefined') {
        if (MediaRecorder.isTypeSupported('audio/webm;codecs=opus')) mimeType = 'audio/webm;codecs=opus';
        else if (MediaRecorder.isTypeSupported('audio/webm')) mimeType = 'audio/webm';
        else if (MediaRecorder.isTypeSupported('audio/mp4')) mimeType = 'audio/mp4';
      }

      const recorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);
      mediaRecorderRef.current = recorder;

      recorder.ondataavailable = (e) => {
        if (e.data && e.data.size > 0) {
          audioChunksRef.current.push(e.data);
        }
      };

      recorder.onstop = async () => {
        const chunks = audioChunksRef.current;
        stopAllAudio();

        if (!chunks || chunks.length === 0) {
          if (recognizedTextRef.current) {
            runWith(recognizedTextRef.current);
          } else {
            setErr('No audio captured. Please speak into the mic.');
          }
          return;
        }

        const rawBlob = new Blob(chunks, { type: recorder.mimeType || 'audio/webm' });
        await processAndSendAudio(rawBlob);
      };

      // 3. Optional live SpeechRecognition preview in parallel
      recognizedTextRef.current = '';
      const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
      if (SpeechRecognition) {
        try {
          const sr = new SpeechRecognition();
          sr.continuous = false;
          sr.interimResults = true;
          sr.lang = SPEECH[lang] || 'hi-IN';

          sr.onresult = (e) => {
            const transcript = Array.from(e.results).map(res => res[0].transcript).join('');
            if (transcript) {
              recognizedTextRef.current = transcript;
              setMsg(transcript);
            }
          };

          sr.onerror = (e) => {
            console.debug('Client speech recognition notice:', e.error);
          };

          speechRecRef.current = sr;
          sr.start();
        } catch (_) {}
      }

      recorder.start(100);
      setLive(true);
      setStatusMsg('🔴 Recording… Speak your order now (Tap mic when done)');

    } catch (e) {
      stopAllAudio();
      setLive(false);
      setErr('Microphone access denied. Please click the lock icon in your address bar and Allow microphone: ' + (e.message || ''));
    }
  };

  const processAndSendAudio = async (rawBlob) => {
    setBusy(true);
    setStatusMsg('Encoding audio & processing with Backend AI Desk…');

    try {
      // Decode audio blob into PCM samples using Web Audio API
      let wavBlob = null;
      try {
        const arrayBuffer = await rawBlob.arrayBuffer();
        const decodeCtx = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: 16000 });
        if (decodeCtx.state === 'suspended') {
          await decodeCtx.resume();
        }
        const audioBuffer = await decodeCtx.decodeAudioData(arrayBuffer);
        const pcmChannel = audioBuffer.getChannelData(0);
        wavBlob = encodeWAV(pcmChannel, audioBuffer.sampleRate);
        decodeCtx.close();
      } catch (decodeErr) {
        console.warn('Direct decode failed, sending raw blob:', decodeErr);
        wavBlob = rawBlob;
      }

      // Send WAV to Backend Voice Engine
      const res = await api.sendVoiceOrder(wavBlob);

      if (res.transcript) {
        setMsg(res.transcript);
      } else if (recognizedTextRef.current && !res.items?.length) {
        // If client recognition caught text but backend had low mic volume, re-parse with text
        const clientRes = await api.parseOrder(recognizedTextRef.current);
        setOrder(clientRes);
        setStatusMsg('');
        return;
      }

      setOrder(res);
      setStatusMsg('');
    } catch (e) {
      // If backend network error but client recognition has text, fall back to parsing text
      if (recognizedTextRef.current) {
        try {
          const fallbackRes = await api.parseOrder(recognizedTextRef.current);
          setOrder(fallbackRes);
          setStatusMsg('');
          return;
        } catch (_) {}
      }
      setErr('Speech processing note: ' + (e.message || 'Please check mic or try typing.'));
    } finally {
      setBusy(false);
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
            Backend AI Voice &amp; PostgreSQL Engine
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
              onClick={handleMicClick}
              disabled={busy}
              aria-label="Tap to speak"
              style={{
                boxShadow: live ? '0 0 0 10px rgba(239, 68, 68, 0.25)' : 'none',
                transition: 'all 0.2s ease',
                cursor: busy ? 'wait' : 'pointer'
              }}
            >
              🎙
            </button>
            <p style={{ marginTop: 8 }}>
              <b>{busy ? '⏳ Processing speech on backend…' : live ? '🔴 Recording… Tap again to STOP & Process' : 'Tap microphone to speak'}</b>
            </p>
            <p className="muted" style={{ fontSize: 13 }}>
              {statusMsg || (live ? 'Speak your order into the microphone (Hindi / Marathi / Hinglish)' : 'Direct backend audio recognition with Marathi disambiguation')}
            </p>

            {/* Live Real-time Decibel / Volume Meter */}
            {live && (
              <div style={{ margin: '14px auto 8px', maxWidth: 300, background: '#f3f4f6', padding: '8px 12px', borderRadius: 10 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, marginBottom: 4, fontWeight: 600 }}>
                  <span style={{ color: audioAudible ? '#059669' : '#9ca3af' }}>
                    {audioAudible ? '🔊 Voice Audible' : '🔇 Low Volume / Silent'}
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

        <textarea
          value={msg}
          onChange={e => setMsg(e.target.value)}
          onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); runWith(msg); } }}
          rows={3}
          placeholder="e.g. 2 kilo atta, ek butter de do… (or click mic above)"
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
            onClick={handleMicClick}
            disabled={busy}
            style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}
          >
            🎙️ {live ? '🔴 Stop & Submit' : 'Record Mic'}
          </button>
        </div>

        {err && <p className="err" role="alert" style={{ marginTop: 8 }}>{err}</p>}

        {/* Quick Store Samples */}
        <div className="demobox" style={{ marginTop: 14 }}>
          <b style={{ color: '#1e293b', fontSize: 13 }}>🛒 Quick Store Order Samples:</b>
          <div className="row l" style={{ marginTop: 6, flexWrap: 'wrap', gap: 6 }}>
            {STORE_SAMPLES.map(s => (
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
            Speak into the microphone or type above. DukaanMitra transcribes your audio on the backend, detects Marathi vs Hindi meanings, and matches against your 5,500+ store catalog.
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
                  const isWarning = flag.includes('⚠️') || flag.includes('Alert') || flag.includes('Warning') || flag.includes('audible');
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

            <p className="muted" style={{ marginTop: 14 }}>Extracted Store Items ({order.items?.length || 0})</p>

            {!order.items || order.items.length === 0 ? (
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
                  The speech did not contain recognized catalog items. Click one of the samples above or speak again.
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
              ) : order.items && order.items.length > 0 ? (
                <p className="warn" style={{ textAlign: 'center' }}>
                  ⚠️ Some items need variant selection before confirmation
                </p>
              ) : null}
            </div>
          </>
        )}
      </section>

      {/* Ambiguity Selection Modal */}
      {sel !== null && order?.items && order.items[sel] && (
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
