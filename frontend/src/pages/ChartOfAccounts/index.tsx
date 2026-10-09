import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { chartOfAccountsApi } from '../../api/endpoints';
import { Plus, X, Search, ArrowLeft } from 'lucide-react';

export default function ChartOfAccounts() {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [search, setSearch] = useState('');
  const [showAdd, setShowAdd] = useState(false);

  const { data: accounts = [], isLoading } = useQuery({
    queryKey: ['chart-of-accounts', search],
    queryFn: () => chartOfAccountsApi.list(undefined, search).then((r) => r.data),
  });

  return (
    <div className="page-layout">
      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '12px 20px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <button onClick={() => navigate(-1)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-secondary)' }}>
            <ArrowLeft size={20} />
          </button>
          <h1 className="page-title" style={{ margin: 0 }}>Chart of Accounts</h1>
        </div>
        <button className="btn-icon" onClick={() => setShowAdd(true)} style={{ color: 'var(--accent)' }}>
          <Plus size={24} />
        </button>
      </div>
      
      <div className="search-bar-container">
        <div className="search-input-wrapper">
          <Search size={18} className="search-icon" />
          <input
            type="text"
            className="search-input"
            placeholder="Search accounts..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
      </div>

      <div className="content-area">
        {isLoading ? (
          <div className="empty-state"><p>Loading...</p></div>
        ) : accounts.length === 0 ? (
          <div className="empty-state">
            <p>No accounts found.</p>
            <button className="btn btn-primary" onClick={() => setShowAdd(true)}>
              Create Account
            </button>
          </div>
        ) : (
          <div className="list-container">
            {accounts.map((acc: any) => (
              <div 
                key={acc.id} 
                className="list-item" 
                style={{ cursor: 'pointer' }}
                onClick={() => navigate(`/chart-of-accounts/${acc.id}`)}
              >
                <div className="list-item-body">
                  <p className="list-item-title">{acc.name}</p>
                  <p className="list-item-sub">{acc.account_type} {acc.code ? `• Code: ${acc.code}` : ''}</p>
                </div>
                <div className="list-item-right">
                  {acc.is_party_control && (
                    <span style={{ fontSize: 10, background: 'rgba(99,102,241,0.1)', color: 'var(--accent)', padding: '2px 6px', borderRadius: 4, fontWeight: 700 }}>
                      CTRL
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {showAdd && (
        <AddAccountModal onClose={() => setShowAdd(false)} onSuccess={() => { setShowAdd(false); qc.invalidateQueries({ queryKey: ['chart-of-accounts']}); }} />
      )}
    </div>
  );
}

function AddAccountModal({ onClose, onSuccess }: { onClose: () => void, onSuccess: () => void }) {
  const [form, setForm] = useState({
    name: '',
    account_type: 'INCOME',
    code: '',
    is_party_control: false
  });

  const mutation = useMutation({
    mutationFn: (data: any) => chartOfAccountsApi.create(data),
    onSuccess,
    onError: (err: any) => alert(err.response?.data?.detail || 'Error creating account')
  });

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <h3>New Account</h3>
          <button className="btn-icon" onClick={onClose}><X size={20} /></button>
        </div>
        <div className="modal-body" style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <div className="form-group">
            <label className="form-label">Account Name</label>
            <input 
              className="form-input" 
              placeholder="e.g. Sales Return" 
              value={form.name} 
              onChange={e => setForm({ ...form, name: e.target.value })} 
              autoFocus 
            />
          </div>
          <div className="form-group">
            <label className="form-label">Type</label>
            <select 
              className="form-input" 
              value={form.account_type} 
              onChange={e => setForm({ ...form, account_type: e.target.value })}
            >
              <option value="ASSET">Asset</option>
              <option value="LIABILITY">Liability</option>
              <option value="EQUITY">Equity</option>
              <option value="INCOME">Income</option>
              <option value="EXPENSE">Expense</option>
            </select>
          </div>
          <div className="form-group">
            <label className="form-label">Account Code (Optional)</label>
            <input 
              className="form-input" 
              placeholder="e.g. 4000" 
              value={form.code} 
              onChange={e => setForm({ ...form, code: e.target.value })} 
            />
          </div>
          <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 14 }}>
            <input 
              type="checkbox" 
              checked={form.is_party_control} 
              onChange={e => setForm({ ...form, is_party_control: e.target.checked })} 
            />
            Party Control Account (Sundry Debtors / Creditors)
          </label>
          <button 
            className="btn btn-primary" 
            style={{ width: '100%', marginTop: 8 }}
            onClick={() => mutation.mutate(form)}
            disabled={mutation.isPending || !form.name.trim()}
          >
            {mutation.isPending ? 'Saving...' : 'Save Account'}
          </button>
        </div>
      </div>
    </div>
  );
}
