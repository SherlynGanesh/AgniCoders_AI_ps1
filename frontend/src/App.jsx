import { Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { useAuth } from './AuthContext';
import Layout from './Layout';
import NewOrder from './NewOrder';
import { Confirm, Bill } from './Confirm';
import { Login, Register, Verify, Forgot, Reset } from './Auth';
import * as P from './Pages';

function Guard() {
  const { user, ready, logout } = useAuth(), loc = useLocation();
  if (!ready) return <p className="muted center">Checking your session…</p>;
  if (!user) return <Navigate to="/login" replace state={{ from: loc.pathname }} />;
  if (user.disabled) return <p className="err center">This account is disabled. Contact support. <button className="link" onClick={logout}>Log out</button></p>;
  if (!user.verified) return <Navigate to="/verify" replace state={{ email: user.email }} />;
  return <Layout />;
}
export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/dashboard" replace />} />
      <Route path="/login" element={<Login />} /><Route path="/register" element={<Register />} />
      <Route path="/verify" element={<Verify />} /><Route path="/forgot-password" element={<Forgot />} />
      <Route path="/reset-password" element={<Reset />} />
      <Route element={<Guard />}>
        <Route path="voice" element={<NewOrder />} /><Route path="confirm" element={<Confirm />} /><Route path="bill/:id" element={<Bill />} /><Route path="settings" element={<P.Settings />} />
        <Route path="dashboard" element={<P.Dashboard />} />
        <Route path="orders" element={<P.Orders />} /><Route path="catalog" element={<P.Catalog />} />
        <Route path="customers" element={<P.Customers />} />
        <Route path="insights" element={<P.Insights />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
