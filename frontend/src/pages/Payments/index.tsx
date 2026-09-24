import { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useNavigate, useSearchParams, useParams } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { paymentsApi, partiesApi, invoicesApi } from '../../api/endpoints';
import { formatCurrency, formatDate } from '../../utils/format';
import { SearchCombobox } from '../../components/SearchCombobox';
import type { ComboboxOption } from '../../components/SearchCombobox';
import { SecureActionModal } from '../../components/SecureActionModal';
import { Search, X, Plus, ChevronLeft, Edit2, Receipt } from 'lucide-react';
import { generateAndSharePaymentReceipt } from '../../utils/pdfGenerator';

const schema = z.object({
  party_id: z.coerce.number().min(1, 'Select a party'),
  amount: z.coerce.number().positive('Must be > 0'),
  payment_date: z.string().min(1, 'Date required'),
  note: z.string().optional(),
  mode: z.enum(['cash', 'upi', 'bank', 'cheque']).default('cash'),
});
type PaymentForm = z.infer<typeof schema>;

const editSchema = z.object({
  payment_date: z.string().min(1, 'Date required'),
  note: z.string().optional(),
  mode: z.enum(['cash', 'upi', 'bank', 'cheque']),
});
type EditPaymentForm = z.infer<typeof editSchema>;

