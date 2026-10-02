import { createContext, useContext, useEffect, useState } from 'react';
import * as auth from './authService';
import { tr } from './i18n';

const A = createContext(), D = createContext();
export const useAuth = () => useContext(A);
export const useData = () => useContext(D);

const API_BASE = 'http://localhost:8000/api';

export function Providers({ children }) {
  const [user, setUser] = useState(null), [ready, setReady] = useState(false), [expired, setExpired] = useState(false);
  const [orders, setOrders] = useState([]), [catalog, setCatalog] = useState([]);
  const [customers, setCustomers] = useState([]), [categories, setCategories] = useState([]);
  const [lang, setLangS] = useState(() => localStorage.getItem('lang') || 'en');
  const setLang = l => { localStorage.setItem('lang', l); setLangS(l); };
  const t = k => tr(lang, k), updateUser = u => setUser(x => ({ ...x, ...u }));

  const loadData = () => {
    // 1. Live PostgreSQL Catalog
    fetch(`${API_BASE}/catalog?limit=250`)
      .then(r => (r.ok ? r.json() : []))
      .then(data => { if (Array.isArray(data) && data.length) setCatalog(data); })
      .catch(() => {});

    // 2. Live PostgreSQL Orders
    fetch(`${API_BASE}/orders-real?limit=100`)
      .then(r => (r.ok ? r.json() : []))
      .then(data => { if (Array.isArray(data) && data.length) setOrders(data); })
      .catch(() => {});

    // 3. Live PostgreSQL Customers
    fetch(`${API_BASE}/customers-real?limit=60`)
      .then(r => (r.ok ? r.json() : []))
      .then(data => { if (Array.isArray(data) && data.length) setCustomers(data); })
      .catch(() => {});

    // 4. Live PostgreSQL Categories
    fetch(`${API_BASE}/categories`)
      .then(r => (r.ok ? r.json() : []))
      .then(data => { if (Array.isArray(data) && data.length) setCategories(data); })
      .catch(() => {});
  };

  useEffect(() => {
    loadData();
    auth.refreshSession().then(d => d && auth.getCurrentUser().then(setUser)).catch(() => {}).finally(() => setReady(true));
    const f = () => { setUser(null); setExpired(true); };
    window.addEventListener('auth:expired', f); return () => window.removeEventListener('auth:expired', f);
  }, []);

  const logout = async () => { await auth.logout(); setUser(null); setExpired(false); };
  const login = u => { setExpired(false); setUser(u); loadData(); };

  return (
    <A.Provider value={{ user, ready, expired, login, logout, lang, setLang, t, updateUser }}>
      <D.Provider value={{
        orders,
        addOrder: o => setOrders([o, ...orders]),
        catalog,
        setCatalog,
        customers,
        categories,
        refreshData: loadData
      }}>
        {children}
      </D.Provider>
    </A.Provider>
  );
}
