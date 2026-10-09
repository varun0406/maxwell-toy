import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { ChevronLeft, BookOpen, Plus, Minus } from 'lucide-react';
import { partiesApi } from '../../api/endpoints';
import { SearchCombobox } from '../../components/SearchCombobox';
import { formatCurrency } from '../../utils/format';
import type { ComboboxOption } from '../../components/SearchCombobox';

export default function Journals() {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [partySearch, setPartySearch] = useState('');
  const [partyId, setPartyId] = useState<number | null>(null);
  const [partyData, setPartyData] = useState<any>(null);
  const [absAmount, setAbsAmount] = useState('');
  const [isPositive, setIsPositive] = useState(false); // false = reduces receivable (credit), true = increases (debit)
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
    sublabel: `Receivable: ${formatCurrency(Number(party.outstanding || 0))}`,
  }));

  const signedAmount = absAmount ? (isPositive ? Number(absAmount) : -Number(absAmount)) : 0;
  const balanceBefore = Number(partyData?.outstanding || 0);
  const balanceAfter = balanceBefore + signedAmount;

  const handlePartyChange = async (option: ComboboxOption) => {
    const pid = Number(option.value);
    setPartyId(pid);
    try {
      const res = await partiesApi.get(pid);
      setPartyData(res.data);
    } catch { setPartyData(null); }
  };

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!partyId || !absAmount || Number(absAmount) <= 0 || !description.trim()) {
      setError('Party, amount (> 0), and description are required.');
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
        <div>
          <h1 className="page-title">Journal Entry</h1>
          <p className="page-subtitle">Post an adjustment to a party ledger</p>
        </div>
      </div>

      <form onSubmit={submit} style={{ maxWidth: 620, margin: '0 auto', padding: '8px 20px 32px' }}>
        {error && <div style={{ color: 'var(--danger)', marginBottom: 14, fontSize: 13, padding: '10px 14px', background: 'rgba(239,68,68,0.08)', borderRadius: 10 }}>{error}</div>}

        <div className="form-group">
          <label className="form-label">Party *</label>
          <SearchCombobox
            value={partyId}
            placeholder="Select party…"
            options={options}
            onChange={handlePartyChange}
            onSearch={setPartySearch}
          />
        </div>

        <div className="form-group">
          <label className="form-label">Amount *</label>
          <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
            {/* +/- toggle */}
            <div style={{ display: 'flex', borderRadius: 12, overflow: 'hidden', border: '1px solid var(--border)', flexShrink: 0 }}>
              <button
                type="button"
                onClick={() => setIsPositive(false)}
                title="Reduce receivable (credit)"
                style={{
                  padding: '10px 18px',
                  border: 'none',
                  cursor: 'pointer',
                  fontWeight: 700,
                  fontSize: 18,
                  background: !isPositive ? 'var(--success)' : 'var(--surface)',
                  color: !isPositive ? 'white' : 'var(--text-muted)',
                  transition: 'all 0.15s',
                }}
              >
                <Minus size={18} />
              </button>
              <button
                type="button"
                onClick={() => setIsPositive(true)}
                title="Increase receivable (debit)"
                style={{
                  padding: '10px 18px',
                  border: 'none',
                  cursor: 'pointer',
                  fontWeight: 700,
                  fontSize: 18,
                  background: isPositive ? 'var(--warning)' : 'var(--surface)',
                  color: isPositive ? 'white' : 'var(--text-muted)',
                  transition: 'all 0.15s',
                }}
              >
                <Plus size={18} />
              </button>
            </div>
            <input
              className="form-input"
              type="number"
              step="0.01"
              min="0"
              value={absAmount}
              onChange={e => setAbsAmount(e.target.value)}
              placeholder="0.00"
              style={{ flex: 1 }}
            />
          </div>
          {/* Impact label */}
          {absAmount && Number(absAmount) > 0 && (
            <div style={{
              marginTop: 8,
              padding: '8px 14px',
              borderRadius: 10,
              background: isPositive ? 'rgba(234,179,8,0.1)' : 'rgba(34,197,94,0.1)',
              color: isPositive ? 'var(--warning)' : 'var(--success)',
              fontSize: 13,
              fontWeight: 600,
            }}>
              {isPositive ? '↑ Increases receivable (party owes more)' : '↓ Reduces receivable (party owes less)'}
            </div>
          )}
        </div>

        {/* Balance preview */}
        {partyData && absAmount && Number(absAmount) > 0 && (
          <div style={{
            background: 'var(--bg-card)',
            border: '1px solid var(--border)',
            borderRadius: 14,
            padding: '14px 18px',
            marginBottom: 18,
          }}>
            <p style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 8 }}>Balance Preview</p>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13 }}>
              <span style={{ color: 'var(--text-secondary)' }}>Before</span>
              <span style={{ fontWeight: 600 }}>{formatCurrency(balanceBefore)}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, marginTop: 4 }}>
              <span style={{ color: 'var(--text-secondary)' }}>Adjustment</span>
              <span style={{ color: isPositive ? 'var(--warning)' : 'var(--success)', fontWeight: 600 }}>
                {isPositive ? '+' : '−'}{formatCurrency(Number(absAmount))}
              </span>
            </div>
            <div style={{ borderTop: '1px solid var(--border)', marginTop: 8, paddingTop: 8, display: 'flex', justifyContent: 'space-between', fontSize: 14 }}>
              <span style={{ fontWeight: 700 }}>After</span>
              <span style={{ fontWeight: 700, color: balanceAfter <= 0 ? 'var(--success)' : 'var(--text)' }}>
                {formatCurrency(balanceAfter)}
              </span>
            </div>
          </div>
        )}

        <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: 10 }}>
          <div className="form-group">
            <label className="form-label">Date *</label>
            <input className="form-input" type="date" value={date} onChange={e => setDate(e.target.value)} />
          </div>
        </div>

        <div className="form-group">
          <label className="form-label">Description *</label>
          <textarea
            className="form-input"
            rows={3}
            value={description}
            onChange={e => setDescription(e.target.value)}
            placeholder="Reason for adjustment (e.g. Discount allowed, Rate difference, etc.)"
          />
        </div>

        <button className="btn btn-primary btn-full" disabled={saving || !absAmount || Number(absAmount) <= 0}>
          <BookOpen size={16} /> {saving ? 'Posting…' : 'Post Journal Entry'}
        </button>
      </form>
    </div>
  );
}