// ── Payments List ─────────────────────────────────────────────────────────────
export function PaymentsList() {
  const navigate = useNavigate();
  const [search, setSearch] = useState('');
  const [dateFilter, setDateFilter] = useState<'all' | 'today' | 'week' | 'month' | 'custom'>('all');
  const [customFrom, setCustomFrom] = useState('');
  const [customTo, setCustomTo] = useState('');
  const [page, setPage] = useState(0);
  const PAGE_SIZE = 20;

  useEffect(() => { setPage(0); }, [search, dateFilter, customFrom, customTo]);

  function getDateRange(f: string): { from: string; to: string } | null {
    const now = new Date();
    const pad = (n: number) => String(n).padStart(2, '0');
    const fmt = (d: Date) => d.getFullYear() + '-' + pad(d.getMonth() + 1) + '-' + pad(d.getDate());
    if (f === 'today') { const t = fmt(now); return { from: t, to: t }; }
    if (f === 'week') { const s = new Date(now); s.setDate(now.getDate() - now.getDay()); return { from: fmt(s), to: fmt(now) }; }
    if (f === 'month') { return { from: fmt(new Date(now.getFullYear(), now.getMonth(), 1)), to: fmt(now) }; }
    return null;
  }

  const dateRange = dateFilter === 'custom'
    ? (customFrom || customTo ? { from: customFrom, to: customTo } : null)
    : getDateRange(dateFilter);

  const { data, isLoading } = useQuery({
    queryKey: ['payments', search, dateFilter, customFrom, customTo, page],
    queryFn: () => paymentsApi.list(undefined, search, page * PAGE_SIZE, PAGE_SIZE, dateRange?.from, dateRange?.to ? dateRange.to + 'T23:59:59' : undefined).then(r => r.data),
  });

  const payments = data?.items || [];
  const totalCount = data?.total || 0;
  const summaryTotal = data?.summary_total || 0;
  const totalPages = Math.ceil(totalCount / PAGE_SIZE);

  const DATE_CHIPS = [
    { id: 'all' as const, label: 'All Time' },
    { id: 'today' as const, label: 'Today' },
    { id: 'week' as const, label: 'This Week' },
    { id: 'month' as const, label: 'This Month' },
    { id: 'custom' as const, label: 'Custom' },
  ];

  return (
    <div className="page-content">
      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div><h1 className="page-title">Payments</h1><p className="page-subtitle">{totalCount} received</p></div>
        <p style={{ fontSize: 14, fontWeight: 700, color: 'var(--success)' }}>Total: {formatCurrency(summaryTotal)}</p>
      </div>

      <div className="search-bar" style={{ marginBottom: 12 }}>
        <Search size={16} />
        <input placeholder="Search party name…" value={search} onChange={e => setSearch(e.target.value)} />
        {search && <button onClick={() => setSearch('')} style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}><X size={14} /></button>}
      </div>

      {/* F17: Date filter chips */}
      <div style={{ display: 'flex', gap: 6, overflowX: 'auto', padding: '0 20px 12px', scrollbarWidth: 'none' }}>
        {DATE_CHIPS.map(chip => (
          <button key={chip.id} onClick={() => setDateFilter(chip.id)} style={{ flexShrink: 0, padding: '5px 12px', borderRadius: 20, border: `1px solid ${dateFilter === chip.id ? 'var(--accent)' : 'var(--border)'}`, background: dateFilter === chip.id ? 'var(--accent-glow)' : 'transparent', color: dateFilter === chip.id ? 'var(--accent)' : 'var(--text-muted)', fontSize: 12, fontWeight: dateFilter === chip.id ? 600 : 400, cursor: 'pointer', whiteSpace: 'nowrap' }}>
            {chip.label}
          </button>
        ))}
      </div>
      {dateFilter === 'custom' && (
        <div style={{ display: 'flex', gap: 8, padding: '0 20px', marginBottom: 12 }}>
          <input className="form-input" type="date" value={customFrom} onChange={e => setCustomFrom(e.target.value)} style={{ flex: 1, padding: '8px 10px', fontSize: 13 }} />
          <input className="form-input" type="date" value={customTo} onChange={e => setCustomTo(e.target.value)} style={{ flex: 1, padding: '8px 10px', fontSize: 13 }} />
        </div>
      )}

      {isLoading ? (
        <div className="loading-screen"><div className="spinner" /></div>
      ) : payments.length === 0 ? (
        <div className="empty-state"><Plus size={48} /><h3>No payments yet</h3><p>Record your first payment to track collections</p></div>
      ) : (
        <div className="list-container">
          {payments.map((p: any) => (
            <div key={p.id} className="list-item" onClick={() => navigate(`/payments/${p.id}`)}>
              <div className="list-item-icon" style={{ background: 'var(--success-bg)' }}>💰</div>
              <div className="list-item-body">
                <p 
                  className="list-item-title party-link" 
                  onClick={(e) => { e.stopPropagation(); navigate(`/parties/${p.party_id}`); }}
                >
                  {p.party_name}
                </p>
                <p className="list-item-sub">PMT-{String(p.id).padStart(4, '0')} · {formatDate(p.payment_date)} · {(p.mode || 'cash').toUpperCase()}</p>
                {p.note && <p className="list-item-sub" style={{ fontSize: 11 }}>{p.note}</p>}
              </div>
              <div className="list-item-right">
                <p style={{ fontWeight: 700, fontSize: 15, color: 'var(--success)' }}>{formatCurrency(p.amount)}</p>
                {Number(p.unallocated) > 0 && <span className="badge badge-accent" style={{ marginTop: 4, fontSize: 10 }}>On Acct {formatCurrency(p.unallocated)}</span>}
              </div>
            </div>
          ))}
          {/* Pagination */}
          {totalPages > 1 && (
            <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: 12, padding: '20px 0' }}>
              <button className="btn btn-sm btn-secondary" disabled={page === 0} onClick={() => setPage(p => p - 1)}>← Prev</button>
              <span style={{ fontSize: 13, color: 'var(--text-secondary)' }}>Page {page + 1} of {totalPages}</span>
              <button className="btn btn-sm btn-secondary" disabled={page >= totalPages - 1} onClick={() => setPage(p => p + 1)}>Next →</button>
            </div>
          )}
        </div>
      )}

      <button className="fab" onClick={() => navigate('/payments/new')}><Plus size={24} /></button>
    </div>
  );
}

