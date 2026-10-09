import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { analyticsApi } from '../../api/endpoints';
import { formatCurrency } from '../../utils/format';
import { Calendar } from 'lucide-react';

export default function TrialBalance() {
  const [asOfDate, setAsOfDate] = useState('');

  const { data, isLoading } = useQuery({
    queryKey: ['trial-balance', asOfDate],
    queryFn: () => analyticsApi.trialBalance(asOfDate).then((r) => r.data),
  });

  return (
    <div className="page-layout">
      <div className="page-header" style={{ padding: '16px 20px' }}>
        <h1 className="page-title">Trial Balance</h1>
      </div>

      <div className="content-area" style={{ padding: '0 20px' }}>
        <div className="card" style={{ padding: '12px 16px', marginBottom: 20 }}>
          <div style={{ display: 'flex', gap: 16, alignItems: 'center', flexWrap: 'wrap' }}>
            <div className="form-group" style={{ flex: 1, minWidth: 150 }}>
              <label className="form-label" style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                <Calendar size={14} /> As Of Date
              </label>
              <input 
                type="date" 
                className="form-input" 
                value={asOfDate} 
                onChange={e => setAsOfDate(e.target.value)} 
              />
            </div>
            <div style={{ flex: 1, minWidth: 150, alignSelf: 'flex-end', paddingBottom: 4 }}>
              {data && (
                <div style={{ 
                  display: 'inline-block', 
                  padding: '6px 12px', 
                  borderRadius: 6, 
                  background: data.is_balanced ? 'var(--success-glow)' : 'var(--danger-glow)',
                  color: data.is_balanced ? 'var(--success)' : 'var(--danger)',
                  fontSize: 12,
                  fontWeight: 600
                }}>
                  {data.is_balanced ? '✓ Books are Balanced' : '⚠️ Books Out of Balance'}
                </div>
              )}
            </div>
          </div>
        </div>

        {isLoading ? (
          <div style={{ padding: 24, textAlign: 'center' }}>Loading...</div>
        ) : !data || data.items.length === 0 ? (
          <div style={{ padding: 24, textAlign: 'center', color: 'var(--text-muted)' }}>
            No balances found.
          </div>
        ) : (
          <div className="card" style={{ overflow: 'hidden' }}>
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                <thead>
                  <tr style={{ background: 'var(--bg-elevated)', borderBottom: '1px solid var(--border)' }}>
                    <th style={{ padding: '12px 16px', textAlign: 'left', fontWeight: 600, color: 'var(--text-secondary)' }}>Account Name</th>
                    <th style={{ padding: '12px 16px', textAlign: 'left', fontWeight: 600, color: 'var(--text-secondary)' }}>Type</th>
                    <th style={{ padding: '12px 16px', textAlign: 'right', fontWeight: 600, color: 'var(--text-secondary)' }}>Debit</th>
                    <th style={{ padding: '12px 16px', textAlign: 'right', fontWeight: 600, color: 'var(--text-secondary)' }}>Credit</th>
                  </tr>
                </thead>
                <tbody>
                  {data.items.map((item: any) => (
                    <tr key={item.account_id} style={{ borderBottom: '1px solid var(--border)' }}>
                      <td style={{ padding: '12px 16px', fontWeight: 500 }}>{item.account_name}</td>
                      <td style={{ padding: '12px 16px', color: 'var(--text-muted)', fontSize: 12 }}>{item.account_type}</td>
                      <td style={{ padding: '12px 16px', textAlign: 'right', color: item.debit > 0 ? 'var(--text)' : 'var(--text-muted)' }}>
                        {item.debit > 0 ? formatCurrency(item.debit) : '-'}
                      </td>
                      <td style={{ padding: '12px 16px', textAlign: 'right', color: item.credit > 0 ? 'var(--text)' : 'var(--text-muted)' }}>
                        {item.credit > 0 ? formatCurrency(item.credit) : '-'}
                      </td>
                    </tr>
                  ))}
                  {/* Totals Row */}
                  <tr style={{ background: 'var(--bg-body)', fontWeight: 700 }}>
                    <td colSpan={2} style={{ padding: '16px', textAlign: 'right' }}>TOTAL</td>
                    <td style={{ padding: '16px', textAlign: 'right', color: data.is_balanced ? 'var(--text)' : 'var(--danger)' }}>
                      {formatCurrency(data.total_debit)}
                    </td>
                    <td style={{ padding: '16px', textAlign: 'right', color: data.is_balanced ? 'var(--text)' : 'var(--danger)' }}>
                      {formatCurrency(data.total_credit)}
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
      <div style={{ height: 100 }} />
    </div>
  );
}
