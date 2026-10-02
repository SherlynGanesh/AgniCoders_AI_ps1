import { createContext, useContext, useEffect, useState } from 'react';
import * as auth from './authService';
import * as seed from './data';
import { tr } from './i18n';

const A = createContext(), D = createContext();
export const useAuth = () => useContext(A);
export const useData = () => useContext(D);

export function Providers({ children }) {
  const [user, setUser] = useState(null), [ready, setReady] = useState(false), [expired, setExpired] = useState(false);
  const [orders, setOrders] = useState(seed.orders), [catalog, setCatalog] = useState(seed.catalog);
  const [lang, setLangS] = useState(() => localStorage.getItem('lang') || 'en');
  const setLang = l => { localStorage.setItem('lang', l); setLangS(l); };
  const t = k => tr(lang, k), updateUser = u => setUser(x => ({ ...x, ...u }));
  const [customers] = useState(seed.customers);
  useEffect(() => {
    // Fetch live catalog and stock directly from PostgreSQL backend
    fetch('http://localhost:8000/api/catalog')
      .then(r => (r.ok ? r.json() : null))
      .then(data => {
        if (data && data.length) setCatalog(data);
      })
      .catch(() => {});

    auth.refreshSession().then(d => d && auth.getCurrentUser().then(setUser)).catch(() => {}).finally(() => setReady(true));
    const f = () => { setUser(null); setExpired(true); };
    window.addEventListener('auth:expired', f); return () => window.removeEventListener('auth:expired', f);
  }, []);
  const logout = async () => { await auth.logout(); setUser(null); setExpired(false); };
  const login = u => { setExpired(false); setUser(u); };
  return (
    <A.Provider value={{ user, ready, expired, login, logout, lang, setLang, t, updateUser }}>
      <D.Provider value={{ orders, addOrder: o => setOrders([o, ...orders]), catalog, setCatalog, customers }}>
        {children}
      </D.Provider>
    </A.Provider>
  );
}
