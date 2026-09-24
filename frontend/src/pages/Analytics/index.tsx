import { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { analyticsApi, invoicesApi, paymentsApi } from '../../api/endpoints';
import { formatCurrency, formatDate } from '../../utils/format';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, PieChart, Pie, Cell, Legend,
  ComposedChart, Line
} from 'recharts';

const COLORS = ['#eab308', '#10b981', '#3b82f6', '#ef4444', '#8b5cf6', '#06b6d4', '#ec4899', '#14b8a6', '#f97316', '#84cc16'];
const MODE_COLORS: Record<string, string> = { cash: '#10b981', upi: '#eab308', bank: '#3b82f6', cheque: '#f59e0b' };
const PAGE_SIZE = 20;

export default function Analytics() {
  const [tab, setTab] = useState<'overview' | 'sales' | 'collections' | 'ar' | 'agents' | 'areas' | 'fabric'>('overview');
  const [collectionDateFilter, setCollectionDateFilter] = useState<'all' | 'month' | 'week'>('all');

  // Paginated state per tab
  const [invPage, setInvPage] = useState(0);
  const [pmtPage, setPmtPage] = useState(0);
  const [arPage, setArPage] = useState(0);

  // Reset pages on tab switch
  useEffect(() => { setInvPage(0); setPmtPage(0); setArPage(0); }, [tab]);

  const { data: summary } = useQuery({
    queryKey: ['dashboard'],
    queryFn: () => analyticsApi.summary().then((r) => r.data),
  });
  const { data: parties = [] } = useQuery({
    queryKey: ['analytics-parties'],
    queryFn: () => analyticsApi.parties().then((r) => r.data.items || []),
  });
  const { data: aging = [] } = useQuery({
    queryKey: ['aging'],
    queryFn: () => analyticsApi.aging().then((r) => r.data.items || []),
    enabled: tab === 'overview',
  });
  const { data: cashflow = [] } = useQuery({
    queryKey: ['cashflow'],
    queryFn: () => analyticsApi.cashflow().then((r) => r.data),
    enabled: tab === 'overview',
  });
  const { data: execSummary } = useQuery({
    queryKey: ['execSummary'],
    queryFn: () => analyticsApi.executiveSummary().then((r) => r.data),
    enabled: tab === 'overview',
  });
  const { data: fabricData = [] } = useQuery({
    queryKey: ['fabricMetrics'],
    queryFn: () => analyticsApi.fabricMetrics().then((r) => r.data),
    enabled: tab === 'fabric',
  });

  const { data: invData } = useQuery({
    queryKey: ['reports-invoices', invPage],
    queryFn: () => invoicesApi.list(undefined, undefined, undefined, invPage * PAGE_SIZE, PAGE_SIZE).then(r => r.data),
    enabled: tab === 'sales',
  });

  const { data: pmtData } = useQuery({
    queryKey: ['reports-payments', pmtPage],
    queryFn: () => paymentsApi.list(undefined, undefined, pmtPage * PAGE_SIZE, PAGE_SIZE).then(r => r.data),
    enabled: tab === 'collections',
  });

  const { data: arData } = useQuery({
    queryKey: ['reports-ar', arPage],
    queryFn: () => analyticsApi.parties(undefined, arPage * PAGE_SIZE, PAGE_SIZE).then(r => r.data),
    enabled: tab === 'ar',
  });

  // F12: Mode breakdown
  const collectionFrom = collectionDateFilter === 'month'
    ? new Date(new Date().getFullYear(), new Date().getMonth(), 1).toISOString().split('T')[0]
    : collectionDateFilter === 'week'
      ? (() => { const d = new Date(); d.setDate(d.getDate() - d.getDay()); return d.toISOString().split('T')[0]; })()
      : undefined;
  const { data: modeData = [] } = useQuery({
    queryKey: ['collections-by-mode', collectionDateFilter],
    queryFn: () => analyticsApi.collectionsByMode(collectionFrom).then(r => r.data),
    enabled: tab === 'collections',
  });

  const { data: agentData = [] } = useQuery({
    queryKey: ['analytics-agent'],
    queryFn: () => analyticsApi.byAgent().then(r => r.data),
    enabled: tab === 'agents',
  });

  const { data: areaData = [] } = useQuery({
    queryKey: ['analytics-area'],
    queryFn: () => analyticsApi.byArea().then(r => r.data),
    enabled: tab === 'areas',
  });

  const invoices = invData?.items || [];
  const invTotal = invData?.total || 0;
  const invPages = Math.ceil(invTotal / PAGE_SIZE);
  const invSummaryTotal = invData?.summary_total || 0;

  const payments = pmtData?.items || [];
  const pmtTotal = pmtData?.total || 0;
  const pmtPages = Math.ceil(pmtTotal / PAGE_SIZE);
  const pmtSummaryTotal = pmtData?.summary_total || 0;

  const arParties = (arData?.items || []).filter((p: any) => p.outstanding > 0);
  const arTotal = arData?.total || 0;
  const arPages = Math.ceil(arTotal / PAGE_SIZE);
  const totalAR = summary?.total_outstanding || 0;

  // Charts: top 10 parties, group rest as "Others"
  const allWithOutstanding = (Array.isArray(parties) ? parties : []).filter((p: any) => p.outstanding > 0);
  const top10 = allWithOutstanding.slice(0, 10);
  const othersTotal = allWithOutstanding.slice(10).reduce((s: number, p: any) => s + Number(p.outstanding), 0);

  const barData = top10.map((p: any) => ({
    name: p.party_name.length > 12 ? p.party_name.slice(0, 12) + '…' : p.party_name,
    Invoiced: Number(p.total_invoiced),
    Collected: Number(p.total_paid),
  }));

  const pieData = [
    ...top10.map((p: any) => ({ name: p.party_name.length > 18 ? p.party_name.slice(0, 18) + '…' : p.party_name, value: Number(p.outstanding) })),
    ...(othersTotal > 0 ? [{ name: `Others (${allWithOutstanding.length - 10})`, value: othersTotal }] : []),
  ].filter(d => d.value > 0);

  const totalAging = (Array.isArray(aging) ? aging : []).reduce((acc: any, curr: any) => {
    acc.current += Number(curr.current || 0);
    acc.days_31_60 += Number(curr.days_31_60 || 0);
    acc.days_61_90 += Number(curr.days_61_90 || 0);
    acc.over_90 += Number(curr.over_90 || 0);
    return acc;
  }, { current: 0, days_31_60: 0, days_61_90: 0, over_90: 0 });

  const agingGraphData = [
    { name: '0-30 Days', value: totalAging.current, fill: '#10b981' },
    { name: '31-60 Days', value: totalAging.days_31_60, fill: '#f59e0b' },
    { name: '61-90 Days', value: totalAging.days_61_90, fill: '#3b82f6' },
    { name: '90+ Days', value: totalAging.over_90, fill: '#ef4444' }
  ].filter(d => d.value > 0);

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

  const PaginationBar = ({ page, totalPages, onPrev, onNext }: any) => (
    <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: 12, padding: '14px 0', borderTop: '1px solid var(--border)' }}>
      <button className="btn btn-sm btn-secondary" disabled={page === 0} onClick={onPrev}>← Prev</button>
      <span style={{ fontSize: 13, color: 'var(--text-secondary)' }}>Page {page + 1} of {Math.max(totalPages, 1)}</span>
      <button className="btn btn-sm btn-secondary" disabled={page >= totalPages - 1} onClick={onNext}>Next →</button>
    </div>
  );

  return (
    <div className="page-content">
      <div className="page-header">
        <h1 className="page-title">Reports Hub</h1>
        <p className="page-subtitle">Business & Accounting Reports</p>
      </div>

      <div className="chips" style={{ marginBottom: 16 }}>
        <button className={`chip ${tab === 'overview' ? 'active' : ''}`} onClick={() => setTab('overview')}>Overview</button>
        <button className={`chip ${tab === 'sales' ? 'active' : ''}`} onClick={() => setTab('sales')}>Sales</button>
        <button className={`chip ${tab === 'collections' ? 'active' : ''}`} onClick={() => setTab('collections')}>Collections</button>
        <button className={`chip ${tab === 'ar' ? 'active' : ''}`} onClick={() => setTab('ar')}>A/R</button>
        <button className={`chip ${tab === 'agents' ? 'active' : ''}`} onClick={() => setTab('agents')}>By Agent</button>
        <button className={`chip ${tab === 'areas' ? 'active' : ''}`} onClick={() => setTab('areas')}>By Area</button>
        <button className={`chip ${tab === 'fabric' ? 'active' : ''}`} onClick={() => setTab('fabric')}>Fabric/Items</button>
      </div>

      {tab === 'overview' && (
        <>
          {execSummary && (
            <div style={{ padding: '0 20px', marginBottom: 24 }}>
              <p className="section-label" style={{ padding: 0, marginBottom: 8 }}>Founder KPIs (Health & Risk)</p>
              <div className="stats-grid" style={{ gridTemplateColumns: 'repeat(5, 1fr)', gap: 12 }}>
                <div className="stat-card" style={{ background: 'var(--bg-card)' }}>
                  <p className="stat-label">DSO (Velocity)</p>
                  <p className="stat-value mono" style={{ fontSize: 18, color: Number(execSummary.dso_days) > 60 ? 'var(--danger)' : 'var(--success)' }}>{Number(execSummary.dso_days).toFixed(0)} Days</p>
                </div>
                <div className="stat-card" style={{ background: 'var(--bg-card)' }}>
                  <p className="stat-label">Unallocated Adv.</p>
                  <p className="stat-value mono" style={{ fontSize: 18, color: 'var(--accent)' }}>{formatCurrency(execSummary.unallocated_advance_pool)}</p>
                </div>
                <div className="stat-card" style={{ background: 'var(--bg-card)' }}>
                  <p className="stat-label">At-Risk (>60d)</p>
                  <p className="stat-value mono" style={{ fontSize: 18, color: Number(execSummary.at_risk_ratio) > 15 ? 'var(--danger)' : 'var(--warning)' }}>{Number(execSummary.at_risk_ratio).toFixed(1)}%</p>
                </div>
                <div className="stat-card" style={{ background: 'var(--bg-card)' }}>
                  <p className="stat-label">Journal Adj.</p>
                  <p className="stat-value mono" style={{ fontSize: 18, color: Number(execSummary.journal_adjustment_ratio) > 5 ? 'var(--danger)' : 'var(--success)' }}>{Number(execSummary.journal_adjustment_ratio).toFixed(1)}%</p>
                </div>
                <div className="stat-card" style={{ background: 'var(--bg-card)' }}>
                  <p className="stat-label">Top 10 Risk</p>
                  <p className="stat-value mono" style={{ fontSize: 18, color: Number(execSummary.top_10_concentration) > 50 ? 'var(--danger)' : 'var(--text-primary)' }}>{Number(execSummary.top_10_concentration).toFixed(1)}%</p>
                </div>
              </div>
            </div>
          )}
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

          {/* Bar Chart — Top 10 */}
          {barData.length > 0 && (
            <>
              <p className="section-label">Top Parties — Invoice vs Collected</p>
              <div style={{ padding: '0 20px' }}>
                <div style={{ background: 'var(--bg-card)', borderRadius: 'var(--radius-lg)', border: '1px solid var(--border)', padding: '16px 4px 8px' }}>
                  <ResponsiveContainer width="100%" height={200}>
                    <BarChart data={barData} margin={{ left: -16 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(0,0,0,0.06)" />
                      <XAxis dataKey="name" tick={{ fill: '#94a3b8', fontSize: 9 }} axisLine={false} tickLine={false} />
                      <YAxis tick={{ fill: '#94a3b8', fontSize: 10 }} axisLine={false} tickLine={false}
                        tickFormatter={(v) => v >= 1000 ? `${(v / 1000).toFixed(0)}k` : v} />
                      <Tooltip content={<CustomTooltip />} />
                      <Bar dataKey="Invoiced" fill="#eab308" radius={[4, 4, 0, 0]} />
                      <Bar dataKey="Collected" fill="#10b981" radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </>
          )}

          {/* Pie Chart — Top 10 + Others */}
          {pieData.length > 0 && (
            <>
              <p className="section-label">Outstanding by Party {allWithOutstanding.length > 10 ? `(Top 10 + ${allWithOutstanding.length - 10} others)` : ''}</p>
              <div style={{ padding: '0 20px' }}>
                <div style={{ background: 'var(--bg-card)', borderRadius: 'var(--radius-lg)', border: '1px solid var(--border)', padding: '16px 4px 8px' }}>
                  <ResponsiveContainer width="100%" height={240}>
                    <PieChart>
                      <Pie data={pieData} cx="50%" cy="45%" outerRadius={80} dataKey="value"
                        label={({ percent }) => percent > 0.04 ? `${(percent * 100).toFixed(0)}%` : ''}
                        labelLine={false}>
                        {pieData.map((_: any, i: number) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                      </Pie>
                      <Legend formatter={(value) => <span style={{ fontSize: 10, color: 'var(--text-secondary)' }}>{value}</span>} />
                      <Tooltip formatter={(value: any) => formatCurrency(value)} contentStyle={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)', borderRadius: 8 }} />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </>
          )}

          {/* Cashflow & Aging Visuals */}
          <div className="stats-grid" style={{ gridTemplateColumns: '1fr 1fr', padding: '0 20px', marginBottom: 20 }}>
            {cashflow.length > 0 && (
              <div>
                <p className="section-label" style={{ padding: 0, marginBottom: 8 }}>Monthly Cash Flow Pipeline</p>
                <div style={{ background: 'var(--bg-card)', borderRadius: 'var(--radius-lg)', border: '1px solid var(--border)', padding: '16px 16px 8px 4px' }}>
                  <ResponsiveContainer width="100%" height={240}>
                    <ComposedChart data={cashflow}>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="rgba(255,255,255,0.05)" />
                      <XAxis dataKey="month" axisLine={false} tickLine={false} tick={{ fontSize: 10, fill: 'var(--text-muted)' }} />
                      <YAxis yAxisId="left" tickFormatter={(val) => `₹${val >= 1000 ? (val/1000).toFixed(0)+'k' : val}`} axisLine={false} tickLine={false} tick={{ fontSize: 10, fill: 'var(--text-muted)' }} />
                      <Tooltip formatter={(value: any) => formatCurrency(value)} contentStyle={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)', borderRadius: 8 }} />
                      <Legend formatter={(value) => <span style={{ fontSize: 11, color: 'var(--text-secondary)' }}>{value.charAt(0).toUpperCase() + value.slice(1)}</span>} />
                      <Bar yAxisId="left" dataKey="invoiced" name="Invoiced Sales" fill="var(--accent)" radius={[4, 4, 0, 0]} barSize={20} />
                      <Line yAxisId="left" type="monotone" dataKey="collected" name="Collections" stroke="var(--success)" strokeWidth={3} dot={{ r: 4 }} />
                    </ComposedChart>
                  </ResponsiveContainer>
                </div>
              </div>
            )}
            
            {agingGraphData.length > 0 && (
              <div>
                <p className="section-label" style={{ padding: 0, marginBottom: 8 }}>Total Receivable Aging</p>
                <div style={{ background: 'var(--bg-card)', borderRadius: 'var(--radius-lg)', border: '1px solid var(--border)', padding: '16px 16px 8px 4px' }}>
                  <ResponsiveContainer width="100%" height={240}>
                    <BarChart data={agingGraphData} layout="vertical" margin={{ left: 20 }}>
                      <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="rgba(255,255,255,0.05)" />
                      <XAxis type="number" tickFormatter={(val) => `₹${val >= 1000 ? (val/1000).toFixed(0)+'k' : val}`} axisLine={false} tickLine={false} tick={{ fontSize: 10, fill: 'var(--text-muted)' }} />
                      <YAxis dataKey="name" type="category" axisLine={false} tickLine={false} tick={{ fontSize: 11, fill: 'var(--text-secondary)' }} />
                      <Tooltip formatter={(value: any) => formatCurrency(value)} cursor={{ fill: 'rgba(255,255,255,0.02)' }} contentStyle={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)', borderRadius: 8 }} />
                      <Bar dataKey="value" radius={[0, 4, 4, 0]} barSize={24}>
                        {agingGraphData.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={entry.fill} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>
            )}
          </div>

          {/* Aging Report */}
          {aging.length > 0 && (
            <>
              <p className="section-label">Receivable Aging</p>
              <div style={{ padding: '0 20px', marginBottom: 20 }}>
                {(Array.isArray(aging) ? aging : []).map((row: any) => (
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
          {/* Summary banner */}
          <div className="stats-grid" style={{ marginBottom: 16 }}>
            <div className="stat-card accent">
              <p className="stat-label">Total Invoices</p>
              <p className="stat-value">{invTotal}</p>
            </div>
            <div className="stat-card success">
              <p className="stat-label">Total Sales Value</p>
              <p className="stat-value mono" style={{ fontSize: 14 }}>{formatCurrency(invSummaryTotal)}</p>
            </div>
          </div>
          <div style={{ background: 'var(--bg-card)', borderRadius: 'var(--radius-lg)', border: '1px solid var(--border)', overflow: 'hidden' }}>
            <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--border)' }}>
              <h3 style={{ fontSize: 16, fontWeight: 700 }}>Sales Register</h3>
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
                  {invoices.map((inv: any) => (
                    <tr key={inv.id} style={{ borderBottom: '1px solid var(--border)' }}>
                      <td style={{ padding: '12px 16px', color: 'var(--text)' }}>{formatDate(inv.invoice_date)}</td>
                      <td style={{ padding: '12px 16px', fontWeight: 500 }}>{inv.invoice_number}</td>
                      <td style={{ padding: '12px 16px' }}>{inv.party_name}</td>
                      <td style={{ padding: '12px 16px', textAlign: 'right', fontWeight: 600 }}>{formatCurrency(inv.total || inv.amount)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
            {invPages > 1 && <PaginationBar page={invPage} totalPages={invPages} onPrev={() => setInvPage(p => p - 1)} onNext={() => setInvPage(p => p + 1)} />}
          </div>
        </div>
      )}

      {tab === 'collections' && (
        <div style={{ padding: '0 20px', paddingBottom: 24 }}>
          {/* Summary banner */}
          <div className="stats-grid" style={{ marginBottom: 16 }}>
            <div className="stat-card success">
              <p className="stat-label">Total Receipts</p>
              <p className="stat-value">{pmtTotal}</p>
            </div>
            <div className="stat-card accent">
              <p className="stat-label">Total Collected</p>
              <p className="stat-value mono" style={{ fontSize: 14 }}>{formatCurrency(pmtSummaryTotal)}</p>
            </div>
          </div>

          {/* F12: Mode breakdown */}
          <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
            {(['all', 'month', 'week'] as const).map(f => (
              <button key={f} onClick={() => setCollectionDateFilter(f)} style={{ padding: '5px 14px', borderRadius: 20, border: `1px solid ${collectionDateFilter === f ? 'var(--accent)' : 'var(--border)'}`, background: collectionDateFilter === f ? 'var(--accent-glow)' : 'transparent', color: collectionDateFilter === f ? 'var(--accent)' : 'var(--text-muted)', fontSize: 12, fontWeight: collectionDateFilter === f ? 600 : 400, cursor: 'pointer' }}>{f === 'all' ? 'All Time' : f === 'month' ? 'This Month' : 'This Week'}</button>
            ))}
          </div>

          {Array.isArray(modeData) && modeData.length > 0 && (
            <>
              <p className="section-label" style={{ paddingLeft: 0, marginBottom: 8 }}>Collections by Mode</p>
              <div style={{ background: 'var(--bg-card)', borderRadius: 'var(--radius-lg)', border: '1px solid var(--border)', padding: '16px 4px 8px', marginBottom: 16 }}>
                <ResponsiveContainer width="100%" height={180}>
                  <BarChart data={modeData.map((m: any) => ({ name: m.mode.toUpperCase(), Amount: Number(m.total), Count: m.count }))} margin={{ left: -16 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(0,0,0,0.06)" />
                    <XAxis dataKey="name" tick={{ fill: '#94a3b8', fontSize: 11 }} axisLine={false} tickLine={false} />
                    <YAxis tick={{ fill: '#94a3b8', fontSize: 10 }} axisLine={false} tickLine={false} tickFormatter={v => v >= 1000 ? `${(v / 1000).toFixed(0)}k` : v} />
                    <Tooltip formatter={(v: any) => formatCurrency(v)} contentStyle={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)', borderRadius: 8 }} />
                    <Bar dataKey="Amount" radius={[4, 4, 0, 0]}>
                      {modeData.map((m: any, i: number) => <Cell key={i} fill={MODE_COLORS[m.mode] || COLORS[i % COLORS.length]} />)}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 8, marginBottom: 16 }}>
                {modeData.map((m: any) => (
                  <div key={m.mode} style={{ background: 'var(--bg-card)', borderRadius: 10, border: '1px solid var(--border)', padding: 12 }}>
                    <p style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 600, letterSpacing: 1 }}>{m.mode}</p>
                    <p style={{ fontSize: 16, fontWeight: 700, color: MODE_COLORS[m.mode] || 'var(--accent)', marginTop: 4 }}>{formatCurrency(m.total)}</p>
                    <p style={{ fontSize: 11, color: 'var(--text-muted)' }}>{m.count} payment{m.count !== 1 ? 's' : ''}</p>
                  </div>
                ))}
              </div>
            </>
          )}

          <div style={{ background: 'var(--bg-card)', borderRadius: 'var(--radius-lg)', border: '1px solid var(--border)', overflow: 'hidden' }}>
            <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--border)' }}>
              <h3 style={{ fontSize: 16, fontWeight: 700 }}>Collection Register</h3>
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
                  {payments.map((p: any) => (
                    <tr key={p.id} style={{ borderBottom: '1px solid var(--border)' }}>
                      <td style={{ padding: '12px 16px', color: 'var(--text)' }}>{formatDate(p.payment_date)}</td>
                      <td style={{ padding: '12px 16px', fontWeight: 500 }}>PMT-{String(p.id).padStart(4, '0')}</td>
                      <td style={{ padding: '12px 16px' }}>{p.party_name}</td>
                      <td style={{ padding: '12px 16px', textAlign: 'right', fontWeight: 600, color: 'var(--success)' }}>{formatCurrency(p.amount)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
            {pmtPages > 1 && <PaginationBar page={pmtPage} totalPages={pmtPages} onPrev={() => setPmtPage(p => p - 1)} onNext={() => setPmtPage(p => p + 1)} />}
          </div>
        </div>
      )}

      {tab === 'ar' && (
        <div style={{ padding: '0 20px', paddingBottom: 24 }}>
          {/* Summary banner */}
          <div className="stats-grid" style={{ marginBottom: 16 }}>
            <div className="stat-card warning">
              <p className="stat-label">Total A/R Outstanding</p>
              <p className="stat-value mono" style={{ fontSize: 14 }}>{formatCurrency(totalAR)}</p>
            </div>
            <div className="stat-card danger">
              <p className="stat-label">Overdue Invoices</p>
              <p className="stat-value">{summary?.overdue_count || 0} bills</p>
            </div>
          </div>
          <div style={{ background: 'var(--bg-card)', borderRadius: 'var(--radius-lg)', border: '1px solid var(--border)', overflow: 'hidden' }}>
            <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--border)' }}>
              <h3 style={{ fontSize: 16, fontWeight: 700 }}>Accounts Receivable</h3>
            </div>
            {arParties.length === 0 ? (
              <div className="empty-state"><p>No outstanding balances</p></div>
            ) : (
              <table style={{ width: '100%', textAlign: 'left', borderCollapse: 'collapse', fontSize: 13 }}>
                <thead>
                  <tr style={{ background: 'var(--bg-elevated)', borderBottom: '1px solid var(--border)' }}>
                    <th style={{ padding: '12px 16px', fontWeight: 600, color: 'var(--text-secondary)' }}>Party Name</th>
                    <th style={{ padding: '12px 16px', fontWeight: 600, color: 'var(--text-secondary)', textAlign: 'right' }}>Invoiced</th>
                    <th style={{ padding: '12px 16px', fontWeight: 600, color: 'var(--text-secondary)', textAlign: 'right' }}>Outstanding</th>
                  </tr>
                </thead>
                <tbody>
                  {arParties.map((p: any) => (
                    <tr key={p.party_id} style={{ borderBottom: '1px solid var(--border)' }}>
                      <td style={{ padding: '12px 16px', fontWeight: 500 }}>{p.party_name}</td>
                      <td style={{ padding: '12px 16px', textAlign: 'right', color: 'var(--text-secondary)' }}>{formatCurrency(p.total_invoiced)}</td>
                      <td style={{ padding: '12px 16px', textAlign: 'right', fontWeight: 700, color: 'var(--warning)' }}>{formatCurrency(p.outstanding)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
            {arPages > 1 && <PaginationBar page={arPage} totalPages={arPages} onPrev={() => setArPage(p => p - 1)} onNext={() => setArPage(p => p + 1)} />}
          </div>
        </div>
      )}

      {tab === 'agents' && (
        <div style={{ padding: '0 20px', paddingBottom: 24 }}>
          <div style={{ background: 'var(--bg-card)', borderRadius: 'var(--radius-lg)', border: '1px solid var(--border)', overflow: 'hidden' }}>
            <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--border)' }}>
              <h3 style={{ fontSize: 16, fontWeight: 700 }}>Performance by Agent</h3>
            </div>
            {agentData.length === 0 ? (
              <div className="empty-state"><p>No agent data</p></div>
            ) : (
              <table style={{ width: '100%', textAlign: 'left', borderCollapse: 'collapse', fontSize: 13 }}>
                <thead>
                  <tr style={{ background: 'var(--bg-elevated)', borderBottom: '1px solid var(--border)' }}>
                    <th style={{ padding: '12px 16px', fontWeight: 600, color: 'var(--text-secondary)' }}>Agent Name</th>
                    <th style={{ padding: '12px 16px', fontWeight: 600, color: 'var(--text-secondary)', textAlign: 'center' }}>Parties</th>
                    <th style={{ padding: '12px 16px', fontWeight: 600, color: 'var(--text-secondary)', textAlign: 'right' }}>Total Sales</th>
                    <th style={{ padding: '12px 16px', fontWeight: 600, color: 'var(--text-secondary)', textAlign: 'right' }}>Collected</th>
                    <th style={{ padding: '12px 16px', fontWeight: 600, color: 'var(--text-secondary)', textAlign: 'right' }}>Outstanding</th>
                  </tr>
                </thead>
                <tbody>
                  {agentData.map((d: any, i: number) => (
                    <tr key={i} style={{ borderBottom: '1px solid var(--border)' }}>
                      <td style={{ padding: '12px 16px', fontWeight: 500 }}>{d.group_name}</td>
                      <td style={{ padding: '12px 16px', textAlign: 'center' }}>{d.party_count}</td>
                      <td style={{ padding: '12px 16px', textAlign: 'right', color: 'var(--accent)' }}>{formatCurrency(d.total_invoiced)}</td>
                      <td style={{ padding: '12px 16px', textAlign: 'right', color: 'var(--success)' }}>{formatCurrency(d.total_paid)}</td>
                      <td style={{ padding: '12px 16px', textAlign: 'right', fontWeight: 700, color: 'var(--warning)' }}>{formatCurrency(d.outstanding)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      )}

      {tab === 'areas' && (
        <div style={{ padding: '0 20px', paddingBottom: 24 }}>
          <div style={{ background: 'var(--bg-card)', borderRadius: 'var(--radius-lg)', border: '1px solid var(--border)', overflow: 'hidden' }}>
            <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--border)' }}>
              <h3 style={{ fontSize: 16, fontWeight: 700 }}>Performance by Area</h3>
            </div>
            {areaData.length === 0 ? (
              <div className="empty-state"><p>No area data</p></div>
            ) : (
              <table style={{ width: '100%', textAlign: 'left', borderCollapse: 'collapse', fontSize: 13 }}>
                <thead>
                  <tr style={{ background: 'var(--bg-elevated)', borderBottom: '1px solid var(--border)' }}>
                    <th style={{ padding: '12px 16px', fontWeight: 600, color: 'var(--text-secondary)' }}>Area</th>
                    <th style={{ padding: '12px 16px', fontWeight: 600, color: 'var(--text-secondary)', textAlign: 'center' }}>Parties</th>
                    <th style={{ padding: '12px 16px', fontWeight: 600, color: 'var(--text-secondary)', textAlign: 'right' }}>Total Sales</th>
                    <th style={{ padding: '12px 16px', fontWeight: 600, color: 'var(--text-secondary)', textAlign: 'right' }}>Collected</th>
                    <th style={{ padding: '12px 16px', fontWeight: 600, color: 'var(--text-secondary)', textAlign: 'right' }}>Outstanding</th>
                  </tr>
                </thead>
                <tbody>
                  {areaData.map((d: any, i: number) => (
                    <tr key={i} style={{ borderBottom: '1px solid var(--border)' }}>
                      <td style={{ padding: '12px 16px', fontWeight: 500 }}>{d.group_name}</td>
                      <td style={{ padding: '12px 16px', textAlign: 'center' }}>{d.party_count}</td>
                      <td style={{ padding: '12px 16px', textAlign: 'right', color: 'var(--accent)' }}>{formatCurrency(d.total_invoiced)}</td>
                      <td style={{ padding: '12px 16px', textAlign: 'right', color: 'var(--success)' }}>{formatCurrency(d.total_paid)}</td>
                      <td style={{ padding: '12px 16px', textAlign: 'right', fontWeight: 700, color: 'var(--warning)' }}>{formatCurrency(d.outstanding)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
          </div>
        </div>
      )}

      {tab === 'fabric' && (
        <div style={{ padding: '0 20px', paddingBottom: 24 }}>
          <p className="section-label">Fabric & Unit Economics</p>
          <div style={{ background: 'var(--bg-card)', borderRadius: 'var(--radius-lg)', border: '1px solid var(--border)' }}>
            <div className="table-responsive">
              <table>
                <thead>
                  <tr>
                    <th>Item / Fabric</th>
                    <th style={{ textAlign: 'right' }}>Total Volume (Meters)</th>
                    <th style={{ textAlign: 'right' }}>Avg Realized Rate</th>
                    <th style={{ textAlign: 'right' }}>Avg Ticket Size</th>
                  </tr>
                </thead>
                <tbody>
                  {fabricData.map((f: any) => (
                    <tr key={f.item_name}>
                      <td style={{ fontWeight: 500 }}>{f.item_name}</td>
                      <td style={{ textAlign: 'right' }}>{Number(f.total_meterage).toFixed(2)} m</td>
                      <td style={{ textAlign: 'right', color: 'var(--success)' }}>₹{Number(f.avg_realized_rate).toFixed(2)} /m</td>
                      <td style={{ textAlign: 'right', color: 'var(--accent)' }}>{formatCurrency(f.avg_ticket_size)}</td>
                    </tr>
                  ))}
                  {fabricData.length === 0 && (
                    <tr><td colSpan={4} style={{ textAlign: 'center', padding: 24 }}>No fabric data found</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}

