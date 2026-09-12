import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { addressBookApi } from '../../api/endpoints';
import { Plus, Search, X, Phone, MapPin, Pencil, Trash2 } from 'lucide-react';

export interface AddressEntry {
  id: number;
  name: string;
  phone: string;
  address_line1: string;
  address_line2?: string;
  city: string;
}

// ── Address Book List ─────────────────────────────────────────────────────────
export default function AddressBook() {
  const [search, setSearch] = useState('');
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<AddressEntry | null>(null);
  const qc = useQueryClient();

  const { data: entries = [], isLoading } = useQuery({
    queryKey: ['address-book', search],
    queryFn: () => addressBookApi.list(search || undefined).then(r => r.data),
  });

  const handleDelete = async (id: number) => {
    await addressBookApi.delete(id);
    qc.invalidateQueries();
  };

  return (
    <div className="page-content">
      <div className="page-header">
        <h1 className="page-title">Address Book</h1>
        <p className="page-subtitle">{entries.length} delivery addresses</p>
      </div>

      <div className="search-bar">
        <Search size={16} />
        <input
          placeholder="Search by name, phone or city…"
          value={search}
          onChange={e => setSearch(e.target.value)}
        />
        {search && (
          <button onClick={() => setSearch('')} style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}>
            <X size={14} />
          </button>
        )}
      </div>

      {isLoading ? (
        <div className="loading-screen"><div className="spinner" /></div>
      ) : entries.length === 0 ? (
        <div className="empty-state">
          <MapPin size={48} />
          <h3>{search ? 'No results' : 'No addresses yet'}</h3>
          <p>{search ? 'Try a different search' : 'Add delivery addresses to use when creating invoices'}</p>
        </div>
      ) : (
        <div className="list-container">
          {entries.map((entry: AddressEntry) => (
            <div key={entry.id} className="list-item" style={{ alignItems: 'flex-start' }}>
              <div className="list-item-icon" style={{ background: 'var(--accent-glow)', color: 'var(--accent-light)', marginTop: 2 }}>
                <MapPin size={18} />
              </div>
              <div className="list-item-body">
                <p className="list-item-title">{entry.name}</p>
                <p className="list-item-sub">
                  {[entry.address_line1, entry.address_line2, entry.city].filter(Boolean).join(', ')}
                </p>
                {entry.phone && (
                  <p style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 3, display: 'flex', alignItems: 'center', gap: 4 }}>
                    <Phone size={10} /> {entry.phone}
                  </p>
                )}
              </div>
              <div style={{ display: 'flex', gap: 6, flexShrink: 0, marginLeft: 8 }}>
                <button
                  className="btn-icon"
                  style={{ width: 32, height: 32, color: 'var(--accent)' }}
                  onClick={() => { setEditing(entry); setShowForm(true); }}
                >
                  <Pencil size={14} />
                </button>
                <button
                  className="btn-icon"
                  style={{ width: 32, height: 32, color: 'var(--danger)' }}
                  onClick={() => handleDelete(entry.id)}
                >
                  <Trash2 size={14} />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      <button className="fab" onClick={() => { setEditing(null); setShowForm(true); }}>
        <Plus size={24} />
      </button>

      {showForm && (
        <AddressFormModal
          initial={editing}
          onClose={() => setShowForm(false)}
          onSuccess={() => { setShowForm(false); qc.invalidateQueries(); }}
        />
      )}
    </div>
  );
}

// ── Add/Edit Modal ────────────────────────────────────────────────────────────
export function AddressFormModal({ initial, onClose, onSuccess }: { initial: AddressEntry | null; onClose: () => void; onSuccess: () => void }) {
  const [form, setForm] = useState({
    name: initial?.name || '',
    phone: initial?.phone || '',
    address_line1: initial?.address_line1 || '',
    address_line2: initial?.address_line2 || '',
    city: initial?.city || '',
  });
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState('');

  const set = (k: string) => (e: React.ChangeEvent<HTMLInputElement>) => setForm(f => ({ ...f, [k]: e.target.value }));

  const onSubmit = async () => {
    if (!form.name.trim()) { setErr('Name is required'); return; }
    setLoading(true); setErr('');
    try {
      if (initial) {
        await addressBookApi.update(initial.id, form);
      } else {
        await addressBookApi.create(form);
      }
      onSuccess();
    } catch {
      setErr('Failed to save address');
    } finally { setLoading(false); }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-sheet" onClick={e => e.stopPropagation()}>
        <div className="modal-handle" />
        <h2 className="modal-title">{initial ? 'Edit Address' : 'New Address'}</h2>
        {err && <div style={{ color: 'var(--danger)', fontSize: 13, marginBottom: 12 }}>{err}</div>}

        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <div className="form-group" style={{ marginBottom: 0 }}>
            <label className="form-label">Name *</label>
            <input className="form-input" placeholder="e.g. Sunrise Warehouse" value={form.name} onChange={set('name')} />
          </div>
          <div className="form-group" style={{ marginBottom: 0 }}>
            <label className="form-label">Phone</label>
            <input className="form-input" type="tel" placeholder="+91 9876543210" value={form.phone} onChange={set('phone')} />
          </div>
          <div className="form-group" style={{ marginBottom: 0 }}>
            <label className="form-label">Address Line 1</label>
            <input className="form-input" placeholder="Street / Building" value={form.address_line1} onChange={set('address_line1')} />
          </div>
          <div className="form-group" style={{ marginBottom: 0 }}>
            <label className="form-label">Address Line 2</label>
            <input className="form-input" placeholder="Area / Landmark" value={form.address_line2} onChange={set('address_line2')} />
          </div>
          <div className="form-group" style={{ marginBottom: 0 }}>
            <label className="form-label">City</label>
            <input className="form-input" placeholder="City" value={form.city} onChange={set('city')} />
          </div>
        </div>

        <div style={{ display: 'flex', gap: 10, marginTop: 20 }}>
          <button type="button" className="btn btn-secondary" style={{ flex: 1 }} onClick={onClose}>Cancel</button>
          <button type="button" className="btn btn-primary" style={{ flex: 1 }} disabled={loading} onClick={onSubmit}>
            {loading ? 'Saving…' : initial ? 'Update' : 'Add Address'}
          </button>
        </div>
      </div>
    </div>
  );
}
