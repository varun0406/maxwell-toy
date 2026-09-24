import { Navigate, Outlet } from 'react-router-dom';
import { useAuthStore, getUnlocked } from '../store/auth';
import BottomNav from './BottomNav';

export function ProtectedLayout() {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated());

  // Must have gone through calculator AND be logged in
  if (!getUnlocked()) return <Navigate to="/" replace />;
  if (!isAuthenticated) return <Navigate to="/login" replace />;

  return (
    <div className="app-shell">
      <BottomNav />
      <div className="app-main-content" style={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
        <Outlet />
      </div>
    </div>
  );
}
