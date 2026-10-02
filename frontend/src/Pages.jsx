import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth, useData } from './AuthContext';
import { Pic } from './Pic';
import { LANGS } from './i18n';

const inr = n => '₹' + (+n).toLocaleString('en-IN');
const chip = s => s === 'Confirmed' ? 'ok' : 'ambiguous';
const Page = ({ title, action, children }) => <><div className="ph"><h1>{title}</h1>{action}</div>{children}</>;
const Stat = ({ l, v, s }) => <div className="card stat"><span className="muted">{l}</span><b>{v}</b>{s && <small className="muted">{s}</small>}</div>;
const Table = ({ cols, rows }) => <div className="tw"><table><thead><tr>{cols.map(c => <th key={c} align="left">{c}</th>)}</tr></thead>
  <tbody>{rows.map((r, i) => <tr key={i}>{r.map((c, j) => <td key={j}>{c}</td>)}</tr>)}</tbody></table></div>;

export function Dashboard() {
  const { t } = useAuth(), { orders, catalog } = useData(), done = orders.filter(o => o.status === 'Confirmed'), pend = orders.filter(o => o.status !== 'Confirmed');
  const low = catalog.filter(p => p.stock <= p.min), QA = [['🎙', 'Take a voice order', '/voice'], ['📦', 'Add a product', '/catalog'], ['🗃', 'Update stock', '/catalog'], ['🧾', 'Order history', '/orders']];
  return (
    <>
      <div className="greet card"><div><h1>{t('namaste')}</h1><p className="muted">{t('ready')}</p>
        <div className="row l"><Link className="cta btn" to="/voice">🎙 {t('speak')}</Link><Link className="btn ghost" to="/voice">{t('manual')}</Link></div></div><div className="big" aria-hidden>🌿</div></div>
      <div className="stats"><Stat l="Today's Orders" v={orders.length} s="+3 vs yesterday" /><Stat l="Completed Orders" v={done.length} s="Delivered or confirmed" />
        <Stat l="Pending Clarifications" v={pend.length} s="Needs your attention" /><Stat l="Today's Sales" v={inr(orders.reduce((a, o) => a + o.total, 0))} s="Across all orders" /></div>
      <div className="two">
        <section className="card"><div className="li"><h3>Recent Orders</h3><Link to="/orders">View All</Link></div>
          <Table cols={['Order ID', 'When', 'Items', 'Total', 'Status', 'Action']} rows={orders.slice(0, 5).map(o => [o.id, o.date, o.items, inr(o.total),
            <span className={'chip ' + chip(o.status)}>{o.status}</span>, <Link to="/orders">View</Link>])} /></section>
        <section className="card"><h3>Quick Actions</h3>{QA.map(([i, t, to]) => <Link className="li qa" key={t} to={to}><span>{i} {t}</span><span>›</span></Link>)}
          <h3 style={{ marginTop: 16 }}>Recent Activity</h3>
          {orders.slice(0, 2).map(o => <p className="li" key={o.id}>Order {o.id} {o.status.toLowerCase()}</p>)}
          {low[0] && <p className="li">Stock low: {low[0].name}</p>}</section>
      </div>
    </>
  );
}

export function Orders() {
  const { orders } = useData(), [q, setQ] = useState(''), [s, setS] = useState('');
  const rows = orders.filter(o => (o.customer + o.id).toLowerCase().includes(q.toLowerCase()) && (!s || o.status === s));
  return (
    <Page title="Order history">
      <div className="toolbar"><input placeholder="Search customer or order" value={q} onChange={e => setQ(e.target.value)} />
        <div className="tabs">{['', 'New', 'Awaiting reply', 'Confirmed'].map(t => <button key={t} className={s === t ? 'on' : ''} onClick={() => setS(t)}>{t || 'All'}</button>)}</div></div>
      <div className="card"><Table cols={['Order', 'Customer', 'Date', 'Items', 'Status', 'Total', 'Bill']}
        rows={rows.map(o => [o.id, o.customer, o.date, o.items, <span className={'chip ' + chip(o.status)}>{o.status}</span>, inr(o.total), o.bill ? <Link to={'/bill/' + encodeURIComponent(o.id)}>View bill</Link> : ''])} />
        {!rows.length && <p className="muted">No orders match your search.</p>}</div>
    </Page>
  );
}

