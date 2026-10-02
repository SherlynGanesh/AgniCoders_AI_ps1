import { useState, useEffect } from 'react';
import { Link, useNavigate, useLocation, useSearchParams } from 'react-router-dom';
import * as auth from './authService';
import { useAuth } from './AuthContext';

const strength = p => [/.{8,}/, /[A-Z]/, /[a-z]/, /\d/, /[^A-Za-z0-9]/].filter(r => r.test(p)).length;
const SL = ['Too weak', 'Weak', 'Fair', 'Good', 'Strong', 'Very strong'];
const okEmail = e => /^\S+@\S+\.\S+$/.test(e);

function useRun() {
  const [busy, setBusy] = useState(false), [err, setErr] = useState('');
  const run = async fn => { if (busy) return; setBusy(true); setErr('');
    try { await fn(); } catch (e) { setErr(e.message); return e; } finally { setBusy(false); } };
  return { busy, err, run };
}
const ART = {
  login: ['🏪', 'Smarter Orders. Smoother Business.', []],
  register: ['🏪', 'Grow Your Business with DukaanMitra', ['Voice based ordering', 'Smart inventory sync', 'Easy bill generation']],
  forgot: ['🔒', "Don't worry! We'll help you get back in.", []],
};
function Shell({ title, sub, children, art, flip, center }) {
  const [em, h, pts] = ART[art] || [];
  return (
    <main className="auth"><div className={'acard' + (flip ? ' flip' : '') + (center ? ' center' : '')}>
      <section className="aform">
        <div className="logo">🏪 DukaanMitra</div>
        <h2>{title}</h2>{sub && <p className="muted">{sub}</p>}
        {auth.DEMO && <p className="demo">Demo mode: simulated, not real security. Real verification needs the backend.</p>}
        {children}
      </section>
      {!center && em && <section className="aart"><div className="big" aria-hidden>{em}</div><h2>{h}</h2>
        <ul>{pts.map(t => <li key={t}>✓ {t}</li>)}</ul></section>}
    </div></main>
  );
}
function F({ label, err, pw, prefix, ...p }) {
  const [s, setS] = useState(false);
  return (
    <label>{label}
      <span className="pw">{prefix && <span className="muted">{prefix}</span>}
        <input {...p} type={pw ? (s ? 'text' : 'password') : p.type} aria-invalid={!!err} />
        {pw && <button type="button" className="link" onClick={() => setS(!s)}>{s ? 'Hide' : 'Show'}</button>}</span>
      {err && <small className="err">{err}</small>}
    </label>
  );
}
const Meter = ({ p }) => p ? <><div className="meter">{[0, 1, 2, 3, 4].map(i => <i key={i} className={i < strength(p) ? 'on' : ''} />)}</div><small className="muted">Strength: {SL[strength(p)]}</small></> : null;

export function Login() {
  const nav = useNavigate(), loc = useLocation(), { login, expired } = useAuth();
  const [f, setF] = useState({ email: '', password: '' }), [e, setE] = useState({}), { busy, err, run } = useRun();
  const submit = async ev => {
    ev.preventDefault(); const x = {};
    if (!okEmail(f.email) && !/^[6-9]\d{9}$/.test(f.email)) x.email = 'Enter a valid email or 10-digit mobile number.';
    if (!f.password) x.password = 'Enter your password.';
    setE(x); if (Object.keys(x).length) return;
    const r = await run(async () => { const d = await auth.login(f.email, f.password); login(d.user); nav(loc.state?.from || '/dashboard', { replace: true }); });
    if (r?.code === 'UNVERIFIED') nav('/verify', { state: { email: f.email } });
  };
  return (
    <Shell title="Welcome Back!" sub="Login to your DukaanMitra account" art="login" flip>
      {expired && <p className="err" role="alert">Your session expired. Log in again.</p>}
      {auth.DEMO && <p className="muted"><small>Demo tests: unverified@x.com, disabled@x.com, or password "wrong".</small></p>}
      <form onSubmit={submit} noValidate>
        <F label="Email or Mobile Number" autoComplete="username" value={f.email} err={e.email} onChange={ev => setF({ ...f, email: ev.target.value })} />
        <F label="Password" pw autoComplete="current-password" value={f.password} err={e.password} onChange={ev => setF({ ...f, password: ev.target.value })} />
        {err && <p className="err" role="alert">{err}</p>}
        <label className="chk"><input type="checkbox" defaultChecked /> Remember me</label>
        <button className="cta" disabled={busy}>{busy ? 'Signing in…' : 'Login'}</button>
        <p className="muted center">or</p><button type="button" className="gbtn" disabled title="Needs backend">Continue with Google</button>
      </form>
      <p className="split"><Link to="/forgot-password">Forgot password?</Link><Link to="/register">Create account</Link></p>
    </Shell>
  );
}

