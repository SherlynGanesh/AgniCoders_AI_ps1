import { useState } from 'react';
import { Navigate, useLocation, useNavigate, useParams, Link } from 'react-router-dom';
import * as api from './api';
import { useAuth, useData } from './AuthContext';

const inr = n => '₹' + (+n).toLocaleString('en-IN');
const PAY = ['Cash', 'UPI', 'Pay later'];

// Step 2: review the order, add customer + payment, confirm.
export function Confirm() {
  const { state } = useLocation(), go = useNavigate(), { addOrder } = useData();
  const [name, setName] = useState(''), [pay, setPay] = useState('Cash'), [busy, setBusy] = useState(false), [err, setErr] = useState('');
  if (!state?.order) return <Navigate to="/voice" replace />;
  const { order, msg } = state, total = order.items.reduce((s, i) => s + i.qty * i.price, 0);
  const confirm = async () => {
    setBusy(true); setErr('');
    try {
      const b = await api.confirmOrder(order.id, order.items, msg), id = '#DM-' + (1000 + Math.floor(Math.random() * 9000));
      addOrder({ id, customer: name.trim() || 'Walk-in', items: order.items.length, total: b.bill.total, status: 'Confirmed', date: 'Today', pay, bill: b.bill, note: b.deliveryNote });
      go('/bill/' + encodeURIComponent(id), { replace: true });
    } catch (e) { setErr(e.message); setBusy(false); }
  };
  return (
    <>
      <div className="ph"><h1>Confirm order</h1></div>
      <div className="bgrid">
        <section className="card"><h3>Order summary</h3>
          <table><thead><tr><th align="left">Item</th><th align="left">Qty</th><th align="right">Amount</th></tr></thead>
            <tbody>{order.items.map((i, k) => <tr key={k}><td>{i.name}</td><td>{i.qty} {i.unit}</td><td>{inr(i.qty * i.price)}</td></tr>)}
              <tr className="tot"><td colSpan="2">Total</td><td>{inr(total)}</td></tr></tbody></table>
          <p className="muted">Original: {msg}</p></section>
        <section className="card"><h3>Customer &amp; payment</h3>
          <label>Customer name (optional)<input value={name} onChange={e => setName(e.target.value)} placeholder="e.g. Sharma ji" /></label>
          <p className="muted">Payment</p><div className="tabs">{PAY.map(p => <button key={p} className={pay === p ? 'on' : ''} onClick={() => setPay(p)}>{p}</button>)}</div>
          {err && <p className="err" role="alert">{err}</p>}
          <button className="cta" onClick={confirm} disabled={busy}>{busy ? 'Confirming…' : 'Confirm & generate bill'}</button>
          <Link className="btn ghost" to="/voice">Back to edit</Link></section>
      </div>
    </>
  );
}

// Step 3: the generated bill.
export function Bill() {
  const { id } = useParams(), { orders } = useData(), { user } = useAuth(), o = orders.find(x => x.id === id);
  if (!o?.bill) return <Navigate to="/orders" replace />;
  return (
    <div className="bgrid">
      <section className="card center no-print"><div className="tick big">✓</div><h2>Order Confirmed!</h2>
        <p className="muted">Order {o.id} has been saved and the bill is ready.</p>
        <button className="cta" onClick={() => window.print()}>Print Bill</button>
        <button className="btn ghost" onClick={() => window.print()}>Download PDF</button>
        <Link className="link" to="/voice">Create Another Order</Link></section>
      <section className="card bill"><div className="li"><b>🏪 {user.shop}</b><span className="muted">Tax Invoice / Bill</span></div>
        <p className="muted">Order No: {o.id} · {o.date} · Customer: {o.customer}</p>
        <table><thead><tr><th align="left">Item</th><th align="left">Qty</th><th align="right">Amount</th></tr></thead>
          <tbody>{o.bill.lines.map((l, i) => <tr key={i}><td>{l.name}</td><td>{l.qty} {l.unit}</td><td>{inr(l.total)}</td></tr>)}
            <tr className="tot"><td colSpan="2">Total</td><td>{inr(o.bill.total)}</td></tr></tbody></table>
        <p className="li"><span><b>Delivery note:</b> {o.note}</span><span className={'chip ' + (o.pay === 'Pay later' ? 'ambiguous' : 'ok')}>{o.pay === 'Pay later' ? 'Payment pending' : 'Paid · ' + o.pay}</span></p></section>
    </div>
  );
}
