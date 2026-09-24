import { useState, useEffect } from 'react';
import { useForm, useFieldArray } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { invoicesApi, partiesApi, addressBookApi } from '../../api/endpoints';
import { formatCurrency, formatDate } from '../../utils/format';
import { Share as ShareIcon, Plus, ChevronLeft, X, Search, MapPin, Edit2, Trash2, Image as ImageIcon, Copy, CreditCard, Filter } from 'lucide-react';
import { generateAndShareInvoice } from '../../utils/pdfGenerator';
import { SecureActionModal } from '../../components/SecureActionModal';
import { SearchCombobox } from '../../components/SearchCombobox';
import type { ComboboxOption } from '../../components/SearchCombobox';
import { ItemAutocomplete } from '../../components/ItemAutocomplete';
import { AddressFormModal } from '../AddressBook';

const itemSchema = z.object({
  item_name: z.string().min(1, 'Required'),
  meter: z.coerce.number().min(0.01, 'Required'),
  rate: z.coerce.number().min(0.01, 'Required'),
});

const schema = z.object({
  party_id: z.coerce.number().min(1, 'Select a party'),
  invoice_number: z.string().optional(),
  description: z.string().optional(),
  invoice_date: z.string().min(1, 'Date required'),
  due_days: z.coerce.number().min(0, 'Must be >= 0').optional(),
  billing_address: z.string().optional(),
  shipping_address: z.string().optional(),
  delivery_challan_url: z.string().optional(),
  items: z.array(itemSchema).min(1, 'At least one item required'),
});
type InvoiceForm = z.infer<typeof schema>;

// Helpers
function getPaymentStatus(inv: any): 'paid' | 'partial' | 'unpaid' {
  if (inv.is_paid) return 'paid';
  if (Number(inv.balance_due) < Number(inv.amount)) return 'partial';
  return 'unpaid';
}

function getDateRange(filter: string): { from: string; to: string } | null {
  const now = new Date();
  const pad = (n: number) => String(n).padStart(2, '0');
  const fmt = (d: Date) => d.getFullYear() + '-' + pad(d.getMonth() + 1) + '-' + pad(d.getDate());
  if (filter === 'today') { const t = fmt(now); return { from: t, to: t }; }
  if (filter === 'week') { const s = new Date(now); s.setDate(now.getDate() - now.getDay()); return { from: fmt(s), to: fmt(now) }; }
  if (filter === 'month') { const s = new Date(now.getFullYear(), now.getMonth(), 1); return { from: fmt(s), to: fmt(now) }; }
  return null;
}