// ── New Payment Form ──────────────────────────────────────────────────────────
export function NewPayment() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const qc = useQueryClient();
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState('');
  const [paymentType, setPaymentType] = useState<'on_account' | 'bill_adjustment'>('on_account');
  const [unpaidInvoices, setUnpaidInvoices] = useState<any[]>([]);
  const [allocations, setAllocations] = useState<{ [invoiceId: number]: number }>({});
  const [draftAllocations, setDraftAllocations] = useState<{ [invoiceId: number]: string }>({});

  const today = new Date().toISOString().split('T')[0];
  // F8: Pre-fill from invoice quick-settle link
  const prefilledInvoiceId = searchParams.get('invoice') ? Number(searchParams.get('invoice')) : null;
  const prefilledAmount = searchParams.get('amount') ? Number(searchParams.get('amount')) : undefined;

  const { register, handleSubmit, watch, setValue, formState: { errors } } = useForm<PaymentForm>({
    resolver: zodResolver(schema),
    defaultValues: {
      party_id: searchParams.get('party') ? Number(searchParams.get('party')) : undefined,
      payment_date: today,
      mode: 'cash',
      amount: prefilledAmount,
    },
  });

  const selectedParty = watch('party_id');
  const enteredAmount = watch('amount') || 0;
  const [partySearch, setPartySearch] = useState('');
  const { data: parties = [] } = useQuery({ queryKey: ['parties', partySearch], queryFn: () => partiesApi.list(partySearch, 0, 100).then(r => r.data.items) });
  const partyOptions: ComboboxOption[] = (Array.isArray(parties) ? parties : []).map((p: any) => ({ value: p.id, label: p.name, sublabel: `Due: ${Number(p.outstanding || 0).toLocaleString('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 })}` }));

  useEffect(() => {
    if (selectedParty && paymentType === 'bill_adjustment') {
      invoicesApi.list(Number(selectedParty), true, undefined, 0, 1000).then(r => {
        const sorted = r.data.items.sort((a: any, b: any) => new Date(a.invoice_date).getTime() - new Date(b.invoice_date).getTime());
        setUnpaidInvoices(sorted);
        // F8: Auto-allocate to pre-filled invoice
        if (prefilledInvoiceId && prefilledAmount) {
          const inv = sorted.find((i: any) => i.id === prefilledInvoiceId);
          if (inv) setAllocations({ [prefilledInvoiceId]: Math.min(prefilledAmount, Number(inv.balance_due)) });
        } else {
          setAllocations({});
        }
        setDraftAllocations({});
      });
    }
  }, [selectedParty, paymentType]);

  // F8: Auto-switch to bill_adjustment if invoice param present
  useEffect(() => {
    if (prefilledInvoiceId) setPaymentType('bill_adjustment');
  }, [prefilledInvoiceId]);

  const handleAllocationChange = (invoiceId: number, value: string, maxLimit: number) => {
    let n = Number(value);
    if (n < 0) n = 0;
    if (n > maxLimit) n = maxLimit;
    setAllocations(prev => ({ ...prev, [invoiceId]: n }));
  };

  const totalAllocated = Object.values(allocations).reduce((s, v) => s + (v || 0), 0);

  const onSubmit = async (data: PaymentForm) => {
    if (loading) return;
    setLoading(true); setErr('');
    if (paymentType === 'bill_adjustment' && totalAllocated > Number(data.amount)) {
      setErr('Total allocated cannot exceed payment amount.');
      setLoading(false); return;
    }
    try {
      const payload: any = { ...data, payment_date: new Date(data.payment_date).toISOString() };
      if (paymentType === 'bill_adjustment') {
        const finalAllocations = { ...allocations };
        Object.entries(draftAllocations).forEach(([idStr, val]) => {
          const invId = Number(idStr);
          if (val !== '') {
            const inv = unpaidInvoices.find(i => i.id === invId);
            if (inv) { let n = Number(val); if (n < 0) n = 0; if (n > Number(inv.balance_due)) n = Number(inv.balance_due); finalAllocations[invId] = n; }
          }
        });
        payload.allocations = Object.entries(finalAllocations).filter(([_, a]) => a > 0).map(([invoice_id, amount]) => ({ invoice_id: Number(invoice_id), allocated_amount: amount }));
      }
      await paymentsApi.create(payload);
      qc.invalidateQueries();
      navigate(-1);
    } catch (e: any) {
      setErr(e.response?.data?.detail || 'Failed to record payment');
    } finally { setLoading(false); }
  };

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', background: 'var(--bg-base)' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '20px 20px 16px', borderBottom: '1px solid var(--border)' }}>
        <button className="btn-icon btn" onClick={() => navigate(-1)}><ChevronLeft size={20} /></button>
        <h1 className="page-title">Record Payment</h1>
      </div>
      <div className="page-content" style={{ paddingTop: 20, paddingLeft: 20, paddingRight: 20 }}>
        {err && <div style={{ color: 'var(--danger)', fontSize: 13, marginBottom: 12 }}>{err}</div>}
        <form onSubmit={handleSubmit(onSubmit)}>
          <div className="form-group">
            <label className="form-label">Party *</label>
            <SearchCombobox value={selectedParty || null} placeholder="Select party…" options={partyOptions} onChange={opt => setValue('party_id', Number(opt.value))} onSearch={setPartySearch} />
            {errors.party_id && <span className="form-error">{errors.party_id.message}</span>}
          </div>
          <div className="form-group">
            <label className="form-label">Amount Received (₹) *</label>
            <input className="form-input" type="number" step="0.01" placeholder="0.00" {...register('amount')} />
            {errors.amount && <span className="form-error">{errors.amount.message}</span>}
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
            <div className="form-group"><label className="form-label">Date *</label><input className="form-input" type="date" {...register('payment_date')} /></div>
            <div className="form-group">
              <label className="form-label">Mode</label>
              <select className="form-select" {...register('mode')}>
                <option value="cash">Cash</option>
                <option value="upi">UPI</option>
                <option value="bank">Bank Transfer</option>
                <option value="cheque">Cheque</option>
              </select>
            </div>
          </div>
          <div className="form-group" style={{ marginBottom: 24 }}>
            <label className="form-label">Note</label>
            <input className="form-input" placeholder="Reference / note…" {...register('note')} />
          </div>

          <div style={{ display: 'flex', gap: 10, marginBottom: 20 }}>
            <button type="button" style={{ flex: 1, padding: 12, borderRadius: 'var(--radius-md)', border: `1px solid ${paymentType === 'on_account' ? 'var(--accent)' : 'var(--border)'}`, background: paymentType === 'on_account' ? 'var(--accent-glow)' : 'var(--bg-elevated)', color: paymentType === 'on_account' ? 'var(--accent)' : 'var(--text-secondary)', fontWeight: paymentType === 'on_account' ? 600 : 400 }} onClick={() => setPaymentType('on_account')}>On Account</button>
            <button type="button" style={{ flex: 1, padding: 12, borderRadius: 'var(--radius-md)', border: `1px solid ${paymentType === 'bill_adjustment' ? 'var(--accent)' : 'var(--border)'}`, background: paymentType === 'bill_adjustment' ? 'var(--accent-glow)' : 'var(--bg-elevated)', color: paymentType === 'bill_adjustment' ? 'var(--accent)' : 'var(--text-secondary)', fontWeight: paymentType === 'bill_adjustment' ? 600 : 400 }} onClick={() => setPaymentType('bill_adjustment')}>Bill Adjustment</button>
          </div>

          {paymentType === 'bill_adjustment' && selectedParty && (
            <div style={{ background: 'var(--bg-elevated)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border)', padding: 14, marginBottom: 20 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
                <p style={{ fontSize: 13, fontWeight: 600, color: 'var(--text)' }}>Select Bills to Settle</p>
                <div style={{ fontSize: 12, textAlign: 'right' }}>
                  <p style={{ color: 'var(--text-secondary)' }}>Remaining to Allocate:</p>
                  <p style={{ color: (enteredAmount - totalAllocated) < 0 ? 'var(--danger)' : 'var(--success)', fontWeight: 700, fontSize: 14 }}>{formatCurrency(enteredAmount - totalAllocated)}</p>
                </div>
              </div>
              {unpaidInvoices.length === 0 ? (
                <p style={{ fontSize: 13, color: 'var(--text-muted)' }}>No pending bills for this party.</p>
              ) : (
                unpaidInvoices.map((inv: any) => (
                  <div key={inv.id} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px 0', borderBottom: '1px solid var(--border)', fontSize: 13 }}>
                    <div>
                      <span style={{ color: 'var(--text)', fontWeight: 500, display: 'block' }}>{inv.invoice_number}</span>
                      <span style={{ color: 'var(--text-secondary)', fontSize: 12 }}>Due: {formatCurrency(inv.balance_due)}</span>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <input type="number" className="form-input" style={{ width: 100, padding: '6px 10px', fontSize: 13 }} placeholder="0.00" value={draftAllocations[inv.id] !== undefined ? draftAllocations[inv.id] : (allocations[inv.id] || '')} onChange={e => setDraftAllocations(prev => ({ ...prev, [inv.id]: e.target.value }))} />
                      <button type="button" className="btn btn-sm" style={{ background: allocations[inv.id] > 0 ? 'var(--success)' : 'var(--accent)', color: 'white', padding: '4px 12px' }} onClick={() => { const val = draftAllocations[inv.id]; if (val !== undefined) { handleAllocationChange(inv.id, val, Number(inv.balance_due)); setDraftAllocations(prev => { const n = { ...prev }; delete n[inv.id]; return n; }); } }}>OK</button>
                    </div>
                  </div>
                ))
              )}
            </div>
          )}
          {paymentType === 'on_account' && <p style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 20, textAlign: 'center' }}>This payment will be saved to the party's account and can be applied to invoices later.</p>}

          <button type="submit" className="btn btn-success btn-full" disabled={loading || (paymentType === 'bill_adjustment' && enteredAmount > 0 && totalAllocated > Number(enteredAmount))}>
            {loading ? 'Processing…' : 'Record Payment'}
          </button>
        </form>
      </div>
    </div>
  );
}

