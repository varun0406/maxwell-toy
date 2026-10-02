import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Plus, Package, Search } from 'lucide-react';
import { formatCurrency, formatDate } from '../../utils/format';
import { api } from '../../api/client';

const API = '/purchases';

// ── API helpers ──────────────────────────────────────────────────────────────
async function fetchVendors(search = '', tag?: string) {
  const params: Record<string, string> = { search };
  if (tag) params.tag = tag;
  const r = await api.get(`${API}/vendors`, { params });
  return r.data as Vendor[];
}
async function fetchBills(vendorId?: number, unpaidOnly = false) {
  const params: Record<string, string | boolean | number> = { unpaid_only: unpaidOnly };
  if (vendorId) params.vendor_id = vendorId;
  const r = await api.get(`${API}/bills`, { params });
  return r.data as PurchaseBill[];
}
async function fetchVendorPayments(vendorId?: number) {
  const params: Record<string, number> = {};
  if (vendorId) params.vendor_id = vendorId;
  const r = await api.get(`${API}/payments`, { params });
  return r.data as VendorPaymentRecord[];
}

// ── Types ────────────────────────────────────────────────────────────────────
interface Vendor {
  id: number; name: string; phone?: string; address?: string; city?: string;
  tag?: string; notes?: string; total_purchased: number; total_paid: number;
  balance_payable: number;
}
interface PurchaseBill {
  id: number; vendor_id: number; vendor_name?: string; bill_number?: string;
  amount: number; balance_due: number; purchase_date: string;
  description?: string; is_paid: boolean;
}
interface VendorPaymentRecord {
  id: number; vendor_id: number; vendor_name?: string; amount: number;
  payment_date: string; mode?: string; note?: string; purchase_id?: number;
}

