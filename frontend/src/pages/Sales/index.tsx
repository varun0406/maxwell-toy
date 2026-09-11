import { useState } from 'react';
import { useForm, useFieldArray } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { invoicesApi, partiesApi, addressBookApi } from '../../api/endpoints';
import { formatCurrency, formatDate } from '../../utils/format';
import { Share as ShareIcon, Plus, ChevronLeft, X, Search, MapPin } from 'lucide-react';
import { generateAndShareInvoice } from '../../utils/pdfGenerator';
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
  items: z.array(itemSchema).min(1, 'At least one item required'),
});
type InvoiceForm = z.infer<typeof schema>;

// ── Invoice List ─────────────────────────────────────────────────────────────
export function InvoicesList() {
  const navigate = useNavigate();
  const [filter, setFilter] = useState<'all' | 'unpaid'>('all');
  const [search, setSearch] = useState('');

  const { data: invoices = [], isLoading } = useQuery({
    queryKey: ['invoices', filter],
    queryFn: () => invoicesApi.list(undefined, filter === 'unpaid').then((r) => r.data),
  });
  
  const { data: parties = [] } = useQuery({
    queryKey: ['parties'],
    queryFn: () => partiesApi.list().then(r => r.data)
  });

  const getPartyName = (id: number) => parties.find((p: any) => p.id === id)?.name || `Party #${id}`;

  const filtered = search
    ? invoices.filter((i: any) => 
        i.invoice_number?.toLowerCase().includes(search.toLowerCase()) ||
        getPartyName(i.party_id).toLowerCase().includes(search.toLowerCase())
      )
    : invoices;

  return (
    <div className="page-content">
      <div className="page-header">
        <h1 className="page-title">Invoices</h1>
        <p className="page-subtitle">{filtered.length} records</p>
      </div>

      <div className="search-bar">
        <Search size={16} />
        <input
          placeholder="Search invoice number…"
          value={search}
          onChange={e => setSearch(e.target.value)}
        />
        {search && <button onClick={() => setSearch('')} style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}><X size={14} /></button>}
      </div>

      <div className="chips">
        <button className={`chip ${filter === 'all' ? 'active' : ''}`} onClick={() => setFilter('all')}>All</button>
        <button className={`chip ${filter === 'unpaid' ? 'active' : ''}`} onClick={() => setFilter('unpaid')}>Unpaid</button>
      </div>

      {isLoading ? (
        <div className="loading-screen"><div className="spinner" /></div>
      ) : filtered.length === 0 ? (
        <div className="empty-state">
          <Plus size={48} />
          <h3>{search ? 'No matches' : 'No invoices yet'}</h3>
          <p>{search ? 'Try a different search' : 'Create your first invoice to get started'}</p>
        </div>
      ) : (
        <div className="list-container">
          {filtered.map((inv: any) => (
            <div key={inv.id} className="list-item">
              <div className="list-item-icon" style={{ background: inv.is_paid ? 'var(--success-bg)' : 'var(--warning-bg)' }}>
                {inv.is_paid ? '✅' : '📄'}
              </div>
              <div className="list-item-body">
                <p className="list-item-title">{getPartyName(inv.party_id)}</p>
                <p className="list-item-sub">{formatDate(inv.invoice_date)}{inv.due_date ? ` · Due ${formatDate(inv.due_date)}` : ''}</p>
              </div>
              <div className="list-item-right" style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 6 }}>
                <p style={{ fontWeight: 700, fontSize: 14, color: inv.is_paid ? 'var(--success)' : 'var(--warning)' }}>
                  {formatCurrency(inv.balance_due)}
                </p>
                <div style={{ display: 'flex', gap: 4 }}>
                  <button
                    className="btn-icon"
                    style={{ padding: 4, background: 'rgba(108,99,255,0.1)', color: 'var(--accent)' }}
                    onClick={async (e) => {
                      e.stopPropagation();
                      const party = (await partiesApi.get(inv.party_id)).data;
                      const fullInv = (await invoicesApi.get(inv.id)).data;
                      generateAndShareInvoice(fullInv, party);
                    }}
                  >
                    <ShareIcon size={14} />
                  </button>
                  <span className={`badge ${inv.is_paid ? 'badge-success' : 'badge-warning'}`}>
                    {inv.is_paid ? 'Paid' : 'Unpaid'}
                  </span>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      <button className="fab" onClick={() => navigate('/invoices/new')}>
        <Plus size={24} />
      </button>
    </div>
  );
}

// ── New Invoice Form ──────────────────────────────────────────────────────────
export function NewInvoice() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const qc = useQueryClient();
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState('');
  const [showAddressPicker, setShowAddressPicker] = useState<'billing' | 'shipping' | null>(null);
  const [addressSearch, setAddressSearch] = useState('');
  const [showNewAddressForm, setShowNewAddressForm] = useState(false);

  const { data: parties = [] } = useQuery({
    queryKey: ['parties'],
    queryFn: () => partiesApi.list().then((r) => r.data),
  });

  const { data: addressEntries = [] } = useQuery({
    queryKey: ['address-book', addressSearch],
    queryFn: () => addressBookApi.list(addressSearch || undefined).then(r => r.data),
    enabled: showAddressPicker !== null,
  });

  const today = new Date().toISOString().split('T')[0];
  const { register, control, handleSubmit, watch, formState: { errors }, setValue } = useForm<InvoiceForm>({
    resolver: zodResolver(schema),
    defaultValues: {
      party_id: searchParams.get('party') ? Number(searchParams.get('party')) : undefined,
      invoice_date: today,
      items: [{ item_name: '', meter: 0, rate: 0 }],
      due_days: 0,
    },
  });

  const { fields, append, remove } = useFieldArray({ control, name: 'items' });
  const watchItems = watch('items');
  const watchPartyId = watch('party_id');
  const totalAmount = watchItems?.reduce((sum, item) => sum + ((item.meter || 0) * (item.rate || 0)), 0) || 0;

  const partyOptions: ComboboxOption[] = parties.map((p: any) => ({
    value: p.id,
    label: p.name,
    sublabel: p.phone || p.billing_city || '',
  }));

  const handlePartySelect = (opt: ComboboxOption) => {
    setValue('party_id', Number(opt.value));
    const party = parties.find((p: any) => p.id === opt.value);
    if (party) {
      setValue('billing_address', [party.billing_address_line1, party.billing_address_line2, party.billing_address_line3, party.billing_city].filter(Boolean).join(', '));
      setValue('shipping_address', [party.shipping_address_line1, party.shipping_address_line2, party.shipping_address_line3, party.shipping_city].filter(Boolean).join(', '));
    }
  };

  const handleAddressSelect = (entry: any, type: 'billing' | 'shipping') => {
    const addr = [entry.address_line1, entry.address_line2, entry.city].filter(Boolean).join(', ');
    setValue(type === 'billing' ? 'billing_address' : 'shipping_address', addr);
    setShowAddressPicker(null);
    setAddressSearch('');
  };

  const onSubmit = async (data: InvoiceForm) => {
    setLoading(true); setErr('');
    try {
      let computedDueDate = undefined;
      if (data.due_days && data.due_days > 0) {
        const d = new Date(data.invoice_date);
        d.setDate(d.getDate() + data.due_days);
        computedDueDate = d.toISOString();
      }

      await invoicesApi.create({
        ...data,
        invoice_date: new Date(data.invoice_date).toISOString(),
        due_date: computedDueDate,
      });
      qc.invalidateQueries({ queryKey: ['invoices'] });
      qc.invalidateQueries({ queryKey: ['dashboard'] });
      navigate(-1);
    } catch (e: any) {
      setErr(e.response?.data?.detail || 'Failed to create invoice');
    } finally { setLoading(false); }
  };

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', background: 'var(--bg-base)' }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '20px 20px 16px', borderBottom: '1px solid var(--border)' }}>
        <button className="btn-icon btn" onClick={() => navigate(-1)}><ChevronLeft size={20} /></button>
        <h1 className="page-title">New Invoice</h1>
      </div>

      <div className="page-content" style={{ paddingTop: 20, paddingLeft: 20, paddingRight: 20 }}>
        {err && <div style={{ color: 'var(--danger)', fontSize: 13, marginBottom: 12 }}>{err}</div>}
        <form onSubmit={handleSubmit(onSubmit)}>

          {/* Party — searchable */}
          <div className="form-group">
            <label className="form-label">Party *</label>
            <SearchCombobox
              value={watchPartyId || null}
              placeholder="Select party…"
              options={partyOptions}
              onChange={handlePartySelect}
            />
            {errors.party_id && <span className="form-error">{errors.party_id.message}</span>}
          </div>

          {/* Billing Address */}
          <div className="form-group">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
              <label className="form-label" style={{ margin: 0 }}>Billing Address</label>
              <button type="button" style={{ fontSize: 11, color: 'var(--accent)', background: 'none', border: 'none', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4 }} onClick={() => { setAddressSearch(''); setShowAddressPicker('billing'); }}>
                <MapPin size={12} /> From Address Book
              </button>
            </div>
            <textarea className="form-textarea" rows={2} {...register('billing_address')} />
          </div>

          {/* Shipping Address */}
          <div className="form-group">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
              <label className="form-label" style={{ margin: 0 }}>Shipping Address</label>
              <button type="button" style={{ fontSize: 11, color: 'var(--accent)', background: 'none', border: 'none', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4 }} onClick={() => { setAddressSearch(''); setShowAddressPicker('shipping'); }}>
                <MapPin size={12} /> From Address Book
              </button>
            </div>
            <textarea className="form-textarea" rows={2} {...register('shipping_address')} />
          </div>

          {/* Items */}
          <h4 style={{ margin: '16px 0 8px', fontSize: 14, color: 'var(--accent-light)' }}>Items</h4>
          {fields.map((field, index) => (
            <div key={field.id} style={{ background: 'var(--bg-elevated)', padding: 12, borderRadius: 12, marginBottom: 12, position: 'relative' }}>
              {index > 0 && (
                <button type="button" onClick={() => remove(index)} style={{ position: 'absolute', top: 8, right: 8, background: 'none', border: 'none', color: 'var(--danger)', cursor: 'pointer' }}>
                  <X size={16} />
                </button>
              )}
              <div className="form-group" style={{ marginBottom: 8 }}>
                <label className="form-label">Item Name</label>
                <ItemAutocomplete
                  value={watchItems[index]?.item_name || ''}
                  onChange={(name, rate) => {
                    setValue(`items.${index}.item_name`, name);
                    if (rate !== undefined && rate > 0) setValue(`items.${index}.rate`, rate);
                  }}
                />
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
                  <div style={{ padding: '12px 0', fontWeight: 600, color: 'var(--accent-light)' }}>
                    {formatCurrency((watchItems[index]?.meter || 0) * (watchItems[index]?.rate || 0))}
                  </div>
                </div>
              </div>
            </div>
          ))}
          <button type="button" className="btn btn-secondary" style={{ width: '100%', marginBottom: 16 }} onClick={() => append({ item_name: '', meter: 0, rate: 0 })}>
            <Plus size={16} /> Add Item
          </button>

          {/* Grand Total */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '16px', background: 'rgba(108,99,255,0.1)', borderRadius: 12, marginBottom: 16 }}>
            <span style={{ fontWeight: 600, color: 'var(--text-muted)' }}>Grand Total</span>
            <span style={{ fontSize: 20, fontWeight: 800, color: 'var(--accent-light)' }}>{formatCurrency(totalAmount)}</span>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
            <div className="form-group">
              <label className="form-label">Invoice Date *</label>
              <input className="form-input" type="date" {...register('invoice_date')} />
            </div>
            <div className="form-group">
              <label className="form-label">Due in Days</label>
              <input className="form-input" type="number" placeholder="e.g. 30" {...register('due_days')} />
            </div>
          </div>

          <div className="form-group">
            <label className="form-label">Description</label>
            <textarea className="form-textarea" placeholder="Goods/services description…" {...register('description')} />
          </div>

          <button type="submit" className="btn btn-primary btn-full" disabled={loading} style={{ marginTop: 8 }}>
            {loading ? 'Creating…' : 'Create Invoice'}
          </button>
        </form>
      </div>

      {/* Address Picker Modal */}
      {showAddressPicker && (
        <div className="modal-overlay" onClick={() => setShowAddressPicker(null)}>
          <div className="modal-sheet" style={{ height: '80vh', display: 'flex', flexDirection: 'column' }} onClick={e => e.stopPropagation()}>
            <div className="modal-handle" />
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
              <h2 className="modal-title" style={{ margin: 0 }}>Select {showAddressPicker === 'billing' ? 'Billing' : 'Shipping'} Address</h2>
              <button className="btn btn-sm btn-primary" onClick={() => setShowNewAddressForm(true)}>
                <Plus size={14} /> New
              </button>
            </div>

            <div className="search-bar" style={{ margin: '0 0 16px' }}>
              <Search size={16} />
              <input
                placeholder="Search name, phone or city…"
                value={addressSearch}
                onChange={e => setAddressSearch(e.target.value)}
                autoFocus
              />
              {addressSearch && <button onClick={() => setAddressSearch('')} style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}><X size={14} /></button>}
            </div>

            <div style={{ flex: 1, overflowY: 'auto' }}>
              {addressEntries.length === 0 ? (
                <div className="empty-state" style={{ padding: '32px 0' }}>
                  <MapPin size={36} />
                  <p>No addresses found</p>
                </div>
              ) : (
                addressEntries.map((entry: any) => (
                  <div
                    key={entry.id}
                    onClick={() => handleAddressSelect(entry, showAddressPicker!)}
                    style={{ padding: '14px 4px', borderBottom: '1px solid var(--border)', cursor: 'pointer' }}
                  >
                    <p style={{ fontWeight: 600, fontSize: 14 }}>{entry.name}</p>
                    <p style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 2 }}>
                      {[entry.address_line1, entry.address_line2, entry.city].filter(Boolean).join(', ')}
                    </p>
                    {entry.phone && <p style={{ fontSize: 11, color: 'var(--accent)', marginTop: 2 }}>{entry.phone}</p>}
                  </div>
                ))
              )}
            </div>

            <button className="btn btn-secondary" style={{ marginTop: 12 }} onClick={() => setShowAddressPicker(null)}>
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* New Address Form Modal */}
      {showNewAddressForm && (
        <AddressFormModal
          initial={null}
          onClose={() => setShowNewAddressForm(false)}
          onSuccess={() => {
            setShowNewAddressForm(false);
            qc.invalidateQueries({ queryKey: ['address-book'] });
            // Optionally could auto-select, but for now just refresh list
          }}
        />
      )}
    </div>
  );
}