// ── Payment Detail ─────────────────────────────────────────────────────────────
export function PaymentDetail() {
  const navigate = useNavigate();
  const { id } = useParams<{ id: string }>();
  const qc = useQueryClient();
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [deleteReason, setDeleteReason] = useState('Entry Error');
  const [showAllocateModal, setShowAllocateModal] = useState(false);

  const { data: payment, isLoading } = useQuery({
    queryKey: ['payment', id],
    queryFn: () => paymentsApi.get(Number(id)).then(r => r.data),
  });

  const { data: party } = useQuery({
    queryKey: ['party', payment?.party_id],
    queryFn: () => partiesApi.get(payment!.party_id).then(r => r.data),
    enabled: !!payment,
  });

  if (isLoading) return <div className="loading-screen"><div className="spinner" /></div>;
  if (!payment) return null;

  const DELETE_REASONS = ['Entry Error', 'Cheque Bounce', 'Payment Cancelled', 'Duplicate Entry', 'Other'];

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', background: 'var(--bg-base)' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '20px 20px 16px', borderBottom: '1px solid var(--border)' }}>
        <button className="btn-icon btn" onClick={() => navigate(-1)}><ChevronLeft size={20} /></button>
        <h1 className="page-title" style={{ flex: 1 }}>Payment Detail</h1>
        {/* F11: Share receipt */}
        <button className="btn-icon" title="Share receipt" style={{ color: 'var(--accent)' }} onClick={() => generateAndSharePaymentReceipt(payment, party)}><Receipt size={18} /></button>
        {/* F13: Edit button */}
        <button className="btn-icon" title="Edit payment" style={{ color: 'var(--accent)' }} onClick={() => setShowEditModal(true)}><Edit2 size={18} /></button>
      </div>

      <div className="page-content" style={{ paddingTop: 20, paddingLeft: 20, paddingRight: 20 }}>
        <div className="hero-card" style={{ margin: 0, marginBottom: 16 }}>
          <p className="hero-label">Amount Received</p>
          <p className="hero-amount">{formatCurrency(payment.amount)}</p>
          <p className="hero-sub">{formatDate(payment.payment_date)} · {(payment.mode || 'cash').toUpperCase()}</p>
          {payment.note && <p className="hero-sub" style={{ marginTop: 4 }}>{payment.note}</p>}
          <p className="hero-sub" style={{ marginTop: 4 }}>PMT-{String(payment.id).padStart(4, '0')} · {party?.name}</p>
        </div>

        {/* F14: Unallocated with Allocate button */}
        {Number(payment.unallocated) > 0 && (
          <div style={{ background: 'var(--accent-glow)', borderRadius: 10, padding: '12px 14px', marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div>
              <p style={{ fontSize: 12, color: 'var(--accent)', fontWeight: 600 }}>Unallocated / On Account</p>
              <p style={{ fontSize: 16, fontWeight: 700, color: 'var(--accent)' }}>{formatCurrency(payment.unallocated)}</p>
            </div>
            <button className="btn btn-sm" style={{ background: 'var(--accent)', color: 'white' }} onClick={() => setShowAllocateModal(true)}>Allocate</button>
          </div>
        )}

        {/* F20: Allocated invoices as tappable links */}
        {payment.allocations?.length > 0 && (
          <>
            <p className="section-label" style={{ padding: '0 0 8px' }}>Allocated Towards Bills</p>
            <div style={{ background: 'var(--bg-elevated)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border)', padding: '0 14px', marginBottom: 16 }}>
              {payment.allocations.map((a: any, i: number) => (
                <div key={a.invoice_id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '12px 0', borderBottom: i < payment.allocations.length - 1 ? '1px solid var(--border)' : 'none', fontSize: 14 }}>
                  {/* F20: Tappable invoice link */}
                  <button onClick={() => navigate(`/invoices/${a.invoice_id}`)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--accent)', fontWeight: 600, fontSize: 14, padding: 0, textAlign: 'left' }}>
                    {a.invoice_number}
                  </button>
                  <p style={{ color: 'var(--success)', fontWeight: 700 }}>{formatCurrency(a.allocated_amount)}</p>
                </div>
              ))}
            </div>
          </>
        )}

        {/* F9: Delete with reason */}
        <button
          className="btn btn-secondary"
          style={{ width: '100%', color: 'var(--danger)', borderColor: 'var(--danger)', marginTop: 8 }}
          onClick={() => setShowDeleteModal(true)}
        >
          <X size={16} /> Delete / Reverse Payment
        </button>
      </div>

      {/* F9: Delete modal with reason dropdown */}
      {showDeleteModal && (
        <div className="modal-overlay" onClick={() => setShowDeleteModal(false)}>
          <div className="modal-sheet" onClick={e => e.stopPropagation()}>
            <div className="modal-handle" />
            <h2 className="modal-title">Delete Payment</h2>
            <p style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 16 }}>Enter Master PIN to confirm. Invoice balances will be recalibrated.</p>
            <div className="form-group" style={{ marginBottom: 16 }}>
              <label className="form-label">Reason for Deletion</label>
              <select className="form-select" value={deleteReason} onChange={e => setDeleteReason(e.target.value)}>
                {DELETE_REASONS.map(r => <option key={r} value={r}>{r}</option>)}
              </select>
            </div>
            <SecureActionModal
              isOpen={true}
              onClose={() => setShowDeleteModal(false)}
              title="Confirm Delete Payment"
              message={`Reason: ${deleteReason}. This will reverse all allocations.`}
              onConfirm={async () => {
                await paymentsApi.delete(Number(id), deleteReason);
                qc.invalidateQueries();
                setShowDeleteModal(false);
                navigate(-1);
              }}
            />
          </div>
        </div>
      )}

      {/* F13: Edit modal */}
      {showEditModal && <EditPaymentModal payment={payment} onClose={() => setShowEditModal(false)} onSuccess={() => { setShowEditModal(false); qc.invalidateQueries({ queryKey: ['payment', id] }); }} />}

      {/* F14: Allocate modal */}
      {showAllocateModal && party && (
        <AllocateFromPaymentModal
          payment={payment}
          partyId={payment.party_id}
          onClose={() => setShowAllocateModal(false)}
          onSuccess={() => { setShowAllocateModal(false); qc.invalidateQueries(); }}
        />
      )}
    </div>
  );
}

