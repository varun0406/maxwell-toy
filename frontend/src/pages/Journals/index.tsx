import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { ChevronLeft, BookOpen } from 'lucide-react';
import { partiesApi } from '../../api/endpoints';
import { SearchCombobox } from '../../components/SearchCombobox';
import type { ComboboxOption } from '../../components/SearchCombobox';

export default function Journals() {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [partySearch, setPartySearch] = useState('');
  const [partyId, setPartyId] = useState<number | null>(null);
  const [amount, setAmount] = useState('');
  const [date, setDate] = useState(new Date().toISOString().slice(0, 10));
  const [description, setDescription] = useState('');
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);

  const { data: parties = [] } = useQuery({
    queryKey: ['journal-parties', partySearch],
    queryFn: () => partiesApi.list(partySearch, 0, 100).then(r => r.data.items || []),
  });
  const options: ComboboxOption[] = parties.map((party: any) => ({
    value: party.id,
    label: party.name,
    sublabel: `Receivable: ${Number(party.outstanding || 0).toLocaleString('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 })}`,
  }));

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    const signedAmount = Number(amount);
    if (!partyId || !signedAmount || !description.trim()) {
      setError('Party, signed amount, and description are required.');
      return;
    }
    setSaving(true);
    setError('');
    try {
      await partiesApi.addJournalEntry(partyId, {
        amount: signedAmount,
        entry_date: new Date(date).toISOString(),
        description: description.trim(),
      });
      await qc.invalidateQueries();
      navigate(-1);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Could not create journal entry.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="page-content">
      <div className="page-header" style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        <button className="btn-icon btn" onClick={() => navigate(-1)} title="Back"><ChevronLeft size={20} /></button>
        <div><h1 className="page-title">Journal Entry</h1><p className="page-subtitle">Post a signed adjustment to a party ledger</p></div>
      </div>
      <form onSubmit={submit} style={{ maxWidth: 620, margin: '0 auto', padding: '8px 20px 32px' }}>
        {error && <div style={{ color: 'var(--danger)', marginBottom: 14, fontSize: 13 }}>{error}</div>}
        <div className="form-group">
          <label className="form-label">Party *</label>
          <SearchCombobox value={partyId} placeholder="Select party…" options={options} onChange={option => setPartyId(Number(option.value))} onSearch={setPartySearch} />
        </div>
        <div className="form-group">
          <label className="form-label">Signed Amount *</label>
          <input className="form-input" type="number" step="0.01" value={amount} onChange={e => setAmount(e.target.value)} placeholder="Positive = receivable increases; negative = decreases" />
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
          <div className="form-group"><label className="form-label">Date *</label><input className="form-input" type="date" value={date} onChange={e => setDate(e.target.value)} /></div>
          <div className="form-group"><label className="form-label">Impact</label><div className="form-input" style={{ color: Number(amount) >= 0 ? 'var(--warning)' : 'var(--success)' }}>{Number(amount) >= 0 ? 'Increase receivable' : 'Reduce receivable'}</div></div>
        </div>
        <div className="form-group"><label className="form-label">Description *</label><textarea className="form-input" rows={3} value={description} onChange={e => setDescription(e.target.value)} placeholder="Reason, source reference, or settlement note" /></div>
        <button className="btn btn-primary btn-full" disabled={saving}><BookOpen size={16} /> {saving ? 'Posting…' : 'Post Journal Entry'}</button>
      </form>
    </div>
  );
}
