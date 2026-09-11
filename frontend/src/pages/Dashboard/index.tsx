import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { analyticsApi } from '../../api/endpoints';
import { useAuthStore } from '../../store/auth';
import { formatCurrency, formatDate } from '../../utils/format';
import {
  Users, ChevronRight, Plus, CreditCard, BarChart2
} from 'lucide-react';

export default function Dashboard() {
  const navigate = useNavigate();
  const user = useAuthStore((s) => s.user);

  const { data: summary, isLoading } = useQuery({
    queryKey: ['dashboard'],
    queryFn: () => analyticsApi.summary().then((r) => r.data),
    refetchInterval: 60_000,
  });

  const greeting = () => {
    const h = new Date().getHours();
    if (h < 12) return 'Good morning';
    if (h < 17) return 'Good afternoon';
    return 'Good evening';
  };

  return (
    <div className="page-content">
      {/* Greeting */}
      <div style={{ padding: '20px 20px 0', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <p style={{ fontSize: 13, color: 'var(--text-muted)' }}>{greeting()},</p>
          <h1 className="page-title">{user?.username || 'User'} 👋</h1>
        </div>
        <div style={{ width: 44, height: 44, borderRadius: 12, overflow: 'hidden', border: '2px solid var(--border)', background: 'var(--bg-elevated)' }}>
          <img src="/logo.png" alt="Logo" style={{ width: '100%', height: '100%', objectFit: 'contain' }} />
        </div>
      </div>

      {/* Outstanding Hero */}
      <div className="hero-card">
        <p className="hero-label">Total Outstanding</p>
        <p className="hero-amount">
          {isLoading ? '...' : formatCurrency(summary?.total_outstanding || 0)}
        </p>
        <p className="hero-sub">
          {summary?.overdue_count || 0} overdue · {summary?.invoices_count || 0} total invoices
        </p>
      </div>

      {/* Stats Grid */}
      <div className="stats-grid">
        <div className="stat-card accent">
          <p className="stat-label">Invoiced</p>
          <p className="stat-value mono">{isLoading ? '…' : formatCurrency(summary?.total_invoiced || 0)}</p>
        </div>
        <div className="stat-card success">
          <p className="stat-label">Collected</p>
          <p className="stat-value mono">{isLoading ? '…' : formatCurrency(summary?.total_collected || 0)}</p>
        </div>
        <div className="stat-card warning">
          <p className="stat-label">Parties</p>
          <p className="stat-value">{summary?.total_parties || 0}</p>
        </div>
        <div className="stat-card danger">
          <p className="stat-label">Overdue</p>
          <p className="stat-value">{summary?.overdue_count || 0}</p>
        </div>
      </div>

      {/* Quick Actions */}
      <p className="section-label">Quick Actions</p>
      <div className="quick-actions">
        <button className="quick-action-btn accent" onClick={() => navigate('/invoices/new')}>
          <Plus size={20} />
          New Invoice
        </button>
        <button className="quick-action-btn success" onClick={() => navigate('/payments/new')}>
          <CreditCard size={20} />
          Record Payment
        </button>
        <button className="quick-action-btn warning" onClick={() => navigate('/analytics')}>
          <BarChart2 size={20} />
          Analytics
        </button>
      </div>

      {/* Recent Payments */}
      {summary?.recent_payments?.length > 0 && (
        <>
          <p className="section-label">Recent Payments</p>
          <div className="list-container">
            {summary.recent_payments.map((p: any) => (
              <div key={p.id} className="list-item" onClick={() => navigate(`/payments/${p.id}`)}>
                <div className="list-item-icon" style={{ background: 'var(--success-bg)' }}>
                  💰
                </div>
                <div className="list-item-body">
                  <p className="list-item-title">Payment #{p.id}</p>
                  <p className="list-item-sub">{formatDate(p.payment_date)} · {p.mode || 'cash'}</p>
                </div>
                <div className="list-item-right">
                  <p style={{ color: 'var(--success)', fontWeight: 700, fontSize: 15 }}>
                    {formatCurrency(p.amount)}
                  </p>
                  <ChevronRight size={14} style={{ color: 'var(--text-muted)' }} />
                </div>
              </div>
            ))}
          </div>
        </>
      )}

      {!isLoading && !summary?.total_parties && (
        <div className="empty-state">
          <Users size={52} style={{ color: 'var(--text-muted)' }} />
          <h3>No parties yet</h3>
          <p>Add your first customer or supplier to get started</p>
          <button className="btn btn-primary" onClick={() => navigate('/parties/new')} style={{ marginTop: 8 }}>
            <Plus size={16} /> Add Party
          </button>
        </div>
      )}
    </div>
  );
}