export function Register() {
  const nav = useNavigate(), { busy, err, run } = useRun(), [e, setE] = useState({});
  const [f, setF] = useState({ name: '', shop: '', email: '', phone: '', password: '', confirm: '', consent: false });
  const set = k => ev => setF({ ...f, [k]: ev.target.type === 'checkbox' ? ev.target.checked : ev.target.value });
  const submit = async ev => {
    ev.preventDefault(); const x = {};
    if (f.name.trim().length < 2) x.name = 'Enter your full name.';
    if (!f.shop.trim()) x.shop = 'Enter your shop name.';
    if (!okEmail(f.email)) x.email = 'Enter a valid email address.';
    if (!/^[6-9]\d{9}$/.test(f.phone)) x.phone = 'Enter a 10-digit Indian mobile number.';
    if (strength(f.password) < 4) x.password = 'Use 8+ characters with upper case, lower case and a number.';
    if (f.confirm !== f.password) x.confirm = 'Passwords do not match.';
    if (!f.consent) x.consent = 'Accept the terms and privacy policy to continue.';
    setE(x); if (Object.keys(x).length) return;
    const r = await run(() => auth.register({ name: f.name, shop: f.shop, email: f.email, phone: '+91' + f.phone, password: f.password, consent: true }));
    if (!r) nav('/verify', { state: { email: f.email, phone: '+91 ' + f.phone } });
  };
  return (
    <Shell title="Create Your Account" sub="Join DukaanMitra and take your shop digital" art="register">
      <form onSubmit={submit} noValidate>
        <F label="Your full name" value={f.name} err={e.name} onChange={set('name')} autoComplete="name" />
        <F label="Shop or business name" value={f.shop} err={e.shop} onChange={set('shop')} />
        <F label="Email" type="email" value={f.email} err={e.email} onChange={set('email')} autoComplete="email" />
        <F label="Mobile number" prefix="+91" inputMode="numeric" maxLength={10} value={f.phone} err={e.phone} onChange={set('phone')} autoComplete="tel-national" />
        <F label="Password" pw value={f.password} err={e.password} onChange={set('password')} autoComplete="new-password" />
        <Meter p={f.password} />
        <F label="Confirm password" pw value={f.confirm} err={e.confirm} onChange={set('confirm')} autoComplete="new-password" />
        <label className="chk"><input type="checkbox" checked={f.consent} onChange={set('consent')} /> I agree to the Terms and Privacy Policy
          {e.consent && <small className="err">{e.consent}</small>}</label>
        {err && <p className="err" role="alert">{err}</p>}
        <button className="cta" disabled={busy}>{busy ? 'Creating…' : 'Create account'}</button>
      </form>
      <p>Already registered? <Link to="/login">Log in</Link></p>
    </Shell>
  );
}