// ── F13: Edit Payment Modal ───────────────────────────────────────────────────
function EditPaymentModal({ payment, onClose, onSuccess }: { payment: any; onClose: () => void; onSuccess: () => void }) {
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState('');
  const { register, handleSubmit, formState: { errors } } = useForm<EditPaymentForm>({
    resolver: zodResolver(editSchema),
    defaultValues: {
      payment_date: payment.payment_date?.split('T')[0] || '',
      mode: payment.mode || 'cash',
      note: payment.note || '',
    },
  });

  const onSubmit = async (data: EditPaymentForm) => {
    setLoading(true); setErr('');
    try {
      await paymentsApi.update(payment.id, { ...data, payment_date: new Date(data.payment_date).toISOString() });
      onSuccess();
    } catch (e: any) {
      setErr(e.response?.data?.detail || 'Failed to update');
    } finally { setLoading(false); }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-sheet" onClick={e => e.stopPropagation()}>
        <div className="modal-handle" />
        <h2 className="modal-title">Edit Payment</h2>
        <p style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 16 }}>Amount cannot be changed — delete and re-record to correct amount.</p>
        {err && <div style={{ color: 'var(--danger)', fontSize: 13, marginBottom: 8 }}>{err}</div>}
        <form onSubmit={handleSubmit(onSubmit)}>
          <div className="form-group"><label className="form-label">Date *</label><input className="form-input" type="date" {...register('payment_date')} />{errors.payment_date && <span className="form-error">{errors.payment_date.message}</span>}</div>
          <div className="form-group">
            <label className="form-label">Mode</label>
            <select className="form-select" {...register('mode')}>
              <option value="cash">Cash</option>
              <option value="upi">UPI</option>
              <option value="bank">Bank Transfer</option>
              <option value="cheque">Cheque</option>
            </select>
          </div>
          <div className="form-group"><label className="form-label">Note</label><input className="form-input" placeholder="Reference / note…" {...register('note')} /></div>
          <div style={{ display: 'flex', gap: 10 }}>
            <button type="button" className="btn btn-secondary" style={{ flex: 1 }} onClick={onClose}>Cancel</button>
            <button type="submit" className="btn btn-primary" style={{ flex: 1 }} disabled={loading}>{loading ? 'Saving…' : 'Save Changes'}</button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ── F14: Allocate From Payment Modal ─────────────────────────────────────────
