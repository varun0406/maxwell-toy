import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { partiesApi, chartOfAccountsApi, vouchersApi, invoicesApi } from '../../api/endpoints';
import { ArrowLeft, Save } from 'lucide-react';

export default function SalesReturn() {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [form, setForm] = useState({
    party_id: '',
    account_id: '',
    invoice_id: '',
    amount: '',
    voucher_date: new Date().toISOString().split('T')[0],
    narration: '',
  });

  const { data: parties = [] } = useQuery({
    queryKey: ['parties'],
    queryFn: () => partiesApi.list('', 0, 1000).then((r) => r.data.items),
  });

  const { data: accounts = [] } = useQuery({
    queryKey: ['accounts', 'EXPENSE'], // Sales returns behave like expense/contra-income
    queryFn: () => chartOfAccountsApi.list().then((r) => r.data),
  });

  const { data: invoices = [] } = useQuery({
    queryKey: ['invoices', form.party_id],
    queryFn: () => invoicesApi.list(parseInt(form.party_id), false, '', 0, 100).then((r) => r.data.items),
    enabled: !!form.party_id,
  });

  const salesReturnAccounts = accounts.filter(a => a.name.toLowerCase().includes('return') || a.account_type === 'EXPENSE');

  const createMutation = useMutation({
    mutationFn: (data: any) => vouchersApi.create(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['vouchers'] });
      navigate('/vouchers');
    },
    onError: (err: any) => alert(err.response?.data?.detail || 'Error creating Credit Note'),
  });

  const handleSave = () => {
    if (!form.party_id || !form.account_id || !form.amount) {
      alert("Please fill all required fields");
      return;
    }
    const amt = parseFloat(form.amount);
    if (isNaN(amt) || amt <= 0) {
      alert("Invalid amount");
      return;
    }

    const payload = {
      voucher_type: 'CREDIT_NOTE',
      voucher_date: new Date(form.voucher_date).toISOString(),
      narration: form.narration || 'Sales Return',
      source: form.invoice_id ? 'INVOICE' : undefined,
      source_ref: form.invoice_id || undefined,
      lines: [
        {
          account_id: parseInt(form.account_id),
          debit: amt,
          credit: 0,
          line_narration: 'Sales Return'
        },
        {
          account_id: accounts.find(a => a.is_party_control)?.id || 1, // Fallback, normally you lookup the Party Control Account ID
          party_id: parseInt(form.party_id),
          debit: 0,
          credit: amt,
          line_narration: 'Party Credit'
        }
      ]
    };
    createMutation.mutate(payload);
  };

  return (
    <div className="page-layout">
      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '12px 20px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <button onClick={() => navigate(-1)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-secondary)' }}>
            <ArrowLeft size={20} />
          </button>
          <h1 className="page-title" style={{ margin: 0 }}>Credit Note (Sales Return)</h1>
        </div>
        <button className="btn-icon" onClick={handleSave} disabled={createMutation.isPending} style={{ color: 'var(--success)' }}>
          <Save size={24} />
        </button>
      </div>
      
      <div className="content-area" style={{ padding: 20 }}>
        <div className="card" style={{ padding: 20 }}>
          
          <div className="form-group">
            <label className="form-label">Date</label>
            <input 
              type="date" 
              className="form-input"
              value={form.voucher_date}
              onChange={e => setForm({ ...form, voucher_date: e.target.value })}
            />
          </div>

          <div className="form-group" style={{ marginTop: 16 }}>
            <label className="form-label">Party (Customer)</label>
            <select 
              className="form-input" 
              value={form.party_id}
              onChange={e => setForm({ ...form, party_id: e.target.value, invoice_id: '' })}
            >
              <option value="">Select Customer...</option>
              {parties.map((p: any) => (
                <option key={p.id} value={p.id}>{p.name}</option>
              ))}
            </select>
          </div>

          {form.party_id && invoices.length > 0 && (
            <div className="form-group" style={{ marginTop: 16 }}>
              <label className="form-label">Against Invoice (Optional)</label>
              <select 
                className="form-input" 
                value={form.invoice_id}
                onChange={e => setForm({ ...form, invoice_id: e.target.value })}
              >
                <option value="">-- No specific invoice --</option>
                {invoices.map((inv: any) => (
                  <option key={inv.id} value={inv.id}>
                    {inv.invoice_number} ({new Date(inv.invoice_date).toLocaleDateString()}) - ₹{inv.amount}
                  </option>
                ))}
              </select>
            </div>
          )}

          <div className="form-group" style={{ marginTop: 16 }}>
            <label className="form-label">Sales Return Account</label>
            <select 
              className="form-input" 
              value={form.account_id}
              onChange={e => setForm({ ...form, account_id: e.target.value })}
            >
              <option value="">Select Account...</option>
              {salesReturnAccounts.map((a: any) => (
                <option key={a.id} value={a.id}>{a.name}</option>
              ))}
            </select>
          </div>

          <div className="form-group" style={{ marginTop: 16 }}>
            <label className="form-label">Amount</label>
            <input 
              type="number" 
              className="form-input"
              placeholder="0.00"
              value={form.amount}
              onChange={e => setForm({ ...form, amount: e.target.value })}
            />
          </div>

          <div className="form-group" style={{ marginTop: 16 }}>
            <label className="form-label">Narration / Notes</label>
            <textarea 
              className="form-input"
              placeholder="Reason for return..."
              value={form.narration}
              onChange={e => setForm({ ...form, narration: e.target.value })}
            />
          </div>

          <button 
            className="btn btn-primary" 
            style={{ width: '100%', marginTop: 24 }}
            onClick={handleSave}
            disabled={createMutation.isPending}
          >
            {createMutation.isPending ? 'Saving...' : 'Save Credit Note'}
          </button>
        </div>
      </div>
    </div>
  );
}
