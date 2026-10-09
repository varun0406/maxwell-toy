import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { partiesApi, chartOfAccountsApi, vouchersApi } from '../../api/endpoints';
import { ArrowLeft, Save, Plus, Trash2 } from 'lucide-react';
import Header from '../../components/Header';
import { formatCurrency } from '../../utils/format';

export default function JournalEntry() {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [form, setForm] = useState({
    voucher_date: new Date().toISOString().split('T')[0],
    narration: '',
  });

  const [lines, setLines] = useState([
    { id: 1, type: 'DR', account_id: '', party_id: '', amount: '' },
    { id: 2, type: 'CR', account_id: '', party_id: '', amount: '' },
  ]);

  const { data: parties = [] } = useQuery({
    queryKey: ['parties'],
    queryFn: () => partiesApi.list('', false).then((r) => r.data.items),
  });

  const { data: accounts = [] } = useQuery({
    queryKey: ['accounts'],
    queryFn: () => chartOfAccountsApi.list().then((r) => r.data),
  });

  const totalDr = lines.filter(l => l.type === 'DR').reduce((acc, l) => acc + (parseFloat(l.amount) || 0), 0);
  const totalCr = lines.filter(l => l.type === 'CR').reduce((acc, l) => acc + (parseFloat(l.amount) || 0), 0);
  const diff = Math.abs(totalDr - totalCr);
  const isBalanced = diff < 0.01 && totalDr > 0;

  const createMutation = useMutation({
    mutationFn: (data: any) => vouchersApi.create(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['vouchers'] });
      navigate('/vouchers');
    },
    onError: (err: any) => alert(err.response?.data?.detail || 'Error creating Journal Voucher'),
  });

  const handleSave = () => {
    if (!isBalanced) {
      alert("Journal must be balanced (Total Dr = Total Cr)");
      return;
    }
    
    // Validate lines
    for (const l of lines) {
      if (!l.account_id || !l.amount || parseFloat(l.amount) <= 0) {
        alert("Please select an account and valid amount for all lines.");
        return;
      }
    }

    const payload = {
      voucher_type: 'JOURNAL',
      voucher_date: new Date(form.voucher_date).toISOString(),
      narration: form.narration,
      lines: lines.map(l => ({
        account_id: parseInt(l.account_id),
        party_id: l.party_id ? parseInt(l.party_id) : null,
        debit: l.type === 'DR' ? parseFloat(l.amount) : 0,
        credit: l.type === 'CR' ? parseFloat(l.amount) : 0,
        line_narration: ''
      }))
    };
    createMutation.mutate(payload);
  };

  const addLine = () => {
    setLines([...lines, { id: Date.now(), type: 'DR', account_id: '', party_id: '', amount: '' }]);
  };

  const removeLine = (id: number) => {
    if (lines.length <= 2) return alert("Must have at least 2 lines");
    setLines(lines.filter(l => l.id !== id));
  };

  const updateLine = (id: number, field: string, value: any) => {
    setLines(lines.map(l => l.id === id ? { ...l, [field]: value } : l));
  };

  return (
    <div className="page-layout">
      <Header 
        title="Journal Voucher" 
        leftIcon={<ArrowLeft />} 
        onLeftClick={() => navigate(-1)} 
        rightIcon={<Save style={{ color: isBalanced ? 'var(--success)' : 'var(--text-muted)' }} />}
        onRightClick={handleSave}
      />
      
      <div className="content-area" style={{ padding: '16px 20px' }}>
        <div style={{ display: 'flex', gap: 12, marginBottom: 16 }}>
          <div className="form-group" style={{ flex: 1 }}>
            <label className="form-label">Date</label>
            <input 
              type="date" 
              className="form-input"
              value={form.voucher_date}
              onChange={e => setForm({ ...form, voucher_date: e.target.value })}
            />
          </div>
        </div>

        {/* Lines */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {lines.map((line, idx) => {
            const isPartyControl = accounts.find((a: any) => a.id.toString() === line.account_id)?.is_party_control;
            return (
              <div key={line.id} className="card" style={{ padding: 12 }}>
                <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                  <select 
                    className="form-input" 
                    style={{ width: 80, padding: '8px', fontWeight: 700 }}
                    value={line.type}
                    onChange={e => updateLine(line.id, 'type', e.target.value)}
                  >
                    <option value="DR">Dr</option>
                    <option value="CR">Cr</option>
                  </select>
                  
                  <select 
                    className="form-input" 
                    style={{ flex: 1 }}
                    value={line.account_id}
                    onChange={e => updateLine(line.id, 'account_id', e.target.value)}
                  >
                    <option value="">Select Account...</option>
                    {accounts.map((a: any) => (
                      <option key={a.id} value={a.id}>{a.name}</option>
                    ))}
                  </select>

                  <button 
                    className="btn-icon" 
                    style={{ padding: 8, color: 'var(--danger)' }}
                    onClick={() => removeLine(line.id)}
                  >
                    <Trash2 size={16} />
                  </button>
                </div>
                
                {isPartyControl && (
                  <div style={{ marginTop: 8 }}>
                    <select 
                      className="form-input" 
                      style={{ border: '1px dashed var(--accent)' }}
                      value={line.party_id}
                      onChange={e => updateLine(line.id, 'party_id', e.target.value)}
                    >
                      <option value="">Select Party...</option>
                      {parties.map((p: any) => (
                        <option key={p.id} value={p.id}>{p.name}</option>
                      ))}
                    </select>
                  </div>
                )}

                <div style={{ marginTop: 8 }}>
                  <input 
                    type="number" 
                    className="form-input" 
                    placeholder="Amount" 
                    style={{ textAlign: 'right', fontWeight: 700, fontSize: 16 }}
                    value={line.amount}
                    onChange={e => updateLine(line.id, 'amount', e.target.value)}
                  />
                </div>
              </div>
            );
          })}
        </div>

        <button className="btn btn-secondary" style={{ width: '100%', marginTop: 12 }} onClick={addLine}>
          <Plus size={16} /> Add Line
        </button>

        <div className="card" style={{ marginTop: 16, padding: 16 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
            <span style={{ fontWeight: 600 }}>Total Debit:</span>
            <span style={{ fontWeight: 700 }}>{formatCurrency(totalDr)}</span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: 8, borderBottom: '1px solid var(--border)' }}>
            <span style={{ fontWeight: 600 }}>Total Credit:</span>
            <span style={{ fontWeight: 700 }}>{formatCurrency(totalCr)}</span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', paddingTop: 8 }}>
            <span style={{ fontWeight: 700, color: isBalanced ? 'var(--success)' : 'var(--danger)' }}>
              {isBalanced ? 'Balanced' : `Difference: ${formatCurrency(diff)}`}
            </span>
          </div>
        </div>

        <div className="form-group" style={{ marginTop: 16 }}>
          <label className="form-label">Narration</label>
          <textarea 
            className="form-input"
            placeholder="Journal narration..."
            value={form.narration}
            onChange={e => setForm({ ...form, narration: e.target.value })}
          />
        </div>

        <div style={{ height: 40 }} />
      </div>
    </div>
  );
}