function AllocateFromPaymentModal({ payment, partyId, onClose, onSuccess }: { payment: any; partyId: number; onClose: () => void; onSuccess: () => void }) {
  const [allocations, setAllocations] = useState<{ [invoiceId: number]: number }>({});
  const [draftAllocations, setDraftAllocations] = useState<{ [invoiceId: number]: string }>({});
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState('');

  const { data: unpaidInvoices = [] } = useQuery({
    queryKey: ['unpaid_invoices', partyId],
    queryFn: () => invoicesApi.list(partyId, true, undefined, 0, 1000).then(r => r.data.items.sort((a: any, b: any) => new Date(a.invoice_date).getTime() - new Date(b.invoice_date).getTime())),
  });

  const available = Number(payment.unallocated);
  const totalAllocated = Object.values(allocations).reduce((s, v) => s + (v || 0), 0);
  const remaining = available - totalAllocated;

  const onSubmit = async () => {
    if (loading) return;
    if (remaining < 0) { setErr('Allocations exceed available balance.'); return; }
    setLoading(true); setErr('');
    try {
      const finalAllocations = { ...allocations };
      Object.entries(draftAllocations).forEach(([idStr, val]) => {
        const invId = Number(idStr);
        if (val !== '') { const inv = (unpaidInvoices as any[]).find(i => i.id === invId); if (inv) { let n = Number(val); if (n < 0) n = 0; if (n > Number(inv.balance_due)) n = Number(inv.balance_due); finalAllocations[invId] = n; } }
      });
      const payload = Object.entries(finalAllocations).filter(([_, a]) => a > 0).map(([invoice_id, amount]) => ({ invoice_id: Number(invoice_id), allocated_amount: amount }));
      await paymentsApi.allocate(payment.id, payload);
      onSuccess();
    } catch (e: any) {
      setErr(e.response?.data?.detail || 'Failed to allocate');
    } finally { setLoading(false); }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-sheet" style={{ height: '80vh', display: 'flex', flexDirection: 'column' }} onClick={e => e.stopPropagation()}>
        <div className="modal-handle" />
        <h2 className="modal-title">Allocate to Invoice</h2>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 12, fontSize: 13 }}>
          <span style={{ color: 'var(--text-muted)' }}>Available: <strong style={{ color: 'var(--accent)' }}>{formatCurrency(available)}</strong></span>
          <span style={{ color: remaining < 0 ? 'var(--danger)' : 'var(--success)', fontWeight: 700 }}>Remaining: {formatCurrency(remaining)}</span>
        </div>
        {err && <div style={{ color: 'var(--danger)', fontSize: 13, marginBottom: 8 }}>{err}</div>}
        <div style={{ flex: 1, overflowY: 'auto' }}>
          {(unpaidInvoices as any[]).length === 0 ? (
            <p style={{ textAlign: 'center', color: 'var(--text-muted)', marginTop: 20 }}>No pending invoices for this party.</p>
          ) : (
            (unpaidInvoices as any[]).map((inv: any) => (
              <div key={inv.id} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px 0', borderBottom: '1px solid var(--border)', fontSize: 13 }}>
                <div>
                  <span style={{ fontWeight: 500 }}>{inv.invoice_number}</span>
                  <span style={{ color: 'var(--text-secondary)', fontSize: 12, display: 'block' }}>Due: {formatCurrency(inv.balance_due)}</span>
                </div>
                <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                  <input type="number" className="form-input" style={{ width: 100, padding: '6px 10px', fontSize: 13 }} placeholder="0.00" value={draftAllocations[inv.id] !== undefined ? draftAllocations[inv.id] : (allocations[inv.id] || '')} onChange={e => setDraftAllocations(prev => ({ ...prev, [inv.id]: e.target.value }))} />
                  <button type="button" className="btn btn-sm" style={{ background: allocations[inv.id] > 0 ? 'var(--success)' : 'var(--accent)', color: 'white', padding: '4px 12px' }} onClick={() => { const val = draftAllocations[inv.id]; if (val !== undefined) { let n = Number(val); if (n < 0) n = 0; if (n > Number(inv.balance_due)) n = Number(inv.balance_due); setAllocations(prev => ({ ...prev, [inv.id]: n })); setDraftAllocations(prev => { const p = { ...prev }; delete p[inv.id]; return p; }); } }}>OK</button>
                </div>
              </div>
            ))
          )}
        </div>
        <div style={{ display: 'flex', gap: 10, marginTop: 16, paddingTop: 16, borderTop: '1px solid var(--border)' }}>
          <button className="btn btn-secondary" style={{ flex: 1 }} onClick={onClose}>Cancel</button>
          <button className="btn btn-primary" style={{ flex: 1 }} disabled={loading || totalAllocated <= 0 || remaining < 0} onClick={onSubmit}>{loading ? 'Processing…' : 'Apply'}</button>
        </div>
      </div>
    </div>
  );
}
