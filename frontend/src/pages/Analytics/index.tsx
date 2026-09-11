import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { analyticsApi, invoicesApi, paymentsApi, partiesApi } from '../../api/endpoints';
import { formatCurrency, formatDate } from '../../utils/format';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, PieChart, Pie, Cell, Legend
} from 'recharts';

const COLORS = ['#6c63ff', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4'];

export default function Analytics() {
  const [tab, setTab] = useState<'overview' | 'sales' | 'collections' | 'ar'>('overview');
  const { data: summary } = useQuery({
    queryKey: ['dashboard'],
    queryFn: () => analyticsApi.summary().then((r) => r.data),
  });
  const { data: parties = [] } = useQuery({
    queryKey: ['analytics-parties'],
    queryFn: () => analyticsApi.parties().then((r) => r.data),
  });
  const { data: aging = [] } = useQuery({
    queryKey: ['aging'],
    queryFn: () => analyticsApi.aging().then((r) => r.data),
    enabled: tab === 'overview',
  });

  const { data: invoices = [] } = useQuery({
    queryKey: ['reports-invoices'],
    queryFn: () => invoicesApi.list().then(r => r.data),
    enabled: tab === 'sales',
  });

  const { data: payments = [] } = useQuery({
    queryKey: ['reports-payments'],
    queryFn: () => paymentsApi.list().then(r => r.data),
    enabled: tab === 'collections',
  });

  const { data: partyList = [] } = useQuery({
    queryKey: ['reports-parties'],
    queryFn: () => partiesApi.list().then(r => r.data),
  });

  const getPartyName = (id: number) => partyList.find((p: any) => p.id === id)?.name || `Party #${id}`;

  const top5 = parties.slice(0, 5);

  const barData = top5.map((p: any) => ({
    name: p.party_name.length > 10 ? p.party_name.slice(0, 10) + '…' : p.party_name,
    Invoiced: Number(p.total_invoiced),
    Collected: Number(p.total_paid),
    Outstanding: Number(p.outstanding),
  }));

  const pieData = top5.map((p: any) => ({
    name: p.party_name,
    value: Number(p.outstanding),
  })).filter((d: any) => d.value > 0);

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload?.length) {
      return (
        <div style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)', borderRadius: 8, padding: '8px 12px' }}>
          <p style={{ fontSize: 12, fontWeight: 700, marginBottom: 4 }}>{label}</p>
          {payload.map((p: any) => (
            <p key={p.name} style={{ fontSize: 12, color: p.color }}>{p.name}: {formatCurrency(p.value)}</p>
          ))}
        </div>
      );
    }
    return null;
  };

  return (
    <div className="page-content">
      <div className="page-header">
        <h1 className="page-title">Reports Hub</h1>
        <p className="page-subtitle">Business & Accounting Reports</p>
      </div>

      <div className="chips" style={{ marginBottom: 16 }}>
        <button className={`chip ${tab === 'overview' ? 'active' : ''}`} onClick={() => setTab('overview')}>Overview</button>
        <button className={`chip ${tab === 'sales' ? 'active' : ''}`} onClick={() => setTab('sales')}>Sales Book</button>
        <button className={`chip ${tab === 'collections' ? 'active' : ''}`} onClick={() => setTab('collections')}>Collections</button>
        <button className={`chip ${tab === 'ar' ? 'active' : ''}`} onClick={() => setTab('ar')}>A/R</button>
      </div>

      {tab === 'overview' && (
        <>
          {/* Summary Row */}
      <div className="stats-grid">
        <div className="stat-card accent">
          <p className="stat-label">Total Invoiced</p>
          <p className="stat-value mono" style={{ fontSize: 16 }}>{formatCurrency(summary?.total_invoiced || 0)}</p>
        </div>
        <div className="stat-card success">
          <p className="stat-label">Collected</p>
          <p className="stat-value mono" style={{ fontSize: 16 }}>{formatCurrency(summary?.total_collected || 0)}</p>
        </div>
        <div className="stat-card warning">
          <p className="stat-label">Outstanding</p>
          <p className="stat-value mono" style={{ fontSize: 16 }}>{formatCurrency(summary?.total_outstanding || 0)}</p>
        </div>
        <div className="stat-card danger">
          <p className="stat-label">Overdue</p>
          <p className="stat-value">{summary?.overdue_count || 0} bills</p>
        </div>
      </div>

      {/* Bar Chart */}
      {barData.length > 0 && (
        <>
          <p className="section-label">Top Parties — Invoice vs Collected</p>
          <div style={{ padding: '0 20px' }}>
            <div style={{ background: 'var(--bg-card)', borderRadius: 'var(--radius-lg)', border: '1px solid var(--border)', padding: '16px 4px 8px' }}>
              <ResponsiveContainer width="100%" height={200}>
                <BarChart data={barData} margin={{ left: -16 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
                  <XAxis dataKey="name" tick={{ fill: '#94a3b8', fontSize: 10 }} axisLine={false} tickLine={false} />
                  <YAxis tick={{ fill: '#94a3b8', fontSize: 10 }} axisLine={false} tickLine={false}
                    tickFormatter={(v) => v >= 1000 ? `${(v/1000).toFixed(0)}k` : v} />
                  <Tooltip content={<CustomTooltip />} />
                  <Bar dataKey="Invoiced" fill="#6c63ff" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="Collected" fill="#10b981" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </>
      )}

      {/* Pie Chart — Outstanding Share */}
      {pieData.length > 0 && (
        <>
          <p className="section-label">Outstanding by Party</p>
          <div style={{ padding: '0 20px' }}>
            <div style={{ background: 'var(--bg-card)', borderRadius: 'var(--radius-lg)', border: '1px solid var(--border)', padding: '16px 4px 8px' }}>
              <ResponsiveContainer width="100%" height={220}>
                <PieChart>
                  <Pie data={pieData} cx="50%" cy="50%" outerRadius={80} dataKey="value" label={({ percent }) => `${(percent * 100).toFixed(0)}%`} labelLine={false}>
                    {pieData.map((_: any, i: number) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                  </Pie>
                  <Legend formatter={(value) => <span style={{ fontSize: 11, color: 'var(--text-secondary)' }}>{value}</span>} />
                  <Tooltip formatter={(value: any) => formatCurrency(value)} contentStyle={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)', borderRadius: 8 }} />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </div>
        </>
      )}

      {/* Aging Report */}
      {aging.length > 0 && (
        <>
          <p className="section-label">Receivable Aging</p>
          <div style={{ padding: '0 20px', marginBottom: 20 }}>
            {aging.map((row: any) => (
              <div key={row.party_id} style={{ background: 'var(--bg-card)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border)', padding: 14, marginBottom: 10 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                  <p style={{ fontWeight: 700, fontSize: 14 }}>{row.party_name}</p>
                  <p style={{ fontWeight: 700, fontSize: 14, color: 'var(--warning)' }}>{formatCurrency(row.total)}</p>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 4, fontSize: 11 }}>
                  {[
                    { label: '0-30d', val: row.current, color: 'var(--success)' },
                    { label: '31-60d', val: row.days_31_60, color: 'var(--warning)' },
                    { label: '61-90d', val: row.days_61_90, color: 'var(--accent)' },
                    { label: '90d+', val: row.over_90, color: 'var(--danger)' },
                  ].map((b) => (
                    <div key={b.label} style={{ textAlign: 'center', background: 'var(--bg-elevated)', borderRadius: 6, padding: '6px 4px' }}>
                      <p style={{ color: 'var(--text-muted)' }}>{b.label}</p>
                      <p style={{ color: b.color, fontWeight: 700, marginTop: 2 }}>{formatCurrency(b.val)}</p>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </>
      )}

      {parties.length === 0 && (
        <div className="empty-state">
          <p>No data yet — create parties and invoices to see analytics</p>
        </div>
      )}
        </>
      )}

      {tab === 'sales' && (
        <div style={{ padding: '0 20px', paddingBottom: 24 }}>
          <div style={{ background: 'var(--bg-card)', borderRadius: 'var(--radius-lg)', border: '1px solid var(--border)', overflow: 'hidden' }}>
            <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <h3 style={{ fontSize: 16, fontWeight: 700 }}>Sales Register</h3>
              <p style={{ fontSize: 14, fontWeight: 700, color: 'var(--accent)' }}>
                Total: {formatCurrency(invoices.reduce((sum: number, i: any) => sum + Number(i.total), 0))}
              </p>
            </div>
            {invoices.length === 0 ? (
              <div className="empty-state"><p>No sales recorded yet</p></div>
            ) : (
              <table style={{ width: '100%', textAlign: 'left', borderCollapse: 'collapse', fontSize: 13 }}>
                <thead>
                  <tr style={{ background: 'var(--bg-elevated)', borderBottom: '1px solid var(--border)' }}>
                    <th style={{ padding: '12px 16px', fontWeight: 600, color: 'var(--text-secondary)' }}>Date</th>
                    <th style={{ padding: '12px 16px', fontWeight: 600, color: 'var(--text-secondary)' }}>Invoice #</th>
                    <th style={{ padding: '12px 16px', fontWeight: 600, color: 'var(--text-secondary)' }}>Party</th>
                    <th style={{ padding: '12px 16px', fontWeight: 600, color: 'var(--text-secondary)', textAlign: 'right' }}>Amount</th>
                  </tr>
                </thead>
                <tbody>
                  {invoices.sort((a: any, b: any) => new Date(b.invoice_date).getTime() - new Date(a.invoice_date).getTime()).map((inv: any) => (
                    <tr key={inv.id} style={{ borderBottom: '1px solid var(--border)' }}>
                      <td style={{ padding: '12px 16px', color: 'var(--text)' }}>{formatDate(inv.invoice_date)}</td>
                      <td style={{ padding: '12px 16px', fontWeight: 500 }}>{inv.invoice_number}</td>
                      <td style={{ padding: '12px 16px' }}>{getPartyName(inv.party_id)}</td>
                      <td style={{ padding: '12px 16px', textAlign: 'right', fontWeight: 600 }}>{formatCurrency(inv.total)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      )}

      {tab === 'collections' && (
        <div style={{ padding: '0 20px', paddingBottom: 24 }}>
          <div style={{ background: 'var(--bg-card)', borderRadius: 'var(--radius-lg)', border: '1px solid var(--border)', overflow: 'hidden' }}>
            <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <h3 style={{ fontSize: 16, fontWeight: 700 }}>Collection Register</h3>
              <p style={{ fontSize: 14, fontWeight: 700, color: 'var(--success)' }}>
                Total: {formatCurrency(payments.reduce((sum: number, p: any) => sum + Number(p.amount), 0))}
              </p>
            </div>
            {payments.length === 0 ? (
              <div className="empty-state"><p>No payments recorded yet</p></div>
            ) : (
              <table style={{ width: '100%', textAlign: 'left', borderCollapse: 'collapse', fontSize: 13 }}>
                <thead>
                  <tr style={{ background: 'var(--bg-elevated)', borderBottom: '1px solid var(--border)' }}>
                    <th style={{ padding: '12px 16px', fontWeight: 600, color: 'var(--text-secondary)' }}>Date</th>
                    <th style={{ padding: '12px 16px', fontWeight: 600, color: 'var(--text-secondary)' }}>Receipt #</th>
                    <th style={{ padding: '12px 16px', fontWeight: 600, color: 'var(--text-secondary)' }}>Party</th>
                    <th style={{ padding: '12px 16px', fontWeight: 600, color: 'var(--text-secondary)', textAlign: 'right' }}>Amount</th>
                  </tr>
                </thead>
                <tbody>
                  {payments.sort((a: any, b: any) => new Date(b.payment_date).getTime() - new Date(a.payment_date).getTime()).map((p: any) => (
                    <tr key={p.id} style={{ borderBottom: '1px solid var(--border)' }}>
                      <td style={{ padding: '12px 16px', color: 'var(--text)' }}>{formatDate(p.payment_date)}</td>
                      <td style={{ padding: '12px 16px', fontWeight: 500 }}>PMT-{String(p.id).padStart(4, '0')}</td>
                      <td style={{ padding: '12px 16px' }}>{getPartyName(p.party_id)}</td>
                      <td style={{ padding: '12px 16px', textAlign: 'right', fontWeight: 600, color: 'var(--success)' }}>{formatCurrency(p.amount)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      )}

      {tab === 'ar' && (
        <div style={{ padding: '0 20px', paddingBottom: 24 }}>
          <div style={{ background: 'var(--bg-card)', borderRadius: 'var(--radius-lg)', border: '1px solid var(--border)', overflow: 'hidden' }}>
            <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <h3 style={{ fontSize: 16, fontWeight: 700 }}>Accounts Receivable</h3>
              <p style={{ fontSize: 14, fontWeight: 700, color: 'var(--warning)' }}>
                Total AR: {formatCurrency(partyList.filter((p: any) => p.outstanding > 0).reduce((sum: number, p: any) => sum + Number(p.outstanding), 0))}
              </p>
            </div>
            {partyList.filter((p: any) => p.outstanding > 0).length === 0 ? (
              <div className="empty-state"><p>No outstanding balances</p></div>
            ) : (
              <table style={{ width: '100%', textAlign: 'left', borderCollapse: 'collapse', fontSize: 13 }}>
                <thead>
                  <tr style={{ background: 'var(--bg-elevated)', borderBottom: '1px solid var(--border)' }}>
                    <th style={{ padding: '12px 16px', fontWeight: 600, color: 'var(--text-secondary)' }}>Party Name</th>
                    <th style={{ padding: '12px 16px', fontWeight: 600, color: 'var(--text-secondary)', textAlign: 'right' }}>Outstanding</th>
                  </tr>
                </thead>
                <tbody>
                  {partyList.filter((p: any) => p.outstanding > 0).sort((a: any, b: any) => Number(b.outstanding) - Number(a.outstanding)).map((p: any) => (
                    <tr key={p.id} style={{ borderBottom: '1px solid var(--border)' }}>
                      <td style={{ padding: '12px 16px', fontWeight: 500 }}>{p.name}</td>
                      <td style={{ padding: '12px 16px', textAlign: 'right', fontWeight: 700, color: 'var(--warning)' }}>{formatCurrency(p.outstanding)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      )}

    </div>
  );
}
