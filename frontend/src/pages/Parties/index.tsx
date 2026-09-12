import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useNavigate, useParams } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { partiesApi, paymentsApi, invoicesApi } from '../../api/endpoints';
import { formatCurrency, formatDate } from '../../utils/format';
import { Plus, Phone, MapPin, Search, NotebookPen, FileText, CreditCard, X, Trash2 } from 'lucide-react';
import { generateAndSharePartyStatement, openWhatsApp } from '../../utils/pdfGenerator';
import { SecureActionModal } from '../../components/SecureActionModal';

const schema = z.object({
  name: z.string().min(1, 'Name required'),
  phone: z.string().optional(),
  email: z.string().email().optional().or(z.literal('')),
  agent_name: z.string().optional(),
  billing_address_line1: z.string().optional(),
  billing_address_line2: z.string().optional(),
  billing_address_line3: z.string().optional(),
  billing_city: z.string().optional(),
  shipping_address_line1: z.string().optional(),
  shipping_address_line2: z.string().optional(),
  shipping_address_line3: z.string().optional(),
  shipping_city: z.string().optional(),
  gstin: z.string().optional(),
  notes: z.string().optional(),
  area: z.string().optional(),
  reminder_date: z.string().optional(),
});
type PartyForm = z.infer<typeof schema>;