// ── Purchases Page ───────────────────────────────────────────────────────────
export default function Purchases() {
  const qc = useQueryClient();
  const [tab, setTab] = useState<'vendors' | 'bills' | 'payments'>('vendors');
  const [search, setSearch] = useState('');
  const [tagFilter, setTagFilter] = useState('');
  const [unpaidOnly, setUnpaidOnly] = useState(false);
  const [selectedVendor, setSelectedVendor] = useState<Vendor | null>(null);
  const [showAddVendor, setShowAddVendor] = useState(false);
  const [showAddBill, setShowAddBill] = useState(false);
  const [showAddPayment, setShowAddPayment] = useState(false);

  const { data: vendors = [], isLoading: vendorsLoading } = useQuery({
    queryKey: ['vendors', search, tagFilter],
    queryFn: () => fetchVendors(search, tagFilter || undefined),
  });

  const { data: bills = [] } = useQuery({
    queryKey: ['purchase-bills', selectedVendor?.id, unpaidOnly],
    queryFn: () => fetchBills(selectedVendor?.id, unpaidOnly),
    enabled: tab === 'bills',
  });

  const { data: vendorPayments = [] } = useQuery({
    queryKey: ['vendor-payments', selectedVendor?.id],
    queryFn: () => fetchVendorPayments(selectedVendor?.id),
    enabled: tab === 'payments',
  });

  const totalPayable = vendors.reduce((s, v) => s + v.balance_payable, 0);
  const totalPurchased = vendors.reduce((s, v) => s + v.total_purchased, 0);

  return (
    <div className="page-content">
      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h1 className="page-title">Purchases</h1>
          <p className="page-subtitle">Vendor bills & outgoing payments</p>
        </div>
        <button
          onClick={() => setShowAddVendor(true)}
          style={{ background: 'var(--accent)', color: 'white', border: 'none', borderRadius: 12, padding: '8px 16px', fontWeight: 700, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6 }}
        >
          <Plus size={16} /> Add Vendor
        </button>
      </div>

      {/* Summary cards */}
      <div className="stats-grid" style={{ gridTemplateColumns: '1fr 1fr 1fr' }}>
        <div className="stat-card accent">
          <p className="stat-label">Total Purchased</p>
          <p className="stat-value mono" style={{ fontSize: 15 }}>{formatCurrency(totalPurchased)}</p>
        </div>
        <div className="stat-card danger">
          <p className="stat-label">Total Payable</p>
          <p className="stat-value mono" style={{ fontSize: 15 }}>{formatCurrency(totalPayable)}</p>
        </div>
        <div className="stat-card">
          <p className="stat-label">Vendors</p>
          <p className="stat-value" style={{ fontSize: 15 }}>{vendors.length}</p>
        </div>
      </div>

      {/* Tabs */}
      <div className="chips">
        {(['vendors', 'bills', 'payments'] as const).map(t => (
          <button key={t} className={`chip ${tab === t ? 'active' : ''}`} onClick={() => setTab(t)}>
            {t.charAt(0).toUpperCase() + t.slice(1)}
          </button>
        ))}
      </div>

      {/* Vendors Tab */}
      {tab === 'vendors' && (
        <div style={{ padding: '0 20px', marginTop: 8 }}>
          {/* Search + tag filter */}
          <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
            <div style={{ flex: 1, display: 'flex', alignItems: 'center', background: 'var(--surface)', padding: '8px 14px', borderRadius: 12, border: '1px solid var(--border)', gap: 8 }}>
              <Search size={15} />
              <input placeholder="Search vendors…" value={search} onChange={e => setSearch(e.target.value)}
                style={{ border: 'none', background: 'none', outline: 'none', fontSize: 14, width: '100%' }} />
            </div>
            <select value={tagFilter} onChange={e => setTagFilter(e.target.value)}
              style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 12, padding: '8px 12px', fontSize: 13, cursor: 'pointer' }}>
              <option value="">All Types</option>
              <option value="KARIGAR">KARIGAR</option>
              <option value="Supplier">Supplier</option>
              <option value="Other">Other</option>
            </select>
          </div>

          {vendorsLoading ? (
            <div className="loading-screen"><div className="spinner" /></div>
          ) : vendors.length === 0 ? (
            <div className="empty-state">
              <Package size={40} style={{ opacity: 0.3, marginBottom: 12 }} />
              <p>No vendors yet. Add your first vendor!</p>
            </div>
          ) : (
            <div style={{ background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 'var(--radius-lg)', overflow: 'hidden' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                <thead>
                  <tr style={{ background: 'var(--bg-elevated)', borderBottom: '2px solid var(--border)' }}>
                    <th style={{ padding: '10px 16px', textAlign: 'left', fontWeight: 700, color: 'var(--text-secondary)' }}>Vendor</th>
                    <th style={{ padding: '10px 16px', textAlign: 'left', fontWeight: 700, color: 'var(--text-secondary)' }}>Type</th>
                    <th style={{ padding: '10px 16px', textAlign: 'right', fontWeight: 700, color: 'var(--text-secondary)' }}>Total Purchased</th>
                    <th style={{ padding: '10px 16px', textAlign: 'right', fontWeight: 700, color: 'var(--text-secondary)' }}>Paid</th>
                    <th style={{ padding: '10px 16px', textAlign: 'right', fontWeight: 700, color: 'var(--text-secondary)' }}>Balance Payable</th>
                    <th style={{ padding: '10px 16px', textAlign: 'center', fontWeight: 700, color: 'var(--text-secondary)' }}>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {vendors.map(v => (
                    <tr key={v.id}
                      style={{ borderBottom: '1px solid var(--border)', transition: 'background 0.15s' }}
                      onMouseEnter={e => (e.currentTarget.style.background = 'var(--bg-elevated)')}
                      onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
                    >
                      <td style={{ padding: '10px 16px' }}>
                        <p style={{ fontWeight: 700 }}>{v.name}</p>
                        {v.phone && <p style={{ fontSize: 11, color: 'var(--text-muted)' }}>{v.phone}</p>}
                        {v.city && <p style={{ fontSize: 11, color: 'var(--text-muted)' }}>{v.city}</p>}
                      </td>
                      <td style={{ padding: '10px 16px' }}>
                        {v.tag && (
                          <span style={{ fontSize: 11, fontWeight: 700, padding: '3px 8px', borderRadius: 6,
                            background: v.tag === 'KARIGAR' ? 'rgba(99,102,241,0.12)' : 'rgba(234,179,8,0.12)',
                            color: v.tag === 'KARIGAR' ? 'var(--accent)' : 'var(--warning)' }}>
                            {v.tag}
                          </span>
                        )}
                      </td>
                      <td style={{ padding: '10px 16px', textAlign: 'right', fontWeight: 600 }}>{formatCurrency(v.total_purchased)}</td>
                      <td style={{ padding: '10px 16px', textAlign: 'right', color: 'var(--success)', fontWeight: 600 }}>{formatCurrency(v.total_paid)}</td>
                      <td style={{ padding: '10px 16px', textAlign: 'right', fontWeight: 700, color: v.balance_payable > 0 ? 'var(--danger)' : 'var(--success)' }}>
                        {v.balance_payable > 0 ? formatCurrency(v.balance_payable) : '—'}
                      </td>
                      <td style={{ padding: '10px 16px', textAlign: 'center' }}>
                        <div style={{ display: 'flex', gap: 6, justifyContent: 'center' }}>
                          <button onClick={() => { setSelectedVendor(v); setShowAddBill(true); }}
                            style={{ fontSize: 11, padding: '4px 8px', borderRadius: 6, background: 'rgba(99,102,241,0.12)', color: 'var(--accent)', border: 'none', cursor: 'pointer', fontWeight: 600 }}>
                            + Bill
                          </button>
                          <button onClick={() => { setSelectedVendor(v); setShowAddPayment(true); }}
                            style={{ fontSize: 11, padding: '4px 8px', borderRadius: 6, background: 'rgba(34,197,94,0.12)', color: 'var(--success)', border: 'none', cursor: 'pointer', fontWeight: 600 }}>
                            + Pay
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
                <tfoot>
                  <tr style={{ background: 'var(--bg-elevated)', borderTop: '2px solid var(--border)' }}>
                    <td colSpan={2} style={{ padding: '10px 16px', fontWeight: 700, fontSize: 12, color: 'var(--text-secondary)' }}>TOTAL ({vendors.length} vendors)</td>
                    <td style={{ padding: '10px 16px', textAlign: 'right', fontWeight: 800 }}>{formatCurrency(totalPurchased)}</td>
                    <td style={{ padding: '10px 16px', textAlign: 'right', fontWeight: 800, color: 'var(--success)' }}>{formatCurrency(vendors.reduce((s,v) => s + v.total_paid, 0))}</td>
                    <td style={{ padding: '10px 16px', textAlign: 'right', fontWeight: 800, color: 'var(--danger)' }}>{formatCurrency(totalPayable)}</td>
                    <td />
                  </tr>
                </tfoot>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Bills Tab */}
      {tab === 'bills' && (
        <div style={{ padding: '0 20px', marginTop: 8 }}>
          <div style={{ display: 'flex', gap: 8, marginBottom: 12, alignItems: 'center', flexWrap: 'wrap' }}>
            <select value={selectedVendor?.id || ''} onChange={e => {
              const v = vendors.find(v => v.id === Number(e.target.value));
              setSelectedVendor(v || null);
            }} style={{ flex: 1, background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 12, padding: '8px 12px', fontSize: 13 }}>
              <option value="">All Vendors</option>
              {vendors.map(v => <option key={v.id} value={v.id}>{v.name}</option>)}
            </select>
            <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 13, fontWeight: 600, cursor: 'pointer' }}>
              <input type="checkbox" checked={unpaidOnly} onChange={e => setUnpaidOnly(e.target.checked)} />
              Unpaid Only
            </label>
            <button onClick={() => setShowAddBill(true)}
              style={{ background: 'var(--accent)', color: 'white', border: 'none', borderRadius: 10, padding: '8px 14px', fontWeight: 700, cursor: 'pointer', fontSize: 13 }}>
              + New Bill
            </button>
          </div>

          {bills.length === 0 ? (
            <div className="empty-state"><p>No purchase bills found</p></div>
          ) : (
            <div style={{ background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 'var(--radius-lg)', overflow: 'hidden' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                <thead>
                  <tr style={{ background: 'var(--bg-elevated)', borderBottom: '2px solid var(--border)' }}>
                    <th style={{ padding: '10px 16px', textAlign: 'left', fontWeight: 700, color: 'var(--text-secondary)' }}>Date</th>
                    <th style={{ padding: '10px 16px', textAlign: 'left', fontWeight: 700, color: 'var(--text-secondary)' }}>Vendor</th>
                    <th style={{ padding: '10px 16px', textAlign: 'left', fontWeight: 700, color: 'var(--text-secondary)' }}>Bill No.</th>
                    <th style={{ padding: '10px 16px', textAlign: 'right', fontWeight: 700, color: 'var(--text-secondary)' }}>Amount</th>
                    <th style={{ padding: '10px 16px', textAlign: 'right', fontWeight: 700, color: 'var(--text-secondary)' }}>Balance Due</th>
                    <th style={{ padding: '10px 16px', textAlign: 'center', fontWeight: 700, color: 'var(--text-secondary)' }}>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {bills.map(b => (
                    <tr key={b.id} style={{ borderBottom: '1px solid var(--border)' }}>
                      <td style={{ padding: '9px 16px', color: 'var(--text-muted)' }}>{formatDate(b.purchase_date)}</td>
                      <td style={{ padding: '9px 16px', fontWeight: 600 }}>{b.vendor_name}</td>
                      <td style={{ padding: '9px 16px' }}>{b.bill_number || '—'}</td>
                      <td style={{ padding: '9px 16px', textAlign: 'right', fontWeight: 600 }}>{formatCurrency(b.amount)}</td>
                      <td style={{ padding: '9px 16px', textAlign: 'right', fontWeight: 700, color: Number(b.balance_due) > 0 ? 'var(--danger)' : 'var(--success)' }}>
                        {Number(b.balance_due) > 0 ? formatCurrency(b.balance_due) : '—'}
                      </td>
                      <td style={{ padding: '9px 16px', textAlign: 'center' }}>
                        <span style={{ fontSize: 11, fontWeight: 700, padding: '3px 8px', borderRadius: 6,
                          background: b.is_paid ? 'rgba(34,197,94,0.12)' : 'rgba(239,68,68,0.12)',
                          color: b.is_paid ? 'var(--success)' : 'var(--danger)' }}>
                          {b.is_paid ? 'PAID' : 'UNPAID'}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Payments Tab */}
      {tab === 'payments' && (
        <div style={{ padding: '0 20px', marginTop: 8 }}>
          <div style={{ display: 'flex', gap: 8, marginBottom: 12, alignItems: 'center' }}>
            <select value={selectedVendor?.id || ''} onChange={e => {
              const v = vendors.find(v => v.id === Number(e.target.value));
              setSelectedVendor(v || null);
            }} style={{ flex: 1, background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 12, padding: '8px 12px', fontSize: 13 }}>
              <option value="">All Vendors</option>
              {vendors.map(v => <option key={v.id} value={v.id}>{v.name}</option>)}
            </select>
            <button onClick={() => setShowAddPayment(true)}
              style={{ background: 'var(--success)', color: 'white', border: 'none', borderRadius: 10, padding: '8px 14px', fontWeight: 700, cursor: 'pointer', fontSize: 13 }}>
              + Record Payment
            </button>
          </div>

          {vendorPayments.length === 0 ? (
            <div className="empty-state"><p>No outgoing payments recorded</p></div>
          ) : (
            <div style={{ background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 'var(--radius-lg)', overflow: 'hidden' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                <thead>
                  <tr style={{ background: 'var(--bg-elevated)', borderBottom: '2px solid var(--border)' }}>
                    <th style={{ padding: '10px 16px', textAlign: 'left', fontWeight: 700, color: 'var(--text-secondary)' }}>Date</th>
                    <th style={{ padding: '10px 16px', textAlign: 'left', fontWeight: 700, color: 'var(--text-secondary)' }}>Vendor</th>
                    <th style={{ padding: '10px 16px', textAlign: 'left', fontWeight: 700, color: 'var(--text-secondary)' }}>Mode</th>
                    <th style={{ padding: '10px 16px', textAlign: 'right', fontWeight: 700, color: 'var(--text-secondary)' }}>Amount</th>
                    <th style={{ padding: '10px 16px', textAlign: 'left', fontWeight: 700, color: 'var(--text-secondary)' }}>Note</th>
                  </tr>
                </thead>
                <tbody>
                  {vendorPayments.map(p => (
                    <tr key={p.id} style={{ borderBottom: '1px solid var(--border)' }}>
                      <td style={{ padding: '9px 16px', color: 'var(--text-muted)' }}>{formatDate(p.payment_date)}</td>
                      <td style={{ padding: '9px 16px', fontWeight: 600 }}>{p.vendor_name}</td>
                      <td style={{ padding: '9px 16px' }}>{(p.mode || 'cash').toUpperCase()}</td>
                      <td style={{ padding: '9px 16px', textAlign: 'right', fontWeight: 700, color: 'var(--success)' }}>{formatCurrency(p.amount)}</td>
                      <td style={{ padding: '9px 16px', color: 'var(--text-muted)', fontSize: 12 }}>{p.note || '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Add Vendor Modal */}
      {showAddVendor && (
        <AddVendorModal onClose={() => setShowAddVendor(false)} onSuccess={() => { setShowAddVendor(false); qc.invalidateQueries({ queryKey: ['vendors'] }); }} />
      )}

      {/* Add Bill Modal */}
      {showAddBill && (
        <AddBillModal vendors={vendors} defaultVendor={selectedVendor} onClose={() => setShowAddBill(false)} onSuccess={() => { setShowAddBill(false); qc.invalidateQueries(); }} />
      )}

      {/* Add Payment Modal */}
      {showAddPayment && (
        <AddPaymentModal vendors={vendors} defaultVendor={selectedVendor} onClose={() => setShowAddPayment(false)} onSuccess={() => { setShowAddPayment(false); qc.invalidateQueries(); }} />
      )}
    </div>
  );
}

// ── Modals ───────────────────────────────────────────────────────────────────

function AddVendorModal({ onClose, onSuccess }: { onClose: () => void; onSuccess: () => void }) {
  const [form, setForm] = useState({ name: '', phone: '', city: '', tag: 'Supplier', notes: '' });
  const [loading, setLoading] = useState(false);

  const submit = async () => {
    if (!form.name) return;
    setLoading(true);
    try {
      await api.post(`${API}/vendors`, form);
      onSuccess();
    } finally { setLoading(false); }
  };

  return (
    <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)', zIndex: 1000, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 16 }}>
      <div style={{ background: 'var(--bg-card)', borderRadius: 20, padding: 24, width: '100%', maxWidth: 440 }}>
        <h3 style={{ fontSize: 18, fontWeight: 800, marginBottom: 20 }}>Add Vendor</h3>
        {[
          { label: 'Name *', key: 'name', placeholder: 'Vendor / KARIGAR name' },
          { label: 'Phone', key: 'phone', placeholder: '+91 9876543210' },
          { label: 'City', key: 'city', placeholder: 'Surat / Bhavnagar...' },
          { label: 'Notes', key: 'notes', placeholder: 'Any notes...' },
        ].map(({ label, key, placeholder }) => (
          <div key={key} style={{ marginBottom: 12 }}>
            <label style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: 0.5 }}>{label}</label>
            <input className="form-input" placeholder={placeholder} value={(form as any)[key]}
              onChange={e => setForm(f => ({ ...f, [key]: e.target.value }))} style={{ marginTop: 4 }} />
          </div>
        ))}
        <div style={{ marginBottom: 20 }}>
          <label style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase' }}>Type</label>
          <select className="form-input" value={form.tag} onChange={e => setForm(f => ({ ...f, tag: e.target.value }))} style={{ marginTop: 4 }}>
            <option value="Supplier">Supplier</option>
            <option value="KARIGAR">KARIGAR</option>
            <option value="Other">Other</option>
          </select>
        </div>
        <div style={{ display: 'flex', gap: 10 }}>
          <button onClick={onClose} style={{ flex: 1, padding: 12, borderRadius: 12, border: '1px solid var(--border)', background: 'none', fontWeight: 600, cursor: 'pointer' }}>Cancel</button>
          <button onClick={submit} disabled={loading || !form.name}
            style={{ flex: 2, padding: 12, borderRadius: 12, background: 'var(--accent)', color: 'white', border: 'none', fontWeight: 700, cursor: 'pointer' }}>
            {loading ? 'Saving…' : 'Add Vendor'}
          </button>
        </div>
      </div>
    </div>
  );
}

function AddBillModal({ vendors, defaultVendor, onClose, onSuccess }: { vendors: Vendor[]; defaultVendor: Vendor | null; onClose: () => void; onSuccess: () => void }) {
  const today = new Date().toISOString().split('T')[0];
  const [form, setForm] = useState({ vendor_id: defaultVendor?.id || '', bill_number: '', amount: '', purchase_date: today, description: '' });
  const [loading, setLoading] = useState(false);

  const submit = async () => {
    if (!form.vendor_id || !form.amount) return;
    setLoading(true);
    try {
      await api.post(`${API}/bills`, { ...form, vendor_id: Number(form.vendor_id), amount: Number(form.amount) });
      onSuccess();
    } finally { setLoading(false); }
  };

  return (
    <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)', zIndex: 1000, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 16 }}>
      <div style={{ background: 'var(--bg-card)', borderRadius: 20, padding: 24, width: '100%', maxWidth: 440 }}>
        <h3 style={{ fontSize: 18, fontWeight: 800, marginBottom: 20 }}>Add Purchase Bill</h3>
        <div style={{ marginBottom: 12 }}>
          <label style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase' }}>Vendor *</label>
          <select className="form-input" value={form.vendor_id} onChange={e => setForm(f => ({ ...f, vendor_id: e.target.value }))} style={{ marginTop: 4 }}>
            <option value="">Select vendor…</option>
            {vendors.map(v => <option key={v.id} value={v.id}>{v.name}</option>)}
          </select>
        </div>
        {[
          { label: 'Bill No.', key: 'bill_number', placeholder: 'Supplier bill number', type: 'text' },
          { label: 'Amount *', key: 'amount', placeholder: '0.00', type: 'number' },
          { label: 'Date *', key: 'purchase_date', placeholder: '', type: 'date' },
          { label: 'Description', key: 'description', placeholder: 'Goods / work description', type: 'text' },
        ].map(({ label, key, placeholder, type }) => (
          <div key={key} style={{ marginBottom: 12 }}>
            <label style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase' }}>{label}</label>
            <input className="form-input" type={type} placeholder={placeholder} value={(form as any)[key]}
              onChange={e => setForm(f => ({ ...f, [key]: e.target.value }))} style={{ marginTop: 4 }} />
          </div>
        ))}
        <div style={{ display: 'flex', gap: 10, marginTop: 8 }}>
          <button onClick={onClose} style={{ flex: 1, padding: 12, borderRadius: 12, border: '1px solid var(--border)', background: 'none', fontWeight: 600, cursor: 'pointer' }}>Cancel</button>
          <button onClick={submit} disabled={loading || !form.vendor_id || !form.amount}
            style={{ flex: 2, padding: 12, borderRadius: 12, background: 'var(--accent)', color: 'white', border: 'none', fontWeight: 700, cursor: 'pointer' }}>
            {loading ? 'Saving…' : 'Add Bill'}
          </button>
        </div>
      </div>
    </div>
  );
}

function AddPaymentModal({ vendors, defaultVendor, onClose, onSuccess }: { vendors: Vendor[]; defaultVendor: Vendor | null; onClose: () => void; onSuccess: () => void }) {
  const today = new Date().toISOString().split('T')[0];
  const [form, setForm] = useState({ vendor_id: defaultVendor?.id || '', amount: '', payment_date: today, mode: 'cash', note: '' });
  const [loading, setLoading] = useState(false);

  const submit = async () => {
    if (!form.vendor_id || !form.amount) return;
    setLoading(true);
    try {
      await api.post(`${API}/payments`, { ...form, vendor_id: Number(form.vendor_id), amount: Number(form.amount) });
      onSuccess();
    } finally { setLoading(false); }
  };

  return (
    <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)', zIndex: 1000, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 16 }}>
      <div style={{ background: 'var(--bg-card)', borderRadius: 20, padding: 24, width: '100%', maxWidth: 440 }}>
        <h3 style={{ fontSize: 18, fontWeight: 800, marginBottom: 20 }}>Record Outgoing Payment</h3>
        <div style={{ marginBottom: 12 }}>
          <label style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase' }}>Vendor *</label>
          <select className="form-input" value={form.vendor_id} onChange={e => setForm(f => ({ ...f, vendor_id: e.target.value }))} style={{ marginTop: 4 }}>
            <option value="">Select vendor…</option>
            {vendors.map(v => <option key={v.id} value={v.id}>{v.name}</option>)}
          </select>
        </div>
        {[
          { label: 'Amount *', key: 'amount', placeholder: '0.00', type: 'number' },
          { label: 'Date *', key: 'payment_date', placeholder: '', type: 'date' },
          { label: 'Note', key: 'note', placeholder: 'Payment note...', type: 'text' },
        ].map(({ label, key, placeholder, type }) => (
          <div key={key} style={{ marginBottom: 12 }}>
            <label style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase' }}>{label}</label>
            <input className="form-input" type={type} placeholder={placeholder} value={(form as any)[key]}
              onChange={e => setForm(f => ({ ...f, [key]: e.target.value }))} style={{ marginTop: 4 }} />
          </div>
        ))}
        <div style={{ marginBottom: 20 }}>
          <label style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase' }}>Mode</label>
          <select className="form-input" value={form.mode} onChange={e => setForm(f => ({ ...f, mode: e.target.value }))} style={{ marginTop: 4 }}>
            <option value="cash">Cash</option>
            <option value="upi">UPI</option>
            <option value="bank">Bank Transfer</option>
            <option value="cheque">Cheque</option>
          </select>
        </div>
        <div style={{ display: 'flex', gap: 10 }}>
          <button onClick={onClose} style={{ flex: 1, padding: 12, borderRadius: 12, border: '1px solid var(--border)', background: 'none', fontWeight: 600, cursor: 'pointer' }}>Cancel</button>
          <button onClick={submit} disabled={loading || !form.vendor_id || !form.amount}
            style={{ flex: 2, padding: 12, borderRadius: 12, background: 'var(--success)', color: 'white', border: 'none', fontWeight: 700, cursor: 'pointer' }}>
            {loading ? 'Saving…' : 'Record Payment'}
          </button>
        </div>
      </div>
    </div>
  );
}