// Invoice List
export function InvoicesList() {
  const navigate = useNavigate();
  const [filter, setFilter] = useState<'all' | 'unpaid'>('all');
  const [search, setSearch] = useState('');
  const [dateFilter, setDateFilter] = useState<'all' | 'today' | 'week' | 'month' | 'custom'>('all');
  const [customFrom, setCustomFrom] = useState('');
  const [customTo, setCustomTo] = useState('');
  const [showAmountFilter, setShowAmountFilter] = useState(false);
  const [minAmount, setMinAmount] = useState('');
  const [maxAmount, setMaxAmount] = useState('');
  const [page, setPage] = useState(0);
  const PAGE_SIZE = 20;

  // Reset to page 0 when any filter changes
  useEffect(() => { setPage(0); }, [filter, search, dateFilter, customFrom, customTo, minAmount, maxAmount]);

  const dateRange = dateFilter === 'custom'
    ? (customFrom || customTo ? { from: customFrom, to: customTo } : null)
    : getDateRange(dateFilter);

  const { data, isLoading } = useQuery({
    queryKey: ['invoices', filter, search, dateFilter, customFrom, customTo, minAmount, maxAmount, page],
    queryFn: () =>
      invoicesApi.list(
        undefined, filter === 'unpaid', search, page * PAGE_SIZE, PAGE_SIZE,
        dateRange?.from || undefined,
        dateRange?.to ? dateRange.to + 'T23:59:59' : undefined,
        minAmount ? parseFloat(minAmount) : undefined,
        maxAmount ? parseFloat(maxAmount) : undefined,
      ).then(r => r.data),
  });

  const invoices = data?.items || [];
  const totalCount = data?.total || 0;
  const summaryTotal = data?.summary_total || 0;
  const totalPages = Math.ceil(totalCount / PAGE_SIZE);
  const qc = useQueryClient();
  const [secureAction, setSecureAction] = useState<{ type: 'edit' | 'delete', id: number } | null>(null);

  const DATE_CHIPS = [
    { id: 'all' as const, label: 'All Time' },
    { id: 'today' as const, label: 'Today' },
    { id: 'week' as const, label: 'This Week' },
    { id: 'month' as const, label: 'This Month' },
    { id: 'custom' as const, label: 'Custom' },
  ];

  return (
    <div className="page-content">
      <div className="page-header">
        <h1 className="page-title">Invoices</h1>
        <p className="page-subtitle">{totalCount} records · {formatCurrency(summaryTotal)}</p>
      </div>

      <div className="search-bar">
        <Search size={16} />
        <input placeholder="Search invoice # or party…" value={search} onChange={e => setSearch(e.target.value)} />
        {search && <button onClick={() => setSearch('')} style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}><X size={14} /></button>}
        <button onClick={() => setShowAmountFilter(s => !s)} style={{ background: 'none', border: 'none', color: showAmountFilter ? 'var(--accent)' : 'var(--text-muted)', cursor: 'pointer', padding: '0 4px' }} title="Filter by amount">
          <Filter size={14} />
        </button>
      </div>

      {showAmountFilter && (
        <div style={{ display: 'flex', gap: 8, padding: '0 20px', marginBottom: 8 }}>
          <input className="form-input" type="number" placeholder="Min ₹" value={minAmount} onChange={e => setMinAmount(e.target.value)} style={{ flex: 1, padding: '8px 10px', fontSize: 13 }} />
          <input className="form-input" type="number" placeholder="Max ₹" value={maxAmount} onChange={e => setMaxAmount(e.target.value)} style={{ flex: 1, padding: '8px 10px', fontSize: 13 }} />
          {(minAmount || maxAmount) && <button onClick={() => { setMinAmount(''); setMaxAmount(''); }} style={{ background: 'none', border: 'none', color: 'var(--danger)', cursor: 'pointer' }}><X size={14} /></button>}
        </div>
      )}

      <div className="chips">
        <button className={`chip ${filter === 'all' ? 'active' : ''}`} onClick={() => setFilter('all')}>All</button>
        <button className={`chip ${filter === 'unpaid' ? 'active' : ''}`} onClick={() => setFilter('unpaid')}>Unpaid</button>
      </div>

      {/* F4: Date filter chips */}
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
      ) : invoices.length === 0 ? (
        <div className="empty-state">
          <Plus size={48} />
          <h3>{search ? 'No matches' : 'No invoices yet'}</h3>
          <p>{search ? 'Try a different search' : 'Create your first invoice to get started'}</p>
        </div>
      ) : (
        <div className="list-container">
          {invoices.map((inv: any) => {
            const status = getPaymentStatus(inv);
            const pct = Number(inv.amount) > 0 ? Math.round((1 - Number(inv.balance_due) / Number(inv.amount)) * 100) : 100;
            return (
              <div key={inv.id} className="list-item">
                <div className="list-item-icon" style={{ background: status === 'paid' ? 'var(--success-bg)' : status === 'partial' ? 'rgba(245,158,11,0.12)' : 'var(--warning-bg)' }}>
                  {status === 'paid' ? '✅' : status === 'partial' ? '⏳' : '📄'}
                </div>
                <div className="list-item-body">
                  <p className="list-item-title">{inv.party_name}</p>
                  <p className="list-item-sub" style={{ fontSize: 11 }}>{inv.invoice_number} · {formatDate(inv.invoice_date)}{inv.due_date ? ` · Due ${formatDate(inv.due_date)}` : ''}</p>
                  {status !== 'paid' && (
                    <p style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>
                      Invoice: <span style={{ color: 'var(--text-secondary)' }}>{formatCurrency(inv.amount)}</span>
                      {status === 'partial' && <> · Paid: <span style={{ color: 'var(--success)' }}>{formatCurrency(Number(inv.amount) - Number(inv.balance_due))}</span></>}
                    </p>
                  )}
                  {status === 'partial' && (
                    <div style={{ marginTop: 4, height: 4, borderRadius: 2, background: 'var(--border)', overflow: 'hidden', width: '100%' }}>
                      <div style={{ height: '100%', width: `${pct}%`, background: 'var(--success)', borderRadius: 2 }} />
                    </div>
                  )}
                  {inv.delivery_challan_url && <a href={inv.delivery_challan_url} target="_blank" rel="noreferrer" style={{ fontSize: 11, color: 'var(--accent)', fontWeight: 600, display: 'inline-block', marginTop: 2 }}>📎 Challan</a>}
                </div>
                <div className="list-item-right" style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 4 }}>
                  <span className="badge" style={{ background: status === 'paid' ? 'var(--success-bg)' : status === 'partial' ? 'rgba(245,158,11,0.15)' : 'var(--warning-bg)', color: status === 'paid' ? 'var(--success)' : status === 'partial' ? '#f59e0b' : 'var(--warning)', fontSize: 10 }}>
                    {status === 'paid' ? 'Paid' : status === 'partial' ? 'Partial' : 'Unpaid'}
                  </span>
                  <p style={{ fontWeight: 700, fontSize: 14, color: status === 'paid' ? 'var(--success)' : 'var(--warning)' }}>
                    {formatCurrency(status === 'paid' ? inv.amount : inv.balance_due)}
                  </p>
                  <p style={{ fontSize: 10, color: 'var(--text-muted)' }}>{status === 'paid' ? 'total' : 'due'}</p>
                  <div style={{ display: 'flex', gap: 3, flexWrap: 'wrap', justifyContent: 'flex-end' }}>
                    <button className="btn-icon" style={{ padding: 4, background: 'rgba(108,99,255,0.1)', color: 'var(--accent)' }} onClick={e => { e.stopPropagation(); setSecureAction({ type: 'edit', id: inv.id }); }}><Edit2 size={13} /></button>
                    <button className="btn-icon" style={{ padding: 4, background: 'rgba(239,68,68,0.1)', color: 'var(--danger)' }} onClick={e => { e.stopPropagation(); setSecureAction({ type: 'delete', id: inv.id }); }}><Trash2 size={13} /></button>
                    <button className="btn-icon" style={{ padding: 4, background: 'rgba(108,99,255,0.1)', color: 'var(--accent)' }} onClick={async e => { e.stopPropagation(); const party = (await partiesApi.get(inv.party_id)).data; const fullInv = (await invoicesApi.get(inv.id)).data; generateAndShareInvoice(fullInv, party); }}><ShareIcon size={13} /></button>
                    <button className="btn-icon" title="Duplicate invoice" style={{ padding: 4, background: 'rgba(16,185,129,0.1)', color: 'var(--success)' }} onClick={e => { e.stopPropagation(); navigate(`/invoices/new?duplicate=${inv.id}`); }}><Copy size={13} /></button>
                    {status !== 'paid' && (
                      <button className="btn-icon" title="Receive full payment" style={{ padding: 4, background: 'rgba(16,185,129,0.2)', color: 'var(--success)' }} onClick={e => { e.stopPropagation(); navigate(`/payments/new?party=${inv.party_id}&invoice=${inv.id}&amount=${inv.balance_due}`); }}><CreditCard size={13} /></button>
                    )}
                    {inv.delivery_challan_url && <button className="btn-icon" style={{ padding: 4, background: 'rgba(59,130,246,0.1)', color: '#3b82f6' }} onClick={e => { e.stopPropagation(); window.open(inv.delivery_challan_url, '_blank'); }}><ImageIcon size={13} /></button>}
                  </div>
                </div>
              </div>
            );
          })}
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

      <button className="fab" onClick={() => navigate('/invoices/new')}><Plus size={24} /></button>

      <SecureActionModal
        isOpen={secureAction !== null}
        onClose={() => setSecureAction(null)}
        title={secureAction?.type === 'edit' ? 'Edit Invoice' : 'Hide Invoice'}
        message={secureAction?.type === 'edit' ? 'Enter Master PIN to edit this invoice.' : 'Enter Master PIN to hide this invoice. Balances will be recalibrated.'}
        onConfirm={async () => {
          if (secureAction?.type === 'edit') navigate(`/invoices/new?edit=${secureAction.id}`);
          else if (secureAction?.type === 'delete') { await invoicesApi.delete(secureAction.id); qc.invalidateQueries(); }
          setSecureAction(null);
        }}
      />
    </div>
  );
}

