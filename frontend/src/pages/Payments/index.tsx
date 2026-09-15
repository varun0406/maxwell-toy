import { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { paymentsApi, partiesApi, invoicesApi } from '../../api/endpoints';
import { formatCurrency, formatDate } from '../../utils/format';
import { SearchCombobox } from '../../components/SearchCombobox';
import type { ComboboxOption } from '../../components/SearchCombobox';
import { useInfiniteQuery } from '@tanstack/react-query';
import { useInView } from 'react-intersection-observer';
import { Search, X, Plus, ChevronLeft } from 'lucide-react';

const schema = z.object({
  party_id: z.coerce.number().min(1, 'Select a party'),
  amount: z.coerce.number().positive('Must be > 0'),
  payment_date: z.string().min(1, 'Date required'),
  note: z.string().optional(),
  mode: z.enum(['cash', 'upi', 'bank', 'cheque']).default('cash'),
});
type PaymentForm = z.infer<typeof schema>;

// ── Payments List ─────────────────────────────────────────────────────────────
export function PaymentsList() {
  const navigate = useNavigate();
  const [search, setSearch] = useState('');
  const { ref, inView } = useInView();

  const {
    data,
    isLoading,
    fetchNextPage,
    hasNextPage,
  } = useInfiniteQuery({
    queryKey: ['payments', search],
    queryFn: ({ pageParam = 0 }) => paymentsApi.list(undefined, search, pageParam, 20).then((r) => r.data),
    getNextPageParam: (lastPage) => {
      if (lastPage.skip + lastPage.limit < lastPage.total) {
        return lastPage.skip + lastPage.limit;
      }
      return undefined;
    },
    initialPageParam: 0,
  });

  useEffect(() => {
    if (inView && hasNextPage) {
      fetchNextPage();
    }
  }, [inView, hasNextPage, fetchNextPage]);

  const payments = data ? data.pages.flatMap((page) => page.items) : [];
  const totalCount = data ? data.pages[0]?.total || 0 : 0;
  const summaryTotal = data ? data.pages[0]?.summary_total || 0 : 0;

  return (
    <div className="page-content">
      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
            <h1 className="page-title">Payments</h1>
            <p className="page-subtitle">{totalCount} received</p>
        </div>
        <div style={{ textAlign: 'right' }}>
            <p style={{ fontSize: 14, fontWeight: 700, color: 'var(--success)' }}>Total: {formatCurrency(summaryTotal)}</p>
        </div>
      </div>

      <div className="search-bar" style={{ marginBottom: 16 }}>
        <Search size={16} />
        <input
          placeholder="Search party name…"
          value={search}
          onChange={e => setSearch(e.target.value)}
        />
        {search && <button onClick={() => setSearch('')} style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}><X size={14} /></button>}
      </div>

      {isLoading ? (
        <div className="loading-screen"><div className="spinner" /></div>
      ) : payments.length === 0 ? (
        <div className="empty-state">
          <Plus size={48} />
          <h3>No payments yet</h3>
          <p>Record your first payment to track collections</p>
        </div>
      ) : (
        <div className="list-container">
          {payments.map((p: any) => (
            <div key={p.id} className="list-item" onClick={() => navigate(`/payments/${p.id}`)}>
              <div className="list-item-icon" style={{ background: 'var(--success-bg)' }}>💰</div>
              <div className="list-item-body">
                <p className="list-item-title">{p.party_name}</p>
                <p className="list-item-sub">PMT-{String(p.id).padStart(4, '0')} · {formatDate(p.payment_date)}</p>
              </div>
              <div className="list-item-right">
                <p style={{ fontWeight: 700, fontSize: 15, color: 'var(--success)' }}>{formatCurrency(p.amount)}</p>
                {p.unallocated > 0 && (
                  <span className="badge badge-accent" style={{ marginTop: 4, fontSize: 10 }}>
                    On Account {formatCurrency(p.unallocated)}
                  </span>
                )}
              </div>
            </div>
          ))}
          {hasNextPage && (
            <div ref={ref} style={{ padding: '20px 0', textAlign: 'center' }}>
              <div className="spinner" style={{ width: 24, height: 24, borderWidth: 3 }} />
            </div>
          )}
        </div>
      )}

      <button className="fab" onClick={() => navigate('/payments/new')}>
        <Plus size={24} />
      </button>
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
  const { register, handleSubmit, watch, setValue, formState: { errors } } = useForm<PaymentForm>({
    resolver: zodResolver(schema),
    defaultValues: {
      party_id: searchParams.get('party') ? Number(searchParams.get('party')) : undefined,
      payment_date: today,
      mode: 'cash',
    },
  });

  const selectedParty = watch('party_id');
  const enteredAmount = watch('amount') || 0;

  const [partySearch, setPartySearch] = useState('');
  const { data: parties = [] } = useQuery({
    queryKey: ['parties', partySearch],
    queryFn: () => partiesApi.list(partySearch, 0, 100).then((r) => r.data.items),
  });

  const partyOptions: ComboboxOption[] = parties.map((p: any) => ({
    value: p.id,
    label: p.name,
    sublabel: `Due: ${p.outstanding?.toLocaleString('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 })}`,
  }));

  // Fetch unpaid invoices when party changes and bill_adjustment is selected
  useEffect(() => {
    if (selectedParty && paymentType === 'bill_adjustment') {
      invoicesApi.list(Number(selectedParty), true).then((r) => {
        setUnpaidInvoices(r.data.sort((a: any, b: any) => new Date(a.invoice_date).getTime() - new Date(b.invoice_date).getTime()));
        setAllocations({}); // Reset allocations when party changes
        setDraftAllocations({});
      });
    }
  }, [selectedParty, paymentType]);

  const handleAllocationChange = (invoiceId: number, value: string, maxLimit: number) => {
    let numValue = Number(value);
    if (numValue < 0) numValue = 0;
    if (numValue > maxLimit) numValue = maxLimit; // Can't allocate more than balance due
    
    setAllocations(prev => ({
      ...prev,
      [invoiceId]: numValue
    }));
  };

  const totalAllocated = Object.values(allocations).reduce((sum, val) => sum + (val || 0), 0);

  const onSubmit = async (data: PaymentForm) => {
    if (loading) return;
    setLoading(true); setErr('');
    
    if (paymentType === 'bill_adjustment' && totalAllocated > Number(data.amount)) {
        setErr("Total allocated amount cannot exceed the received payment amount.");
        setLoading(false);
        return;
    }

    try {
      const payload: any = {
        ...data,
        payment_date: new Date(data.payment_date).toISOString(),
      };

      if (paymentType === 'bill_adjustment') {
          // Commit any pending drafts before submitting
          const finalAllocations = { ...allocations };
          Object.entries(draftAllocations).forEach(([invIdStr, val]) => {
              const invId = Number(invIdStr);
              if (val !== '') {
                  const inv = unpaidInvoices.find(i => i.id === invId);
                  if (inv) {
                      let num = Number(val);
                      if (num < 0) num = 0;
                      if (num > Number(inv.balance_due)) num = Number(inv.balance_due);
                      finalAllocations[invId] = num;
                  }
              }
          });

          payload.allocations = Object.entries(finalAllocations)
            .filter(([_, amount]) => amount > 0)
            .map(([invoice_id, amount]) => ({
                invoice_id: Number(invoice_id),
                allocated_amount: amount
            }));
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
          
          {/* Party — searchable */}
          <div className="form-group">
            <label className="form-label">Party *</label>
            <SearchCombobox
              value={selectedParty || null}
              placeholder="Select party…"
              options={partyOptions}
              onChange={opt => setValue('party_id', Number(opt.value))}
              onSearch={setPartySearch}
            />
            {errors.party_id && <span className="form-error">{errors.party_id.message}</span>}
          </div>

          <div className="form-group">
            <label className="form-label">Amount Received (₹) *</label>
            <input className="form-input" type="number" step="0.01" placeholder="0.00" {...register('amount')} />
            {errors.amount && <span className="form-error">{errors.amount.message}</span>}
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
            <div className="form-group">
              <label className="form-label">Date *</label>
              <input className="form-input" type="date" {...register('payment_date')} />
            </div>
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

          {/* Payment Type Toggle */}
          <div style={{ display: 'flex', gap: 10, marginBottom: 20 }}>
            <button 
                type="button"
                style={{ 
                    flex: 1, 
                    padding: '12px', 
                    borderRadius: 'var(--radius-md)', 
                    border: `1px solid ${paymentType === 'on_account' ? 'var(--accent)' : 'var(--border)'}`,
                    background: paymentType === 'on_account' ? 'var(--accent-glow)' : 'var(--bg-elevated)',
                    color: paymentType === 'on_account' ? 'var(--accent)' : 'var(--text-secondary)',
                    fontWeight: paymentType === 'on_account' ? 600 : 400,
                }}
                onClick={() => setPaymentType('on_account')}
            >
                On Account
            </button>
            <button 
                type="button"
                style={{ 
                    flex: 1, 
                    padding: '12px', 
                    borderRadius: 'var(--radius-md)', 
                    border: `1px solid ${paymentType === 'bill_adjustment' ? 'var(--accent)' : 'var(--border)'}`,
                    background: paymentType === 'bill_adjustment' ? 'var(--accent-glow)' : 'var(--bg-elevated)',
                    color: paymentType === 'bill_adjustment' ? 'var(--accent)' : 'var(--text-secondary)',
                    fontWeight: paymentType === 'bill_adjustment' ? 600 : 400,
                }}
                onClick={() => setPaymentType('bill_adjustment')}
            >
                Bill Adjustment
            </button>
          </div>

          {paymentType === 'bill_adjustment' && selectedParty && (
            <div style={{ background: 'var(--bg-elevated)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border)', padding: 14, marginBottom: 20 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
                <p style={{ fontSize: 13, fontWeight: 600, color: 'var(--text)' }}>
                    Select Bills to Settle
                </p>
                <div style={{ fontSize: 12, textAlign: 'right' }}>
                    <p style={{ color: 'var(--text-secondary)' }}>Remaining to Allocate:</p>
                    <p style={{ color: (enteredAmount - totalAllocated) < 0 ? 'var(--danger)' : 'var(--success)', fontWeight: 700, fontSize: 14 }}>
                        {formatCurrency(enteredAmount - totalAllocated)}
                    </p>
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
                            <input 
                                type="number" 
                                className="form-input" 
                                style={{ width: 100, padding: '6px 10px', fontSize: 13 }}
                                placeholder="0.00"
                                value={draftAllocations[inv.id] !== undefined ? draftAllocations[inv.id] : (allocations[inv.id] || '')}
                                onChange={(e) => setDraftAllocations(prev => ({ ...prev, [inv.id]: e.target.value }))}
                            />
                            <button 
                                type="button" 
                                className="btn btn-sm" 
                                style={{ background: allocations[inv.id] === Number(draftAllocations[inv.id]) || (draftAllocations[inv.id] === undefined && allocations[inv.id] > 0) ? 'var(--success)' : 'var(--accent)', color: 'white', padding: '4px 12px' }}
                                onClick={() => {
                                    const val = draftAllocations[inv.id];
                                    if (val !== undefined) {
                                        handleAllocationChange(inv.id, val, Number(inv.balance_due));
                                        setDraftAllocations(prev => { const next = {...prev}; delete next[inv.id]; return next; });
                                    }
                                }}
                            >
                                OK
                            </button>
                        </div>
                    </div>
                  ))
              )}
            </div>
          )}

          {paymentType === 'on_account' && (
              <p style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 20, textAlign: 'center' }}>
                  This payment will be saved directly to the party's account and will not be applied to any specific invoices yet.
              </p>
          )}

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
  const id = window.location.pathname.split('/').pop();

  const { data: payment, isLoading } = useQuery({
    queryKey: ['payment', id],
    queryFn: () => paymentsApi.get(Number(id)).then((r) => r.data),
  });

  if (isLoading) return <div className="loading-screen"><div className="spinner" /></div>;
  if (!payment) return null;

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', background: 'var(--bg-base)' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '20px 20px 16px', borderBottom: '1px solid var(--border)' }}>
        <button className="btn-icon btn" onClick={() => navigate(-1)}><ChevronLeft size={20} /></button>
        <h1 className="page-title">Payment Detail</h1>
      </div>

      <div className="page-content" style={{ paddingTop: 20, paddingLeft: 20, paddingRight: 20 }}>
        <div className="hero-card" style={{ margin: 0, marginBottom: 16 }}>
          <p className="hero-label">Amount Received</p>
          <p className="hero-amount">{formatCurrency(payment.amount)}</p>
          <p className="hero-sub">{formatDate(payment.payment_date)} · {payment.mode}</p>
          {payment.note && <p className="hero-sub" style={{ marginTop: 4 }}>{payment.note}</p>}
        </div>

        {payment.unallocated > 0 && (
          <div style={{ background: 'var(--accent-glow)', borderRadius: 10, padding: '10px 14px', marginBottom: 16, fontSize: 13, color: 'var(--accent-light)' }}>
            Unallocated (On Account): <strong>{formatCurrency(payment.unallocated)}</strong>
          </div>
        )}

        {payment.allocations?.length > 0 && (
            <>
                <p className="section-label" style={{ padding: '0 0 8px' }}>Allocated Towards Bills</p>
                <div style={{ background: 'var(--bg-elevated)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border)', padding: '0 14px' }}>
                    {payment.allocations?.map((a: any, i: number) => (
                        <div key={a.invoice_id} style={{ display: 'flex', justifyContent: 'space-between', padding: '12px 0', borderBottom: i < payment.allocations.length - 1 ? '1px solid var(--border)' : 'none', fontSize: 14 }}>
                            <div>
                                <p style={{ fontWeight: 600 }}>{a.invoice_number}</p>
                            </div>
                            <p style={{ color: 'var(--success)', fontWeight: 700 }}>{formatCurrency(a.allocated_amount)}</p>
                        </div>
                    ))}
                </div>
            </>
        )}
      </div>
    </div>
  );
}
