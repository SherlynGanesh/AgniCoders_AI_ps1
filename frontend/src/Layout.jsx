import { useState } from 'react';
import { NavLink, Outlet } from 'react-router-dom';
import { useAuth } from './AuthContext';
import * as auth from './authService';

const NAV = [['/dashboard', 'dashboard', '🏠'], ['/voice', 'neworder', '🎙'], ['/orders', 'orders', '🧾'], ['/catalog', 'catalog', '📦'],
  ['/customers', 'customers', '👥'], ['/insights', 'insights', '📈'], ['/settings', 'settings', '⚙️']];

export default function Layout() {
  const { user, logout, t } = useAuth(), [menu, setMenu] = useState(false), [ask, setAsk] = useState(false);
  return (
    <div className="app">
      <aside className="side-nav">
        <strong className="brand">🏪 DukaanMitra</strong>
        <nav>{NAV.map(([to, l, i]) => <NavLink key={to} to={to}>{i} {t(l)}</NavLink>)}</nav>
        <div className="shopbox"><i>{user.shop[0]}</i><span><b>{user.shop}</b><br />{user.name}</span></div>
      </aside>
      <div>
        <header className="top2">
          <input className="srch" placeholder="Search products, orders…" aria-label="Search" />
          <div className="row">{auth.DEMO && <span className="pill">Demo Mode</span>}
            <div className="prof">
              <button className="avatar" onClick={() => setMenu(!menu)} aria-label="Profile menu">{user.name[0]}</button>
              {menu && <div className="menu card"><b>{user.name}</b><span className="muted">{user.shop}</span>
                <span className={'chip ' + (user.verified ? 'ok' : 'ambiguous')}>{user.verified ? 'Verified' : 'Unverified'}</span>
                <NavLink className="link" to="/settings" onClick={() => setMenu(false)}>{t('settings')}</NavLink><button className="link" onClick={() => { setMenu(false); setAsk(true); }}>{t('logout')}</button></div>}
            </div></div>
        </header>
        <div className="page"><Outlet /></div>
      </div>
      {ask && <div className="modal" role="dialog" aria-modal="true"><div className="card"><h2>Log out?</h2>
        <p className="muted">You'll need to log in again to manage orders.</p>
        <div className="row"><button className="link" onClick={() => setAsk(false)}>Stay logged in</button><button className="cta" onClick={logout}>Log out</button></div></div></div>}
    </div>
  );
}
