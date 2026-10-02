// Tokens live in memory only. Refresh token = HttpOnly cookie set by the backend.
// Expected: POST /auth/login {email,password} -> {accessToken,user:{name,shop,verified}}
//           POST /auth/refresh -> {accessToken} | POST /auth/logout | GET /auth/me
const BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';
export const DEMO = false;
let token = null;
export class ApiError extends Error { constructor(s, m, c) { super(m); this.status = s; this.code = c; } }

export async function req(path, opts = {}, retry = true) {
  const r = await fetch(BASE + path, { ...opts, credentials: 'include',
    headers: { 'Content-Type': 'application/json', ...(token && { Authorization: `Bearer ${token}` }) } });
  if (r.status === 401 && retry && path !== '/auth/refresh') {
    if (await refreshSession()) return req(path, opts, false);
    token = null; window.dispatchEvent(new Event('auth:expired'));
  }
  const d = await r.json().catch(() => ({}));
  if (!r.ok) throw new ApiError(r.status, d.message || 'Something went wrong. Try again.', d.code);
  return d;
}
export async function login(email, password) {
  if (DEMO) {
    if (/^unverified/i.test(email)) throw new ApiError(403, 'Verify your account to continue.', 'UNVERIFIED');
    if (/^disabled/i.test(email)) throw new ApiError(403, 'This account is disabled. Contact support.', 'DISABLED');
    if (password === 'wrong') throw new ApiError(401, 'Incorrect email or password.');
    return { user: { name: 'Ramesh Gupta', shop: 'Gupta Kirana Store', email, verified: true } };
  }
  const d = await req('/auth/login', { method: 'POST', body: JSON.stringify({ email, password }) });
  token = d.accessToken; return d;
}
export async function refreshSession() {
  if (DEMO) return null;
  try { const d = await req('/auth/refresh', { method: 'POST' }, false); token = d.accessToken; return d; } catch { return null; }
}
export const getCurrentUser = () => (DEMO ? null : req('/auth/me'));
export async function logout() { if (!DEMO) await req('/auth/logout', { method: 'POST' }).catch(() => {}); token = null; }

// Expected: POST /auth/register, /auth/verify-otp {email,otp}, /auth/resend-otp {email},
// /auth/forgot-password {email}, /auth/reset-password {token,password}.
// Error codes: DUPLICATE, UNVERIFIED, DISABLED, OTP_EXPIRED, OTP_INVALID (429 = too many attempts).
const post = (p, b) => req(p, { method: 'POST', body: JSON.stringify(b) });
const demo = v => new Promise(r => setTimeout(() => r(v), 400));
export async function register(f) {
  if (DEMO) { if (/exists/i.test(f.email)) throw new ApiError(409, 'An account with this email already exists.', 'DUPLICATE'); return demo({ pending: true }); }
  return post('/auth/register', f);
}
export async function verifyOtp(email, otp) {
  if (DEMO) {
    if (otp === '000000') throw new ApiError(400, 'This code has expired. Request a new one.', 'OTP_EXPIRED');
    if (otp === '111111') throw new ApiError(400, 'Incorrect code.', 'OTP_INVALID');
    return demo({ verified: true });
  }
  return post('/auth/verify-otp', { email, otp });
}
export const resendOtp = email => (DEMO ? demo({}) : post('/auth/resend-otp', { email }));
export const forgotPassword = email => (DEMO ? demo({}) : post('/auth/forgot-password', { email }));
export const resetPassword = (token, password) => (DEMO ? demo({}) : post('/auth/reset-password', { token, password }));