// ── Party List ──────────────────────────────────────────────────────────────
export function PartiesList() {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [search, setSearch] = useState('');
  const [showAdd, setShowAdd] = useState(false);
  const [secureActionId, setSecureActionId] = useState<number | null>(null);

  const { data: parties = [], isLoading, refetch } = useQuery({
    queryKey: ['parties', search],
    queryFn: () => partiesApi.list(search).then((r) => r.data),
  });

  return (
    <div className="page-content">
      <div className="page-header">
        <h1 className="page-title">Parties</h1>
        <p className="page-subtitle">{parties.length} customers / suppliers</p>
      </div>

      <div className="search-bar">
        <Search size={16} />
        <input
          placeholder="Search by name…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        {search && <button onClick={() => setSearch('')} style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}><X size={14} /></button>}
      </div>

      {isLoading ? (
        <div className="loading-screen"><div className="spinner" /></div>
      ) : parties.length === 0 ? (
        <div className="empty-state">
          <Search size={48} />
          <h3>{search ? 'No results' : 'No parties yet'}</h3>
          <p>{search ? 'Try a different name' : 'Add your first customer or supplier'}</p>
        </div>
      ) : (
        <div className="list-container">
          {parties.map((p: any) => (
            <div key={p.id} className="list-item" onClick={() => navigate(`/parties/${p.id}`)}>
              <div className="list-item-icon" style={{ background: 'linear-gradient(135deg, var(--accent-glow), rgba(108,99,255,0.05))', color: 'var(--accent-light)', fontWeight: 700, fontSize: 16 }}>
                {p.name[0].toUpperCase()}
              </div>
              <div className="list-item-body">
                <p className="list-item-title">{p.name}</p>
                <p className="list-item-sub">{p.phone || p.email || 'No contact info'}</p>
              </div>
              <div className="list-item-right" style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end' }}>
                <p style={{ fontWeight: 700, fontSize: 14, color: p.outstanding > 0 ? 'var(--warning)' : 'var(--success)' }}>
                  {formatCurrency(p.outstanding)}
                </p>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginTop: 4 }}>
                  <p style={{ fontSize: 11, color: 'var(--text-muted)' }}>due</p>
                  <button 
                    className="btn-icon" 
                    style={{ padding: 4, background: 'rgba(239,68,68,0.1)', color: 'var(--danger)' }}
                    onClick={(e) => {
                      e.stopPropagation();
                      setSecureActionId(p.id);
                    }}
                  >
                    <Trash2 size={12} />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      <button className="fab" onClick={() => setShowAdd(true)}>
        <Plus size={24} />
      </button>

      {showAdd && (
        <AddPartyModal onClose={() => setShowAdd(false)} onSuccess={() => { setShowAdd(false); refetch(); }} />
      )}

      <SecureActionModal
        isOpen={secureActionId !== null}
        onClose={() => setSecureActionId(null)}
        title="Hide Party"
        message="Enter Master PIN to hide this party. All related data will also be hidden."
        onConfirm={async () => {
          if (secureActionId) {
            await partiesApi.delete(secureActionId);
            qc.invalidateQueries();
          }
          setSecureActionId(null);
        }}
      />
    </div>
  );
}

// ── Party Detail ────────────────────────────────────────────────────────────
export function PartyDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [tab, setTab] = useState<'ledger' | 'invoices' | 'payments'>('ledger');
  const [showAllocateModal, setShowAllocateModal] = useState(false);
  const [showJournalModal, setShowJournalModal] = useState(false);
  const [secureAction, setSecureAction] = useState<{ type: 'payment' | 'journal', id: number } | null>(null);
  const [showEditModal, setShowEditModal] = useState(false);
  const qc = useQueryClient();

  const { data: party, refetch: refetchParty } = useQuery({
    queryKey: ['party', id],
    queryFn: () => partiesApi.get(Number(id)).then((r) => r.data),
  });
  
  const { data: ledger = [] } = useQuery({
    queryKey: ['ledger', id],
    queryFn: () => partiesApi.ledger(Number(id)).then((r) => r.data),
    enabled: tab === 'ledger',
  });

  const { data: payments = [] } = useQuery({
    queryKey: ['payments', id],
    queryFn: () => paymentsApi.list(Number(id)).then(r => r.data)
  });
  
  const hasUnallocated = payments.some((p: any) => p.unallocated > 0);
  const totalUnallocated = payments.reduce((sum: number, p: any) => sum + Number(p.unallocated), 0);

  if (!party) return <div className="loading-screen"><div className="spinner" /></div>;

  return (
    <div className="page-content">
      {/* Party Hero */}
      <div className="hero-card" style={{ marginTop: 16 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <p className="hero-label">Outstanding Balance</p>
            <p className="hero-amount">{formatCurrency(party.outstanding)}</p>
          </div>
          <div style={{
            width: 56, height: 56, borderRadius: 14,
            background: 'rgba(255,255,255,0.1)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: 24, fontWeight: 800,
          }}>
            {party.name[0].toUpperCase()}
          </div>
        </div>
        <p className="hero-sub" style={{ marginTop: 12, fontSize: 18, fontWeight: 700, color: '#fff' }}>{party.name}</p>
        <div style={{ display: 'flex', gap: 16, marginTop: 12, fontSize: 12, color: 'rgba(255,255,255,0.55)' }}>
          {party.phone && <span><Phone size={12} style={{ display: 'inline', marginRight: 4 }} />{party.phone}</span>}
          {party.billing_city && <span><MapPin size={12} style={{ display: 'inline', marginRight: 4 }} />{party.billing_city}</span>}
          {party.agent_name && <span>Agent: {party.agent_name}</span>}
          {party.area && <span style={{ background: 'rgba(255,255,255,0.2)', padding: '2px 6px', borderRadius: 4 }}>Area: {party.area}</span>}
        </div>
        <div style={{ marginTop: 12 }}>
          <button className="btn btn-sm" style={{ background: 'rgba(255,255,255,0.2)', color: 'white', border: 'none' }} onClick={() => setShowEditModal(true)}>
            Edit Party Details
          </button>
        </div>
      </div>

      {/* Mini stats */}
      <div className="stats-grid" style={{ gridTemplateColumns: '1fr 1fr 1fr' }}>
        <div className="stat-card accent">
          <p className="stat-label">Invoiced</p>
          <p className="stat-value mono" style={{ fontSize: 15 }}>{formatCurrency(party.total_invoiced)}</p>
        </div>
        <div className="stat-card success">
          <p className="stat-label">Paid</p>
          <p className="stat-value mono" style={{ fontSize: 15 }}>{formatCurrency(party.total_paid)}</p>
        </div>
        <div className="stat-card warning">
          <p className="stat-label">Due</p>
          <p className="stat-value mono" style={{ fontSize: 15 }}>{formatCurrency(party.outstanding)}</p>
        </div>
      </div>
      
      {hasUnallocated && (
          <div style={{ background: 'var(--accent-glow)', padding: '12px 16px', borderRadius: 12, margin: '16px 20px 0', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                  <p style={{ fontSize: 12, color: 'var(--accent)', fontWeight: 600 }}>Unallocated Balance</p>
                  <p style={{ fontSize: 16, fontWeight: 700, color: 'var(--accent)' }}>{formatCurrency(totalUnallocated)}</p>
              </div>
              <button className="btn btn-sm" style={{ background: 'var(--accent)', color: 'white' }} onClick={() => setShowAllocateModal(true)}>
                  Settle Bills
              </button>
          </div>
      )}

      {/* Quick actions */}
      <div className="quick-actions" style={{ marginTop: hasUnallocated ? 16 : 24 }}>
        <button className="quick-action-btn accent" onClick={() => navigate(`/invoices/new?party=${id}`)}>
          <FileText size={18} />New Invoice
        </button>
        <button className="quick-action-btn success" onClick={() => navigate(`/payments/new?party=${id}`)}>
          <CreditCard size={18} />Payment
        </button>
        <button className="quick-action-btn" style={{ borderColor: 'var(--accent)', color: 'var(--accent)' }} onClick={() => setShowJournalModal(true)}>
          <NotebookPen size={18} />General A/c
        </button>
        <button
          className="quick-action-btn warning"
          onClick={async () => {
            const unpaid = (await invoicesApi.list(Number(id), true)).data;
            if (unpaid.length === 0) { alert('No pending invoices for this party.'); return; }
            generateAndSharePartyStatement(party, unpaid, totalUnallocated);
          }}
        >
          <FileText size={18} />Statement
        </button>
        {party.phone && (
          <button
            className="quick-action-btn"
            style={{ borderColor: 'rgba(37,211,102,0.3)', color: '#25d366' }}
            onClick={() => openWhatsApp(party.phone, `Hi ${party.name}, please find the attached outstanding statement.`)}
          >
            <Phone size={18} />WhatsApp
          </button>
        )}
      </div>

      {/* Tabs */}
      <div className="chips">
        {(['ledger', 'invoices', 'payments'] as const).map((t) => (
          <button key={t} className={`chip ${tab === t ? 'active' : ''}`} onClick={() => setTab(t)}>
            {t.charAt(0).toUpperCase() + t.slice(1)}
          </button>
        ))}
      </div>

      {/* Ledger */}
      {tab === 'ledger' && (
        <div style={{ padding: '0 20px', marginTop: 8 }}>
          {ledger.length === 0 ? (
            <div className="empty-state"><p>No transactions yet</p></div>
          ) : (
            ledger.map((entry: any, i: number) => (
              <div key={i} className="ledger-row">
                <div className={`ledger-dot ${entry.type}`} />
                <div style={{ flex: 1 }}>
                  <p style={{ fontSize: 14, fontWeight: 600 }}>{entry.reference}</p>
                  <p style={{ fontSize: 12, color: 'var(--text-muted)' }}>{formatDate(entry.date)}</p>
                </div>
                <div style={{ textAlign: 'right', display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 4 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                    <p style={{ fontSize: 14, fontWeight: 700, color: Number(entry.amount) < 0 ? 'var(--success)' : 'var(--text-primary)' }}>
                      {Number(entry.amount) < 0 ? '-' : '+'}{formatCurrency(Math.abs(Number(entry.amount)))}
                    </p>
                    {(entry.type === 'payment' || entry.type === 'journal') && (
                      <button 
                        className="btn-icon" 
                        style={{ padding: 4, background: 'rgba(239,68,68,0.1)', color: 'var(--danger)' }}
                        onClick={() => {
                          const idParts = entry.reference.split('-');
                          const id = Number(idParts[1]);
                          if (!isNaN(id)) {
                            setSecureAction({ type: entry.type as 'payment' | 'journal', id });
                          }
                        }}
                      >
                        <Trash2 size={12} />
                      </button>
                    )}
                  </div>
                  <p style={{ fontSize: 11, color: 'var(--text-muted)' }}>Bal: {formatCurrency(entry.running_balance)}</p>
                </div>
              </div>
            ))
          )}
        </div>
      )}
      
      {showAllocateModal && (
          <AllocateOnAccountModal 
            partyId={Number(id)} 
            onClose={() => setShowAllocateModal(false)} 
            payments={payments.filter((p: any) => p.unallocated > 0)}
          />
      )}

      {showJournalModal && (
        <JournalModal
          partyId={Number(id)}
          onClose={() => setShowJournalModal(false)}
          onSuccess={() => { setShowJournalModal(false); qc.invalidateQueries(); }}
        />
      )}

      <SecureActionModal
        isOpen={secureAction !== null}
        onClose={() => setSecureAction(null)}
        title={`Hide ${secureAction?.type === 'payment' ? 'Payment' : 'Journal Entry'}`}
        message={`Enter Master PIN to hide this ${secureAction?.type}. Balances will be recalibrated.`}
        onConfirm={async () => {
          if (secureAction?.type === 'payment') {
            await paymentsApi.delete(secureAction.id);
          } else if (secureAction?.type === 'journal') {
            await partiesApi.deleteJournalEntry(secureAction.id);
          }
          qc.invalidateQueries();
          setSecureAction(null);
        }}
      />

      {showEditModal && (
        <EditPartyModal 
          party={party} 
          onClose={() => setShowEditModal(false)} 
          onSuccess={() => { setShowEditModal(false); refetchParty(); qc.invalidateQueries({ queryKey: ['parties'] }); }} 
        />
      )}
    </div>
  );
}


// ── Allocate On-Account Modal ───────────────────────────────────────────────
function AllocateOnAccountModal({ partyId, payments, onClose }: { partyId: number, payments: any[], onClose: () => void }) {
    const qc = useQueryClient();
    const [selectedPaymentId, setSelectedPaymentId] = useState<number | null>(payments[0]?.id || null);
    const [allocations, setAllocations] = useState<{ [invoiceId: number]: number }>({});
    const [draftAllocations, setDraftAllocations] = useState<{ [invoiceId: number]: string }>({});
    const [loading, setLoading] = useState(false);
    const [err, setErr] = useState('');
    
    const { data: unpaidInvoices = [] } = useQuery({
      queryKey: ['unpaid_invoices', partyId],
      queryFn: () => invoicesApi.list(partyId, true).then(r => r.data.sort((a: any, b: any) => new Date(a.invoice_date).getTime() - new Date(b.invoice_date).getTime())),
    });
    
    const selectedPayment = payments.find(p => p.id === selectedPaymentId);
    const availableAmount = selectedPayment ? Number(selectedPayment.unallocated) : 0;
    const totalAllocated = Object.values(allocations).reduce((sum, val) => sum + (val || 0), 0);
    const remainingToAllocate = availableAmount - totalAllocated;
    
    const handleAllocationChange = (invoiceId: number, value: string, maxLimit: number) => {
      let numValue = Number(value);
      if (numValue < 0) numValue = 0;
      if (numValue > maxLimit) numValue = maxLimit;
      setAllocations(prev => ({ ...prev, [invoiceId]: numValue }));
    };
    
    const onSubmit = async () => {
        if (loading) return;
        if (!selectedPaymentId) return;
        if (remainingToAllocate < 0) {
            setErr("Allocations exceed available balance.");
            return;
        }
        
        setLoading(true); setErr('');
        try {
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

            const payload = Object.entries(finalAllocations)
              .filter(([_, amount]) => amount > 0)
              .map(([invoice_id, amount]) => ({
                  invoice_id: Number(invoice_id),
                  allocated_amount: amount
              }));
              
            await paymentsApi.allocate(selectedPaymentId, payload);
            qc.invalidateQueries();
            onClose();
        } catch (e: any) {
            setErr(e.response?.data?.detail || 'Failed to allocate balance');
        } finally {
            setLoading(false);
        }
    };
    
    return (
        <div className="modal-overlay" onClick={onClose}>
          <div className="modal-sheet" onClick={(e) => e.stopPropagation()} style={{ height: '80vh', display: 'flex', flexDirection: 'column' }}>
            <div className="modal-handle" />
            <h2 className="modal-title">Settle Bills (On Account)</h2>
            {err && <div style={{ color: 'var(--danger)', fontSize: 13, marginBottom: 12 }}>{err}</div>}
            
            <div style={{ flex: 1, overflowY: 'auto', paddingRight: 8, paddingBottom: 16 }}>
                <div className="form-group">
                    <label className="form-label">Select Payment</label>
                    <select 
                        className="form-select" 
                        value={selectedPaymentId || ''} 
                        onChange={(e) => { setSelectedPaymentId(Number(e.target.value)); setAllocations({}); }}
                    >
                        {payments.map(p => (
                            <option key={p.id} value={p.id}>
                                PMT-{String(p.id).padStart(4, '0')} — Avail: {formatCurrency(p.unallocated)}
                            </option>
                        ))}
                    </select>
                </div>
                
                {selectedPayment && (
                    <div style={{ background: 'var(--bg-elevated)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border)', padding: 14, marginBottom: 20 }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
                        <p style={{ fontSize: 13, fontWeight: 600, color: 'var(--text)' }}>
                            Select Bills to Settle
                        </p>
                        <div style={{ fontSize: 12, textAlign: 'right' }}>
                            <p style={{ color: 'var(--text-secondary)' }}>Remaining to Allocate:</p>
                            <p style={{ color: remainingToAllocate < 0 ? 'var(--danger)' : 'var(--success)', fontWeight: 700, fontSize: 14 }}>
                                {formatCurrency(remainingToAllocate)}
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
            </div>
            
            <div style={{ display: 'flex', gap: 10, marginTop: 16, paddingTop: 16, borderTop: '1px solid var(--border)' }}>
                <button type="button" className="btn btn-secondary" style={{ flex: 1 }} onClick={onClose}>Cancel</button>
                <button type="button" className="btn btn-primary" style={{ flex: 1 }} disabled={loading || totalAllocated <= 0 || remainingToAllocate < 0} onClick={onSubmit}>
                  {loading ? 'Processing…' : 'Apply Balance'}
                </button>
            </div>
          </div>
        </div>
    )
}

// ── Add Party Modal ─────────────────────────────────────────────────────────
function AddPartyModal({ onClose, onSuccess }: { onClose: () => void; onSuccess: () => void }) {
  const { register, handleSubmit, formState: { errors } } = useForm<PartyForm>({ resolver: zodResolver(schema) });
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState('');

  const onSubmit = async (data: PartyForm) => {
    if (loading) return;
    setLoading(true);
    try {
      await partiesApi.create(data);
      onSuccess();
    } catch (e: any) {
      setErr(e.response?.data?.detail || 'Failed to create party');
    } finally { setLoading(false); }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-sheet" onClick={(e) => e.stopPropagation()}>
        <div className="modal-handle" />
        <h2 className="modal-title">New Party</h2>
        {err && <div style={{ color: 'var(--danger)', fontSize: 13, marginBottom: 12 }}>{err}</div>}
        <form onSubmit={handleSubmit(onSubmit)}>
          <div style={{ maxHeight: '60vh', overflowY: 'auto', paddingRight: 8, paddingBottom: 16 }}>
            <h4 style={{ margin: '8px 0', fontSize: 14, color: 'var(--accent-glow)' }}>General</h4>
            <div className="form-group">
              <label className="form-label">Name *</label>
              <input className="form-input" placeholder="Party / Company name" {...register('name')} />
              {errors.name && <span className="form-error">{errors.name.message}</span>}
            </div>
            <div className="form-group">
              <label className="form-label">Agent Name</label>
              <input className="form-input" placeholder="e.g. Rahul Agent" {...register('agent_name')} />
            </div>
            <div style={{ display: 'flex', gap: 8 }}>
              <div className="form-group" style={{ flex: 1 }}>
                <label className="form-label">Phone</label>
                <input className="form-input" type="tel" placeholder="+91 9999999999" {...register('phone')} />
              </div>
              <div className="form-group" style={{ flex: 1 }}>
                <label className="form-label">Email</label>
                <input className="form-input" type="email" placeholder="party@email.com" {...register('email')} />
              </div>
            </div>
            <div className="form-group">
              <label className="form-label">GSTIN</label>
              <input className="form-input" placeholder="22AAAAA0000A1Z5" {...register('gstin')} />
            </div>

            <h4 style={{ margin: '16px 0 8px', fontSize: 14, color: 'var(--accent-glow)' }}>Categorization & Reminders</h4>
            <div style={{ display: 'flex', gap: 8 }}>
              <div className="form-group" style={{ flex: 1 }}>
                <label className="form-label">Area</label>
                <input className="form-input" placeholder="e.g. North Zone" {...register('area')} />
              </div>
              <div className="form-group" style={{ flex: 1 }}>
                <label className="form-label">Reminder Date</label>
                <input className="form-input" type="date" {...register('reminder_date')} />
              </div>
            </div>

            <h4 style={{ margin: '16px 0 8px', fontSize: 14, color: 'var(--accent-glow)' }}>Billing Address</h4>
            <div className="form-group">
              <input className="form-input" placeholder="Line 1" {...register('billing_address_line1')} />
            </div>
            <div className="form-group">
              <input className="form-input" placeholder="Line 2" {...register('billing_address_line2')} />
            </div>
            <div style={{ display: 'flex', gap: 8 }}>
              <div className="form-group" style={{ flex: 1 }}>
                <input className="form-input" placeholder="Line 3" {...register('billing_address_line3')} />
              </div>
              <div className="form-group" style={{ flex: 1 }}>
                <input className="form-input" placeholder="City" {...register('billing_city')} />
              </div>
            </div>

            <h4 style={{ margin: '16px 0 8px', fontSize: 14, color: 'var(--accent-glow)' }}>Shipping Address</h4>
            <div className="form-group">
              <input className="form-input" placeholder="Line 1" {...register('shipping_address_line1')} />
            </div>
            <div className="form-group">
              <input className="form-input" placeholder="Line 2" {...register('shipping_address_line2')} />
            </div>
            <div style={{ display: 'flex', gap: 8 }}>
              <div className="form-group" style={{ flex: 1 }}>
                <input className="form-input" placeholder="Line 3" {...register('shipping_address_line3')} />
              </div>
              <div className="form-group" style={{ flex: 1 }}>
                <input className="form-input" placeholder="City" {...register('shipping_city')} />
              </div>
            </div>
          </div>
          
          <div style={{ display: 'flex', gap: 10, marginTop: 8 }}>
            <button type="button" className="btn btn-secondary" style={{ flex: 1 }} onClick={onClose}>Cancel</button>
            <button type="submit" className="btn btn-primary" style={{ flex: 1 }} disabled={loading}>
              {loading ? 'Saving…' : 'Add Party'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ── Edit Party Modal ────────────────────────────────────────────────────────
function EditPartyModal({ party, onClose, onSuccess }: { party: any; onClose: () => void; onSuccess: () => void }) {
  const { register, handleSubmit, formState: { errors } } = useForm<PartyForm>({ 
    resolver: zodResolver(schema),
    defaultValues: {
      ...party,
      reminder_date: party.reminder_date ? party.reminder_date.split('T')[0] : '',
    }
  });
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState('');

  const onSubmit = async (data: PartyForm) => {
    if (loading) return;
    setLoading(true);
    try {
      // If reminder date is set, convert it to iso string or keep it as YYYY-MM-DD
      const payload = { ...data };
      if (payload.reminder_date) {
        payload.reminder_date = new Date(payload.reminder_date).toISOString();
      } else {
        payload.reminder_date = undefined;
      }
      
      await partiesApi.update(party.id, payload);
      onSuccess();
    } catch (e: any) {
      setErr(e.response?.data?.detail || 'Failed to update party');
    } finally { setLoading(false); }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-sheet" onClick={(e) => e.stopPropagation()}>
        <div className="modal-handle" />
        <h2 className="modal-title">Edit Party</h2>
        {err && <div style={{ color: 'var(--danger)', fontSize: 13, marginBottom: 12 }}>{err}</div>}
        <form onSubmit={handleSubmit(onSubmit)}>
          <div style={{ maxHeight: '60vh', overflowY: 'auto', paddingRight: 8, paddingBottom: 16 }}>
            <h4 style={{ margin: '8px 0', fontSize: 14, color: 'var(--accent-glow)' }}>General</h4>
            <div className="form-group">
              <label className="form-label">Name *</label>
              <input className="form-input" placeholder="Party / Company name" {...register('name')} />
              {errors.name && <span className="form-error">{errors.name.message}</span>}
            </div>
            <div className="form-group">
              <label className="form-label">Agent Name</label>
              <input className="form-input" placeholder="e.g. Rahul Agent" {...register('agent_name')} />
            </div>
            <div style={{ display: 'flex', gap: 8 }}>
              <div className="form-group" style={{ flex: 1 }}>
                <label className="form-label">Phone</label>
                <input className="form-input" type="tel" placeholder="+91 9999999999" {...register('phone')} />
              </div>
              <div className="form-group" style={{ flex: 1 }}>
                <label className="form-label">Email</label>
                <input className="form-input" type="email" placeholder="party@email.com" {...register('email')} />
              </div>
            </div>
            <div className="form-group">
              <label className="form-label">GSTIN</label>
              <input className="form-input" placeholder="22AAAAA0000A1Z5" {...register('gstin')} />
            </div>

            <h4 style={{ margin: '16px 0 8px', fontSize: 14, color: 'var(--accent-glow)' }}>Categorization & Reminders</h4>
            <div style={{ display: 'flex', gap: 8 }}>
              <div className="form-group" style={{ flex: 1 }}>
                <label className="form-label">Area</label>
                <input className="form-input" placeholder="e.g. North Zone" {...register('area')} />
              </div>
              <div className="form-group" style={{ flex: 1 }}>
                <label className="form-label">Reminder Date</label>
                <input className="form-input" type="date" {...register('reminder_date')} />
              </div>
            </div>

            <h4 style={{ margin: '16px 0 8px', fontSize: 14, color: 'var(--accent-glow)' }}>Billing Address</h4>
            <div className="form-group">
              <input className="form-input" placeholder="Line 1" {...register('billing_address_line1')} />
            </div>
            <div className="form-group">
              <input className="form-input" placeholder="Line 2" {...register('billing_address_line2')} />
            </div>
            <div style={{ display: 'flex', gap: 8 }}>
              <div className="form-group" style={{ flex: 1 }}>
                <input className="form-input" placeholder="Line 3" {...register('billing_address_line3')} />
              </div>
              <div className="form-group" style={{ flex: 1 }}>
                <input className="form-input" placeholder="City" {...register('billing_city')} />
              </div>
            </div>

            <h4 style={{ margin: '16px 0 8px', fontSize: 14, color: 'var(--accent-glow)' }}>Shipping Address</h4>
            <div className="form-group">
              <input className="form-input" placeholder="Line 1" {...register('shipping_address_line1')} />
            </div>
            <div className="form-group">
              <input className="form-input" placeholder="Line 2" {...register('shipping_address_line2')} />
            </div>
            <div style={{ display: 'flex', gap: 8 }}>
              <div className="form-group" style={{ flex: 1 }}>
                <input className="form-input" placeholder="Line 3" {...register('shipping_address_line3')} />
              </div>
              <div className="form-group" style={{ flex: 1 }}>
                <input className="form-input" placeholder="City" {...register('shipping_city')} />
              </div>
            </div>
          </div>
          
          <div style={{ display: 'flex', gap: 10, marginTop: 8 }}>
            <button type="button" className="btn btn-secondary" style={{ flex: 1 }} onClick={onClose}>Cancel</button>
            <button type="submit" className="btn btn-primary" style={{ flex: 1 }} disabled={loading}>
              {loading ? 'Saving…' : 'Save Changes'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ── Journal Entry Modal ──────────────────────────────────────────────────────────
function JournalModal({ partyId, onClose, onSuccess }: { partyId: number; onClose: () => void; onSuccess: () => void }) {
  const [form, setForm] = useState({
    amount: '',
    entry_date: new Date().toISOString().split('T')[0],
    description: '',
    type: 'charge' // charge = positive, discount = negative
  });
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState('');

  const set = (k: string) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => 
    setForm(f => ({ ...f, [k]: e.target.value }));

  const onSubmit = async () => {
    if (loading) return;
    if (!form.amount || Number(form.amount) <= 0) { setErr('Amount must be > 0'); return; }
    setLoading(true); setErr('');
    try {
      const finalAmount = form.type === 'charge' ? Number(form.amount) : -Number(form.amount);
      await partiesApi.addJournalEntry(partyId, {
        amount: finalAmount,
        entry_date: new Date(form.entry_date).toISOString(),
        description: form.description
      });
      onSuccess();
    } catch {
      setErr('Failed to save journal entry');
    } finally { setLoading(false); }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-sheet" onClick={e => e.stopPropagation()}>
        <div className="modal-handle" />
        <h2 className="modal-title">General Account Adjustment</h2>
        <p style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 16 }}>Use this to round-off balances, apply discounts, or charge penalties.</p>
        
        {err && <div style={{ color: 'var(--danger)', fontSize: 13, marginBottom: 12 }}>{err}</div>}

        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <div className="form-group" style={{ marginBottom: 0 }}>
            <label className="form-label">Type *</label>
            <div style={{ display: 'flex', gap: 8, marginTop: 4 }}>
              <button 
                className="btn" 
                style={{ flex: 1, padding: '10px 0', border: form.type === 'charge' ? '2px solid var(--warning)' : '1px solid var(--border)', background: form.type === 'charge' ? 'rgba(251,191,36,0.1)' : 'transparent', color: form.type === 'charge' ? 'var(--warning)' : 'var(--text-muted)' }}
                onClick={() => setForm({ ...form, type: 'charge' })}
              >
                Charge (+)
              </button>
              <button 
                className="btn" 
                style={{ flex: 1, padding: '10px 0', border: form.type === 'discount' ? '2px solid var(--success)' : '1px solid var(--border)', background: form.type === 'discount' ? 'rgba(34,211,165,0.1)' : 'transparent', color: form.type === 'discount' ? 'var(--success)' : 'var(--text-muted)' }}
                onClick={() => setForm({ ...form, type: 'discount' })}
              >
                Discount (-)
              </button>
            </div>
            <p style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 6 }}>
              {form.type === 'charge' ? 'Increases the party\'s due amount.' : 'Decreases the party\'s due amount.'}
            </p>
          </div>

          <div style={{ display: 'flex', gap: 12 }}>
            <div className="form-group" style={{ flex: 1, marginBottom: 0 }}>
              <label className="form-label">Amount *</label>
              <input className="form-input" type="number" step="0.01" placeholder="0.00" value={form.amount} onChange={set('amount')} />
            </div>
            <div className="form-group" style={{ flex: 1, marginBottom: 0 }}>
              <label className="form-label">Date *</label>
              <input className="form-input" type="date" value={form.entry_date} onChange={set('entry_date')} />
            </div>
          </div>
          
          <div className="form-group" style={{ marginBottom: 0 }}>
            <label className="form-label">Description</label>
            <input className="form-input" placeholder="e.g. Round off difference" value={form.description} onChange={set('description')} />
          </div>
        </div>

        <div style={{ display: 'flex', gap: 10, marginTop: 20 }}>
          <button type="button" className="btn btn-secondary" style={{ flex: 1 }} onClick={onClose}>Cancel</button>
          <button type="button" className="btn btn-primary" style={{ flex: 1 }} disabled={loading} onClick={onSubmit}>
            {loading ? 'Saving…' : 'Add Entry'}
          </button>
        </div>
      </div>
    </div>
  );
}