export function Catalog() {
  const { catalog, setCatalog } = useData(), [q, setQ] = useState(''), blank = { name: '', unit: 'kg', price: '', stock: '', img: '' }, [n, setN] = useState(blank);
  const add = e => { e.preventDefault(); if (!n.name || !n.price) return;
    setCatalog([...catalog, { id: Date.now(), img: n.img, name: n.name, unit: n.unit, price: +n.price, stock: +n.stock || 0, min: 5, sold: 0 }]); setN(blank); };
  const setStock = (id, v) => setCatalog(catalog.map(p => p.id === id ? { ...p, stock: Math.max(0, parseInt(v.replace(/\D/g, '')) || 0) } : p));
  const adj = (id, d) => setCatalog(catalog.map(p => p.id === id ? { ...p, stock: Math.max(0, p.stock + d) } : p));
  return (
    <Page title="Catalog & Stock">
      <form className="toolbar card" onSubmit={add}>
        <input placeholder="Product name" value={n.name} onChange={e => setN({ ...n, name: e.target.value })} />
        <select value={n.unit} onChange={e => setN({ ...n, unit: e.target.value })}><option>kg</option><option>pc</option><option>L</option></select>
        <input placeholder="Price ₹" inputMode="numeric" value={n.price} onChange={e => setN({ ...n, price: e.target.value })} />
        <input placeholder="Stock" inputMode="numeric" value={n.stock} onChange={e => setN({ ...n, stock: e.target.value })} />
        <label className="upl">📷 {n.img ? 'Photo added' : 'Add photo'}<input type="file" accept="image/*" hidden onChange={e => { const f = e.target.files[0]; if (!f) return; const r = new FileReader(); r.onload = () => setN(x => ({ ...x, img: r.result })); r.readAsDataURL(f); }} /></label>
        <button className="cta">Add product</button></form>
      <div className="toolbar"><input placeholder="Search products" value={q} onChange={e => setQ(e.target.value)} /></div>
      <div className="stats"><Stat l="Total products" v={catalog.length} /><Stat l="Low stock" v={catalog.filter(p => p.stock > 0 && p.stock <= p.min).length} /><Stat l="Out of stock" v={catalog.filter(p => !p.stock).length} /></div>
      <div className="card"><Table cols={['Picture', 'Product', 'Unit', 'Price', 'Status', 'Update stock', '']}
        rows={catalog.filter(p => p.name.toLowerCase().includes(q.toLowerCase())).map(p => [<Pic p={p} size="sm" />, p.name, p.unit, inr(p.price),
          <span className={'chip ' + (p.stock === 0 ? 'oos' : p.stock <= p.min ? 'ambiguous' : 'ok')}>{p.stock === 0 ? 'Out of stock' : p.stock <= p.min ? 'Low' : 'In stock'}</span>,
          <span className="row l" style={{ margin: 0 }}><button className="btn-sm" onClick={() => adj(p.id, -1)} aria-label={'Decrease ' + p.name}>−</button>
            <input className="qty" inputMode="numeric" value={p.stock} aria-label={'Stock of ' + p.name} onChange={e => setStock(p.id, e.target.value)} />
            <button className="btn-sm" onClick={() => adj(p.id, 1)} aria-label={'Increase ' + p.name}>+</button> <span className="muted">{p.unit}</span></span>,
          <button className="link" onClick={() => setCatalog(catalog.filter(x => x.id !== p.id))}>Remove</button>])} /></div>
    </Page>
  );
}

export function Customers() {
  const { customers } = useData();
  return <Page title="Customers"><div className="card"><Table cols={['Name', 'Phone', 'Orders', 'Usually buys', 'Total spent']}
    rows={customers.map(c => [c.name, c.phone, c.orders, c.usual, inr(c.spent)])} /></div></Page>;
}

export function Insights() {
  const { orders, catalog } = useData(), top = [...catalog].sort((a, b) => b.sold - a.sold).slice(0, 6), max = top[0].sold;
  const wait = orders.filter(o => o.status !== 'Confirmed').length;
  return (
    <Page title="Insights">
      <div className="stats"><Stat l="Average order value" v={inr(orders.reduce((s, o) => s + o.total, 0) / orders.length)} />
        <Stat l="Orders needing clarification" v={Math.round(wait / orders.length * 100) + '%'} /><Stat l="Out-of-stock items" v={catalog.filter(p => !p.stock).length} /></div>
      <section className="card"><h3>Top selling products</h3>{top.map(p => <div className="li" key={p.id}>
        <span style={{ width: 150 }}>{p.name}</span><div className="bar" style={{ flex: 1 }}><b style={{ width: p.sold / max * 100 + '%' }} /></div><span>{p.sold}</span></div>)}</section>
    </Page>
  );
}

export function Settings() {
  const { user, updateUser, lang, setLang, t } = useAuth(), [f, setF] = useState({ name: user.name, shop: user.shop, email: user.email || '', phone: user.phone || '', address: user.address || '' }), [ok, setOk] = useState(false);
  const save = e => { e.preventDefault(); updateUser(f); setOk(true); setTimeout(() => setOk(false), 2000); };
  return (
    <Page title={t('settings')}>
      <section className="card"><h3>{t('language')}</h3><p className="muted">{t('langsub')}</p>
        <div className="tabs">{Object.entries(LANGS).map(([k, v]) => <button key={k} className={lang === k ? 'on' : ''} onClick={() => setLang(k)}>{v}</button>)}</div></section>
      <form className="card sform" onSubmit={save}><h3>{t('profile')}</h3>
        {[['name', 'name'], ['shop', 'shop'], ['email', 'email'], ['phone', 'phone'], ['address', 'address']].map(([k, l]) =>
          <label key={k}>{t(l)}<input value={f[k]} onChange={e => setF({ ...f, [k]: e.target.value })} /></label>)}
        <div className="row l"><button className="cta">{t('save')}</button>{ok && <span className="chip ok">{t('saved')}</span>}</div></form>
    </Page>
  );
}