// New Invoice Form
export function NewInvoice() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const qc = useQueryClient();
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState('');
  const [suggestedNumber, setSuggestedNumber] = useState('');
  const [showAddressPicker, setShowAddressPicker] = useState<'billing' | 'shipping' | null>(null);
  const [addressSearch, setAddressSearch] = useState('');
  const [showNewAddressForm, setShowNewAddressForm] = useState(false);
  const [uploadingChallan, setUploadingChallan] = useState(false);

  const editId = searchParams.get('edit') ? Number(searchParams.get('edit')) : null;
  const duplicateId = searchParams.get('duplicate') ? Number(searchParams.get('duplicate')) : null;

  const { data: editInvoice } = useQuery({ queryKey: ['invoice', editId], queryFn: () => invoicesApi.get(editId!).then(r => r.data), enabled: !!editId });
  const { data: duplicateInvoice } = useQuery({ queryKey: ['invoice', duplicateId], queryFn: () => invoicesApi.get(duplicateId!).then(r => r.data), enabled: !!duplicateId && !editId });

  const [partySearch, setPartySearch] = useState('');
  const { data: parties = [] } = useQuery({ queryKey: ['parties', partySearch], queryFn: () => partiesApi.list(partySearch, 0, 100).then(r => r.data.items) });
  const { data: addressEntries = [] } = useQuery({ queryKey: ['address-book', addressSearch], queryFn: () => addressBookApi.list(addressSearch || undefined).then(r => r.data), enabled: showAddressPicker !== null });

  const today = new Date().toISOString().split('T')[0];
  const { register, control, handleSubmit, watch, formState: { errors }, setValue } = useForm<InvoiceForm>({
    resolver: zodResolver(schema),
    defaultValues: { party_id: searchParams.get('party') ? Number(searchParams.get('party')) : undefined, invoice_date: today, items: [{ item_name: '', meter: 0, rate: 0 }], due_days: 0 },
  });

  useEffect(() => {
    if (editInvoice) {
      setValue('party_id', editInvoice.party_id);
      setValue('invoice_number', editInvoice.invoice_number);
      setValue('invoice_date', editInvoice.invoice_date.split('T')[0]);
      if (editInvoice.due_date) { const diff = new Date(editInvoice.due_date).getTime() - new Date(editInvoice.invoice_date).getTime(); setValue('due_days', Math.max(0, Math.ceil(diff / 86400000))); }
      else setValue('due_days', 0);
      setValue('description', editInvoice.description || '');
      setValue('billing_address', editInvoice.billing_address || '');
      setValue('shipping_address', editInvoice.shipping_address || '');
      if (editInvoice.items?.length > 0) setValue('items', editInvoice.items.map((i: any) => ({ item_name: i.item_name, meter: i.meter, rate: i.rate })));
      if (editInvoice.delivery_challan_url) setValue('delivery_challan_url', editInvoice.delivery_challan_url);
    }
  }, [editInvoice, setValue]);

  useEffect(() => {
    if (duplicateInvoice && !editId) {
      setValue('party_id', duplicateInvoice.party_id);
      setValue('invoice_date', today);
      setValue('description', duplicateInvoice.description || '');
      setValue('billing_address', duplicateInvoice.billing_address || '');
      setValue('shipping_address', duplicateInvoice.shipping_address || '');
      if (duplicateInvoice.items?.length > 0) setValue('items', duplicateInvoice.items.map((i: any) => ({ item_name: i.item_name, meter: i.meter, rate: i.rate })));
    }
  }, [duplicateInvoice, editId, setValue, today]);

  const { fields, append, remove } = useFieldArray({ control, name: 'items' });
  const watchItems = watch('items');
  const watchPartyId = watch('party_id');
  const totalAmount = watchItems?.reduce((s, i) => s + ((i.meter || 0) * (i.rate || 0)), 0) || 0;

  const partyOptions: ComboboxOption[] = (Array.isArray(parties) ? parties : []).map((p: any) => ({ value: p.id, label: p.name, sublabel: p.phone || p.billing_city || '' }));

  const handlePartySelect = (opt: ComboboxOption) => {
    setValue('party_id', Number(opt.value));
    const party = parties.find((p: any) => p.id === opt.value);
    if (party) {
      setValue('billing_address', [party.billing_address_line1, party.billing_address_line2, party.billing_address_line3, party.billing_city].filter(Boolean).join(', '));
      setValue('shipping_address', [party.shipping_address_line1, party.shipping_address_line2, party.shipping_address_line3, party.shipping_city].filter(Boolean).join(', '));
    }
  };

  const handleAddressSelect = (entry: any, type: 'billing' | 'shipping') => {
    setValue(type === 'billing' ? 'billing_address' : 'shipping_address', [entry.address_line1, entry.address_line2, entry.city].filter(Boolean).join(', '));
    setShowAddressPicker(null); setAddressSearch('');
  };

  const onSubmit = async (data: InvoiceForm) => {
    if (loading) return;
    setLoading(true); setErr(''); setSuggestedNumber('');
    try {
      let computedDueDate: string | undefined;
      if (data.due_days && data.due_days > 0) { const d = new Date(data.invoice_date); d.setDate(d.getDate() + data.due_days); computedDueDate = d.toISOString(); }
      const payload = { ...data, invoice_date: new Date(data.invoice_date).toISOString(), due_date: computedDueDate };
      if (editId) await invoicesApi.update(editId, payload);
      else await invoicesApi.create(payload);
      qc.invalidateQueries();
      navigate(-1);
    } catch (e: any) {
      const detail = e.response?.data?.detail || 'Failed to save invoice';
      setErr(detail);
      // F7: Parse suggested next number from conflict error
      const invMatch = detail.match(/INV[\/\-][^\s'"]+/);
      if (invMatch) {
        const parts = invMatch[0].split(/[\/\-]/);
        const num = parseInt(parts[parts.length - 1], 10);
        if (!isNaN(num)) {
          const sep = invMatch[0].includes('/') ? '/' : '-';
          const suggested = parts.slice(0, -1).join(sep) + sep + String(num + 1).padStart(parts[parts.length - 1].length, '0');
          setSuggestedNumber(suggested);
        }
      }
    } finally { setLoading(false); }
  };

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', background: 'var(--bg-base)' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '20px 20px 16px', borderBottom: '1px solid var(--border)' }}>
        <button className="btn-icon btn" onClick={() => navigate(-1)}><ChevronLeft size={20} /></button>
        <h1 className="page-title">{editId ? 'Edit Invoice' : duplicateId ? 'Duplicate Invoice' : 'New Invoice'}</h1>
      </div>

      <div className="page-content" style={{ paddingTop: 20, paddingLeft: 20, paddingRight: 20 }}>
        {err && (
          <div style={{ color: 'var(--danger)', fontSize: 13, marginBottom: 8 }}>
            {err}
            {suggestedNumber && (
              <span> Use <button type="button" onClick={() => { setValue('invoice_number', suggestedNumber); setErr(''); setSuggestedNumber(''); }} style={{ background: 'none', border: 'none', color: 'var(--accent)', cursor: 'pointer', fontWeight: 700, fontSize: 13, textDecoration: 'underline' }}>{suggestedNumber}</button>?</span>
            )}
          </div>
        )}
        <form onSubmit={handleSubmit(onSubmit)}>
          <div className="form-group">
            <label className="form-label">Party *</label>
            <SearchCombobox value={watchPartyId || null} placeholder="Select party…" options={partyOptions} onChange={handlePartySelect} onSearch={setPartySearch} />
            {errors.party_id && <span className="form-error">{errors.party_id.message}</span>}
          </div>

          <div className="form-group">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
              <label className="form-label" style={{ margin: 0 }}>Billing Address</label>
              <button type="button" style={{ fontSize: 11, color: 'var(--accent)', background: 'none', border: 'none', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4 }} onClick={() => { setAddressSearch(''); setShowAddressPicker('billing'); }}><MapPin size={12} /> From Address Book</button>
            </div>
            <textarea className="form-textarea" rows={2} {...register('billing_address')} />
          </div>

          <div className="form-group">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
              <label className="form-label" style={{ margin: 0 }}>Shipping Address</label>
              <button type="button" style={{ fontSize: 11, color: 'var(--accent)', background: 'none', border: 'none', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4 }} onClick={() => { setAddressSearch(''); setShowAddressPicker('shipping'); }}><MapPin size={12} /> From Address Book</button>
            </div>
            <textarea className="form-textarea" rows={2} {...register('shipping_address')} />
          </div>

          <h4 style={{ margin: '16px 0 8px', fontSize: 14, color: 'var(--accent-light)' }}>Items</h4>
          {fields.map((field, index) => (
            <div key={field.id} style={{ background: 'var(--bg-elevated)', padding: 12, borderRadius: 12, marginBottom: 12, position: 'relative' }}>
              {index > 0 && <button type="button" onClick={() => remove(index)} style={{ position: 'absolute', top: 8, right: 8, background: 'none', border: 'none', color: 'var(--danger)', cursor: 'pointer' }}><X size={16} /></button>}
              <div className="form-group" style={{ marginBottom: 8 }}>
                <label className="form-label">Item Name</label>
                <ItemAutocomplete value={watchItems[index]?.item_name || ''} onChange={(name, rate) => { setValue(`items.${index}.item_name`, name); if (rate !== undefined && rate > 0) setValue(`items.${index}.rate`, rate); }} />
                {errors.items?.[index]?.item_name && <span className="form-error">{errors.items[index]?.item_name?.message}</span>}
              </div>
              <div style={{ display: 'flex', gap: 8 }}>
                <div className="form-group" style={{ flex: 1, marginBottom: 0 }}>
                  <label className="form-label">Meter / Qty</label>
                  <input className="form-input" type="number" step="0.01" {...register(`items.${index}.meter`)} />
                </div>
                <div className="form-group" style={{ flex: 1, marginBottom: 0 }}>
                  <label className="form-label">Rate</label>
                  <input className="form-input" type="number" step="0.01" {...register(`items.${index}.rate`)} />
                </div>
                <div className="form-group" style={{ flex: 1, marginBottom: 0 }}>
                  <label className="form-label">Total</label>
                  <div style={{ padding: '12px 0', fontWeight: 600, color: 'var(--accent-light)' }}>{formatCurrency((watchItems[index]?.meter || 0) * (watchItems[index]?.rate || 0))}</div>
                </div>
              </div>
            </div>
          ))}
          <button type="button" className="btn btn-secondary" style={{ width: '100%', marginBottom: 16 }} onClick={() => append({ item_name: '', meter: 0, rate: 0 })}><Plus size={16} /> Add Item</button>

          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: 16, background: 'rgba(108,99,255,0.1)', borderRadius: 12, marginBottom: 16 }}>
            <span style={{ fontWeight: 600, color: 'var(--text-muted)' }}>Grand Total</span>
            <span style={{ fontSize: 20, fontWeight: 800, color: 'var(--accent-light)' }}>{formatCurrency(totalAmount)}</span>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
            <div className="form-group"><label className="form-label">Invoice Date *</label><input className="form-input" type="date" {...register('invoice_date')} /></div>
            <div className="form-group"><label className="form-label">Due in Days</label><input className="form-input" type="number" placeholder="e.g. 30" {...register('due_days')} /></div>
          </div>

          <div className="form-group"><label className="form-label">Invoice Number (auto if blank)</label><input className="form-input" placeholder="Auto-generated…" {...register('invoice_number')} /></div>
          <div className="form-group"><label className="form-label">Description</label><textarea className="form-textarea" placeholder="Goods/services description…" {...register('description')} /></div>

          <div className="form-group">
            <label className="form-label">Delivery Challan</label>
            <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
              <input type="file" accept="image/*" capture="environment" id="challan-camera" style={{ display: 'none' }} onChange={async e => { if (e.target.files?.[0]) { setUploadingChallan(true); try { const res = await invoicesApi.upload(e.target.files[0]); setValue('delivery_challan_url', res.data.url); } catch { alert("Upload failed"); } finally { setUploadingChallan(false); } } }} />
              <input type="file" accept="image/*,.pdf" id="challan-file" style={{ display: 'none' }} onChange={async e => { if (e.target.files?.[0]) { setUploadingChallan(true); try { const res = await invoicesApi.upload(e.target.files[0]); setValue('delivery_challan_url', res.data.url); } catch { alert("Upload failed"); } finally { setUploadingChallan(false); } } }} />
              <button type="button" className="btn btn-secondary" style={{ flex: 1 }} onClick={() => document.getElementById('challan-camera')?.click()}>Take Photo</button>
              <button type="button" className="btn btn-secondary" style={{ flex: 1 }} onClick={() => document.getElementById('challan-file')?.click()}>Upload File</button>
              {watch('delivery_challan_url') && <a href={watch('delivery_challan_url')} target="_blank" rel="noreferrer" style={{ fontSize: 13, color: 'var(--accent)', fontWeight: 600 }}>View</a>}
              {uploadingChallan && <div className="spinner" style={{ width: 20, height: 20 }} />}
            </div>
          </div>

          <button type="submit" className="btn btn-primary btn-full" disabled={loading} style={{ marginTop: 8 }}>
            {loading ? 'Saving…' : editId ? 'Update Invoice' : duplicateId ? 'Create Duplicate' : 'Create Invoice'}
          </button>
        </form>
      </div>

      {showAddressPicker && (
        <div className="modal-overlay" onClick={() => setShowAddressPicker(null)}>
          <div className="modal-sheet" style={{ height: '80vh', display: 'flex', flexDirection: 'column' }} onClick={e => e.stopPropagation()}>
            <div className="modal-handle" />
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
              <h2 className="modal-title" style={{ margin: 0 }}>Select {showAddressPicker === 'billing' ? 'Billing' : 'Shipping'} Address</h2>
              <button className="btn btn-sm btn-primary" onClick={() => setShowNewAddressForm(true)}><Plus size={14} /> New</button>
            </div>
            <div className="search-bar" style={{ margin: '0 0 16px' }}>
              <Search size={16} />
              <input placeholder="Search…" value={addressSearch} onChange={e => setAddressSearch(e.target.value)} autoFocus />
              {addressSearch && <button onClick={() => setAddressSearch('')} style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}><X size={14} /></button>}
            </div>
            <div style={{ flex: 1, overflowY: 'auto' }}>
              {(Array.isArray(addressEntries) ? addressEntries : []).map((entry: any) => (
                <div key={entry.id} onClick={() => handleAddressSelect(entry, showAddressPicker!)} style={{ padding: '14px 4px', borderBottom: '1px solid var(--border)', cursor: 'pointer' }}>
                  <p style={{ fontWeight: 600, fontSize: 14 }}>{entry.name}</p>
                  <p style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 2 }}>{[entry.address_line1, entry.address_line2, entry.city].filter(Boolean).join(', ')}</p>
                  {entry.phone && <p style={{ fontSize: 11, color: 'var(--accent)', marginTop: 2 }}>{entry.phone}</p>}
                </div>
              ))}
            </div>
            <button className="btn btn-secondary" style={{ marginTop: 12 }} onClick={() => setShowAddressPicker(null)}>Cancel</button>
          </div>
        </div>
      )}

      {showNewAddressForm && <AddressFormModal initial={null} onClose={() => setShowNewAddressForm(false)} onSuccess={() => { setShowNewAddressForm(false); qc.invalidateQueries(); }} />}
    </div>
  );
}
