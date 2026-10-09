import { useParams, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { chartOfAccountsApi } from '../../api/endpoints';
import { ArrowLeft, Filter } from 'lucide-react';
import { api } from '../../api/client';

export default function AccountLedger() {
  const { id } = useParams();
  const navigate = useNavigate();

  // Fetch account details to get the name
  const { data: accounts = [] } = useQuery({
    queryKey: ['chart-of-accounts'],
    queryFn: () => chartOfAccountsApi.list().then(r => r.data)
  });
  const account = accounts.find((a: any) => a.id === parseInt(id || '0'));

  // Fetch ledger entries
  const { data: ledger = [], isLoading } = useQuery({
    queryKey: ['account-ledger', id],
    queryFn: () => api.get(`/chart-of-accounts/${id}/entries`).then(r => r.data.items),
    enabled: !!id
  });

  return (
    <div className="page-layout">
      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '12px 20px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <button onClick={() => navigate(-1)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-secondary)' }}>
            <ArrowLeft size={20} />
          </button>
          <h1 className="page-title" style={{ margin: 0 }}>{account?.name || 'Account Ledger'}</h1>
        </div>
        <button className="btn-icon" style={{ color: 'var(--text-secondary)' }}>
          <Filter size={20} />
        </button>
      </div>

      <div className="content-area">
        {isLoading ? (
          <div className="empty-state"><p>Loading ledger...</p></div>
        ) : ledger.length === 0 ? (
          <div className="empty-state"><p>No transactions found for this account.</p></div>
        ) : (
          <div className="list-container">
            {ledger.map((entry: any) => (
              <div key={entry.id} className="list-item" style={{ flexDirection: 'column', alignItems: 'stretch' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                  <span style={{ fontSize: 12, color: 'var(--text-tertiary)', fontWeight: 600 }}>
                    {new Date(entry.voucher_date).toLocaleDateString()} • {entry.voucher_type} {entry.voucher_number ? `#${entry.voucher_number}` : ''}
                  </span>
                </div>
                
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                  <div style={{ flex: 1, paddingRight: 16 }}>
                    <p style={{ margin: '0 0 4px', fontSize: 14 }}>
                      {entry.party_name ? <span style={{ fontWeight: 600, color: 'var(--accent)' }}>{entry.party_name}</span> : entry.narration}
                    </p>
                    {entry.party_name && entry.narration && (
                      <p style={{ margin: 0, fontSize: 12, color: 'var(--text-secondary)' }}>{entry.narration}</p>
                    )}
                  </div>
                  <div style={{ textAlign: 'right', minWidth: 90 }}>
                    {parseFloat(entry.debit) > 0 && (
                      <p style={{ margin: 0, fontWeight: 700, color: 'var(--danger)', fontSize: 15 }}>
                        + ₹{parseFloat(entry.debit).toLocaleString('en-IN', { minimumFractionDigits: 2 })} <span style={{fontSize: 10}}>Dr</span>
                      </p>
                    )}
                    {parseFloat(entry.credit) > 0 && (
                      <p style={{ margin: 0, fontWeight: 700, color: 'var(--success)', fontSize: 15 }}>
                        - ₹{parseFloat(entry.credit).toLocaleString('en-IN', { minimumFractionDigits: 2 })} <span style={{fontSize: 10}}>Cr</span>
                      </p>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