export function Verify() {
  const { state } = useLocation(), nav = useNavigate(), email = state?.email, { busy, err, run } = useRun();
  const [otp, setOtp] = useState(''), [st, setSt] = useState('pending'), [cd, setCd] = useState(30), [left, setLeft] = useState(5);
  useEffect(() => { if (cd <= 0) return; const t = setTimeout(() => setCd(cd - 1), 1000); return () => clearTimeout(t); }, [cd]);
  if (!email) return <Shell center title="Verification required" sub="Log in or register to get a code."><Link className="cta btn" to="/login">Go to login</Link></Shell>;
  const submit = async ev => {
    ev.preventDefault(); if (!/^\d{6}$/.test(otp) || left <= 0) return;
    const e = await run(async () => { await auth.verifyOtp(email, otp); setSt('verified'); });
    if (e) { setSt(e.code === 'OTP_EXPIRED' ? 'expired' : 'failed'); if (e.code !== 'OTP_EXPIRED') setLeft(l => l - 1); }
  };
  const resend = async () => { const e = await run(() => auth.resendOtp(email)); if (!e) { setCd(30); setLeft(5); setSt('pending'); setOtp(''); } };
  const cls = { pending: 'pend', verified: 'ok', expired: 'ambiguous', failed: 'oos' };
  return (
    <Shell center title="Verify Your Mobile Number" sub={`We've sent a 6 digit OTP to ${state.phone || email}`}>
      {auth.DEMO && <p className="muted"><small>Demo: any 6 digits verify. 000000 = expired, 111111 = wrong code.</small></p>}
      <p>Status: <span className={'chip ' + cls[st]}>{st[0].toUpperCase() + st.slice(1)}</span></p>
      {st === 'verified' ? <><p>Your account is verified.</p><button className="cta" onClick={() => nav('/login')}>Continue to login</button></> : (
        <form onSubmit={submit}>
          <div className="boxes">{[0, 1, 2, 3, 4, 5].map(i => <input key={i} className="box" inputMode="numeric" maxLength={1} aria-label={'Digit ' + (i + 1)} value={(otp[i] || '').trim()} autoComplete={i ? 'off'  : 'one-time-code'}
            onChange={e => { const v = e.target.value.replace(/\D/g, '').slice(-1); const d = Array.from({ length: 6 }, (_, k) => otp[k] || ' '); d[i] = v || ' '; setOtp(d.join('').replace(/ +$/, '')); if (v) e.target.nextSibling?.focus(); }}
            onKeyDown={e => { if (e.key === 'Backspace' && !otp[i]) e.target.previousSibling?.focus(); }} />)}</div>
          {err && <p className="err" role="alert">{err}{st === 'failed' && left > 0 ? ` ${left} attempts left.` : ''}</p>}
          {left <= 0 && <p className="err">Too many attempts. Request a new code.</p>}
          <button className="cta" disabled={busy || left <= 0 || otp.length < 6}>{busy ? 'Checking…' : 'Verify'}</button>
          <p><button type="button" className="link" disabled={cd > 0 || busy} onClick={resend}>{cd > 0 ? `Resend OTP in 00:${String(cd).padStart(2, '0')}` : 'Resend code'}</button></p>
          <p><Link to="/register">Change mobile number</Link></p>
        </form>)}
    </Shell>
  );
}

export function Forgot() {
  const [email, setEmail] = useState(''), [sent, setSent] = useState(false), [e, setE] = useState(''), { busy, err, run } = useRun();
  const submit = async ev => {
    ev.preventDefault(); if (!okEmail(email)) return setE('Enter a valid email address.'); setE('');
    if (!(await run(() => auth.forgotPassword(email)))) setSent(true);
  };
  return (
    <Shell art="forgot" title="Reset Your Password" sub="Enter your email and we'll send you a reset link.">
      {sent ? <><p>If an account exists for {email}, a reset link is on its way.</p>
        {auth.DEMO && <Link to="/reset-password?token=demo">Demo: open the reset page</Link>}</> : (
        <form onSubmit={submit} noValidate>
          <F label="Email" type="email" value={email} err={e} onChange={ev => setEmail(ev.target.value)} />
          {err && <p className="err" role="alert">{err}</p>}
          <button className="cta" disabled={busy}>{busy ? 'Sending…' : 'Send reset link'}</button>
        </form>)}
      <p><Link to="/login">Back to login</Link></p>
    </Shell>
  );
}

export function Reset() {
  const [q] = useSearchParams(), token = q.get('token'), nav = useNavigate(), { busy, err, run } = useRun();
  const [p, setP] = useState(''), [c, setC] = useState(''), [e, setE] = useState('');
  if (!token) return <Shell center title="Link not valid" sub="This reset link is missing or expired."><Link className="cta btn" to="/forgot-password">Request a new link</Link></Shell>;
  const submit = async ev => {
    ev.preventDefault();
    if (strength(p) < 4) return setE('Use 8+ characters with upper case, lower case and a number.');
    if (p !== c) return setE('Passwords do not match.'); setE('');
    if (!(await run(() => auth.resetPassword(token, p)))) nav('/login');
  };
  return (
    <Shell art="forgot" title="Set a new password">
      <form onSubmit={submit} noValidate>
        <F label="New password" pw value={p} onChange={ev => setP(ev.target.value)} autoComplete="new-password" />
        <Meter p={p} />
        <F label="Confirm new password" pw value={c} onChange={ev => setC(ev.target.value)} autoComplete="new-password" />
        {(e || err) && <p className="err" role="alert">{e || err}</p>}
        <button className="cta" disabled={busy}>{busy ? 'Saving…' : 'Reset password'}</button>
      </form>
    </Shell>
  );
}
