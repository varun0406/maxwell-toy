import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { analyticsApi } from '../../api/endpoints';
import { useAuthStore } from '../../store/auth';
import { formatCurrency, formatDate } from '../../utils/format';
import CalculationEvidence from '../../components/CalculationEvidence';
import {
  Users, ChevronRight, Plus, CreditCard, BarChart2, CalendarClock, ShieldAlert
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
        <div className="hero-amount">
          {isLoading ? '...' : (
            <CalculationEvidence
              title="Total Outstanding"
              valueClass="hero-amount"
              items={[
                { label: 'Total Invoiced', value: summary?.total_invoiced || 0, operator: '+' },
                { label: 'Journal Adjustments', value: summary?.total_journal || 0, operator: summary?.total_journal >= 0 ? '+' : '-' },
                { label: 'Total Collected', value: summary?.total_collected || 0, operator: '-' },
                { label: 'Total Outstanding', value: summary?.total_outstanding || 0, operator: '=' }
              ]}
            >
              {formatCurrency(summary?.total_outstanding || 0)}
            </CalculationEvidence>
          )}
        </div>
        <p className="hero-sub">
          {summary?.overdue_count || 0} overdue · {summary?.invoices_count || 0} total invoices
        </p>
      </div>

      {/* Stats Grid */}
      <div className="stats-grid">
        <div className="stat-card accent">
          <p className="stat-label">Invoiced</p>
          <div className="stat-value mono">
            {isLoading ? '…' : (
              <CalculationEvidence
                title="Total Invoiced"
                valueClass="stat-value mono"
                items={[
                  { label: 'Sum of all unpaid and paid invoices', value: summary?.total_invoiced || 0, operator: '=' }
                ]}
              >
                {formatCurrency(summary?.total_invoiced || 0)}
              </CalculationEvidence>
            )}
          </div>
        </div>
        <div className="stat-card success">
          <p className="stat-label">Collected</p>
          <div className="stat-value mono">
            {isLoading ? '…' : (
              <CalculationEvidence
                title="Total Collected"
                valueClass="stat-value mono"
                items={[
                  { label: 'Sum of all received payments', value: summary?.total_collected || 0, operator: '=' }
                ]}
              >
                {formatCurrency(summary?.total_collected || 0)}
              </CalculationEvidence>
            )}
          </div>
        </div>
        <div className="stat-card warning">
          <p className="stat-label">Parties</p>
          <p className="stat-value">{summary?.total_parties || 0}</p>
        </div>
        <div className="stat-card danger">
          <p className="stat-label">Overdue</p>
          <div className="stat-value">
            {isLoading ? '…' : (
              <CalculationEvidence
                title="Overdue Invoices"
                valueClass="stat-value"
                items={[
                  { label: 'Invoices past due date', value: summary?.overdue_count || 0, operator: '=' }
                ]}
              >
                {summary?.overdue_count || 0}
              </CalculationEvidence>
            )}
          </div>
        </div>
      </div>

      {/* Quick Actions */}
      <p className="section-label">Quick Actions</p>
      <div className="quick-actions" style={{ marginBottom: 12 }}>
        <button className="quick-action-btn accent" onClick={() => navigate('/invoices/new')}>
          <Plus size={20} />
          New Invoice
        </button>
        <button className="quick-action-btn success" onClick={() => navigate('/payments/new')}>
          <CreditCard size={20} />
          Record Payment
        </button>
        <button className="quick-action-btn danger" onClick={() => navigate('/pending-dues')}>
          <CalendarClock size={20} />
          Pending Dues
        </button>
        <button className="quick-action-btn warning" onClick={() => navigate('/analytics')}>
          <BarChart2 size={20} />
          Analytics
        </button>
        {user?.is_superuser && (
          <button className="quick-action-btn" style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)' }} onClick={() => navigate('/users')}>
            <ShieldAlert size={20} />
            Manage Users
          </button>
        )}
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
          <button className="btn btn-primary" onClick={() => navigate('/parties', { state: { showAdd: true } })} style={{ marginTop: 8 }}>
            <Plus size={16} /> Add Party
          </button>
        </div>
      )}
    </div>
  );
}
