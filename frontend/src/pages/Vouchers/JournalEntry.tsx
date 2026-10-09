import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { partiesApi, chartOfAccountsApi, vouchersApi } from '../../api/endpoints';
import { ArrowLeft, Save, Plus, Trash2 } from 'lucide-react';
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
    queryFn: () => partiesApi.list('', 0, 1000).then((r) => r.data.items),
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
      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '12px 20px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <button onClick={() => navigate(-1)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-secondary)' }}>
            <ArrowLeft size={20} />
          </button>
          <h1 className="page-title" style={{ margin: 0 }}>Journal Voucher</h1>
        </div>
        <button className="btn-icon" onClick={handleSave} disabled={!isBalanced || createMutation.isPending} style={{ color: isBalanced ? 'var(--success)' : 'var(--text-muted)' }}>
          <Save size={24} />
        </button>
      </div>
      
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

        {/* Lines Table */}
        <div className="card" style={{ overflowX: 'auto', marginTop: 12 }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
            <thead>
              <tr style={{ background: 'var(--surface)', borderBottom: '1px solid var(--border)', textAlign: 'left' }}>
                <th style={{ padding: '12px 16px', fontWeight: 600 }}>Account</th>
                <th style={{ padding: '12px 16px', fontWeight: 600 }}>Party (if Control)</th>
                <th style={{ padding: '12px 16px', fontWeight: 600, textAlign: 'right' }}>Debit (₹)</th>
                <th style={{ padding: '12px 16px', fontWeight: 600, textAlign: 'right' }}>Credit (₹)</th>
                <th style={{ padding: '12px 16px', width: 40 }}></th>
              </tr>
            </thead>
            <tbody>
              {lines.map((line) => {
                const isPartyControl = accounts.find((a: any) => a.id.toString() === line.account_id)?.is_party_control;
                return (
                  <tr key={line.id} style={{ borderBottom: '1px solid var(--border)' }}>
                    <td style={{ padding: '8px 16px' }}>
                      <select 
                        className="form-input" 
                        style={{ minWidth: 200, padding: '8px' }}
                        value={line.account_id}
                        onChange={e => updateLine(line.id, 'account_id', e.target.value)}
                      >
                        <option value="">Select Account...</option>
                        {accounts.map((a: any) => (
                          <option key={a.id} value={a.id}>{a.name}</option>
                        ))}
                      </select>
                    </td>
                    <td style={{ padding: '8px 16px' }}>
                      {isPartyControl ? (
                        <select 
                          className="form-input" 
                          style={{ minWidth: 200, border: '1px dashed var(--accent)', padding: '8px' }}
                          value={line.party_id}
                          onChange={e => updateLine(line.id, 'party_id', e.target.value)}
                        >
                          <option value="">Select Party...</option>
                          {parties.map((p: any) => (
                            <option key={p.id} value={p.id}>{p.name}</option>
                          ))}
                        </select>
                      ) : (
                        <span style={{ color: 'var(--text-muted)' }}>—</span>
                      )}
                    </td>
                    <td style={{ padding: '8px 16px' }}>
                      <input 
                        type="number" 
                        className="form-input" 
                        placeholder="Dr" 
                        style={{ textAlign: 'right', fontWeight: 600, minWidth: 100 }}
                        value={line.type === 'DR' ? line.amount : ''}
                        onChange={e => {
                          const val = e.target.value;
                          if (val) {
                            setLines(lines.map(l => l.id === line.id ? { ...l, type: 'DR', amount: val } : l));
                          } else {
                            updateLine(line.id, 'amount', '');
                          }
                        }}
                      />
                    </td>
                    <td style={{ padding: '8px 16px' }}>
                      <input 
                        type="number" 
                        className="form-input" 
                        placeholder="Cr" 
                        style={{ textAlign: 'right', fontWeight: 600, minWidth: 100 }}
                        value={line.type === 'CR' ? line.amount : ''}
                        onChange={e => {
                          const val = e.target.value;
                          if (val) {
                            setLines(lines.map(l => l.id === line.id ? { ...l, type: 'CR', amount: val } : l));
                          } else {
                            updateLine(line.id, 'amount', '');
                          }
                        }}
                      />
                    </td>
                    <td style={{ padding: '8px 16px', textAlign: 'center' }}>
                      <button 
                        className="btn-icon" 
                        style={{ color: 'var(--danger)', padding: 4 }}
                        onClick={() => removeLine(line.id)}
                      >
                        <Trash2 size={16} />
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
            <tfoot>
              <tr style={{ background: 'var(--bg-body)' }}>
                <td colSpan={2} style={{ padding: '12px 16px' }}>
                  <button className="btn btn-secondary btn-sm" onClick={addLine}>
                    <Plus size={14} /> Add Line
                  </button>
                </td>
                <td style={{ padding: '12px 16px', textAlign: 'right', fontWeight: 700, fontSize: 14 }}>
                  {formatCurrency(totalDr)}
                </td>
                <td style={{ padding: '12px 16px', textAlign: 'right', fontWeight: 700, fontSize: 14 }}>
                  {formatCurrency(totalCr)}
                </td>
                <td style={{ padding: '12px 16px' }}>
                </td>
              </tr>
            </tfoot>
          </table>
        </div>

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
